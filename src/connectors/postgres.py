"""
PostgreSQL connectors for data extraction and loading.

Implements Source and Sink for PostgreSQL databases.
"""

import logging
import psycopg
from psycopg import sql
from typing import Any, Dict, List, Optional
from datetime import datetime, date, time

from .base import (
    Source,
    Sink,
    DataType,
    Column,
    Schema,
    DataRow,
    DataSet,
)

logger = logging.getLogger(__name__)

# Mapping PostgreSQL types to our DataType
PG_TO_DATATYPE = {
    "integer": DataType.INTEGER,
    "bigint": DataType.INTEGER,
    "smallint": DataType.INTEGER,
    "serial": DataType.INTEGER,
    "bigserial": DataType.INTEGER,
    "smallserial": DataType.INTEGER,
    "real": DataType.FLOAT,
    "double precision": DataType.FLOAT,
    "numeric": DataType.DECIMAL,
    "decimal": DataType.DECIMAL,
    "character varying": DataType.STRING,
    "varchar": DataType.STRING,
    "character": DataType.STRING,
    "text": DataType.STRING,
    "name": DataType.STRING,
    "boolean": DataType.BOOLEAN,
    "date": DataType.DATE,
    "time": DataType.TIMESTAMP,
    "timestamp": DataType.DATETIME,
    "timestamp without time zone": DataType.DATETIME,
    "timestamp with time zone": DataType.DATETIME,
    "bytea": DataType.BYTES,
    "json": DataType.JSON,
    "jsonb": DataType.JSON,
}

# Mapping DataType to PostgreSQL types
DATATYPE_TO_PG = {
    DataType.INTEGER: "INTEGER",
    DataType.FLOAT: "REAL",
    DataType.STRING: "VARCHAR(255)",
    DataType.BOOLEAN: "BOOLEAN",
    DataType.DATE: "DATE",
    DataType.DATETIME: "TIMESTAMP",
    DataType.TIMESTAMP: "TIMESTAMP",
    DataType.BYTES: "BYTEA",
    DataType.DECIMAL: "DECIMAL",
    DataType.JSON: "JSONB",
    DataType.NULL: "VARCHAR(255)",
}


class PostgreSQLSource(Source):
    """Extract data from PostgreSQL databases."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize PostgreSQL source.
        
        Config:
        {
            "host": "localhost",
            "port": 5432,
            "database": "mydb",
            "user": "postgres",
            "password": "password",
            "table": "source_table"  # or "query": "SELECT * FROM ..."
        }
        """
        super().__init__(name, config)
        self.connection = None
    
    def connect(self) -> None:
        """Establish PostgreSQL connection."""
        try:
            host = self.config.get("host", "localhost")
            port = self.config.get("port", 5432)
            database = self.config.get("database")
            user = self.config.get("user")
            password = self.config.get("password")
            
            if not database:
                raise ValueError("database configuration required")
            
            self.connection = psycopg.connect(
                host=host,
                port=port,
                dbname=database,
                user=user,
                password=password,
                autocommit=True
            )
            
            logger.info(f"[{self.name}] Connected to PostgreSQL: {user}@{host}:{port}/{database}")
        
        except Exception as e:
            logger.error(f"[{self.name}] Connection failed: {str(e)}")
            raise
    
    def disconnect(self) -> None:
        """Close PostgreSQL connection."""
        if self.connection:
            self.connection.close()
            logger.info(f"[{self.name}] Disconnected from PostgreSQL")
    
    def get_schema(self) -> Schema:
        """Get schema from source table."""
        if not self.connection:
            raise RuntimeError("Not connected to source")
        
        table_name = self.config.get("table")
        if not table_name:
            raise ValueError("table configuration required for schema extraction")
        
        try:
            with self.connection.cursor() as cursor:
                # Query information schema for column details
                cursor.execute(
                    """
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = %s
                    ORDER BY ordinal_position
                    """,
                    (table_name,)
                )
                
                columns = []
                for row in cursor.fetchall():
                    col_name, pg_type, is_nullable = row
                    
                    # Map PostgreSQL type to our DataType
                    data_type = PG_TO_DATATYPE.get(pg_type.lower(), DataType.STRING)
                    nullable = is_nullable.lower() == "yes"
                    
                    columns.append(Column(
                        name=col_name,
                        data_type=data_type,
                        nullable=nullable
                    ))
                
                return Schema(columns=columns)
        
        except Exception as e:
            logger.error(f"[{self.name}] Schema extraction failed: {str(e)}")
            raise
    
    def extract(self, query: Optional[str] = None) -> DataSet:
        """
        Extract data from PostgreSQL.
        
        Args:
            query: Custom SQL query. If None, uses table from config.
            
        Returns:
            DataSet containing extracted data
        """
        if not self.connection:
            raise RuntimeError("Not connected to source")
        
        try:
            # Build extraction query
            if query:
                extraction_query = query
                table_name = None
            else:
                table_name = self.config.get("table")
                if not table_name:
                    raise ValueError("table configuration required or query parameter needed")
                extraction_query = f"SELECT * FROM {table_name}"
            
            # Get schema
            if table_name:
                schema = self.get_schema()
            else:
                # For custom queries, infer schema from result
                with self.connection.cursor() as cursor:
                    cursor.execute(extraction_query)
                    # Get column info from cursor description
                    columns = [
                        Column(
                            name=desc[0],
                            data_type=DataType.STRING,  # Default to string for custom queries
                            nullable=True
                        )
                        for desc in cursor.description
                    ]
                    schema = Schema(columns=columns)
            
            # Extract data
            with self.connection.cursor() as cursor:
                cursor.execute(extraction_query)
                rows = []
                
                for pg_row in cursor.fetchall():
                    row_dict = {}
                    for col, value in zip(schema.columns, pg_row):
                        row_dict[col.name] = value
                    
                    rows.append(DataRow(data=row_dict))
            
            dataset = DataSet(
                schema=schema,
                rows=rows,
                metadata={
                    "source": self.name,
                    "table": table_name,
                    "extracted_at": datetime.now().isoformat()
                }
            )
            
            logger.info(f"[{self.name}] Extracted {dataset.row_count()} rows")
            return dataset
        
        except Exception as e:
            logger.error(f"[{self.name}] Extraction failed: {str(e)}")
            raise


class PostgreSQLSink(Sink):
    """Load data into PostgreSQL databases."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize PostgreSQL sink.
        
        Config:
        {
            "host": "localhost",
            "port": 5432,
            "database": "mydb",
            "user": "postgres",
            "password": "password",
            "table_name": "target_table",
            "create_if_not_exists": true,
            "drop_if_exists": false
        }
        """
        super().__init__(name, config)
        self.connection = None
    
    def connect(self) -> None:
        """Establish PostgreSQL connection."""
        try:
            host = self.config.get("host", "localhost")
            port = self.config.get("port", 5432)
            database = self.config.get("database")
            user = self.config.get("user")
            password = self.config.get("password")
            
            if not database:
                raise ValueError("database configuration required")
            
            self.connection = psycopg.connect(
                host=host,
                port=port,
                dbname=database,
                user=user,
                password=password,
                autocommit=True
            )
            
            logger.info(f"[{self.name}] Connected to PostgreSQL: {user}@{host}:{port}/{database}")
        
        except Exception as e:
            logger.error(f"[{self.name}] Connection failed: {str(e)}")
            raise
    
    def disconnect(self) -> None:
        """Close PostgreSQL connection."""
        if self.connection:
            self.connection.close()
            logger.info(f"[{self.name}] Disconnected from PostgreSQL")
    
    def create_table(self, schema: Schema, table_name: str) -> None:
        """
        Create table in PostgreSQL based on schema.
        
        Args:
            schema: Schema definition
            table_name: Name of table to create
        """
        if not self.connection:
            raise RuntimeError("Not connected to sink")
        
        drop_if_exists = self.config.get("drop_if_exists", False)
        
        try:
            with self.connection.cursor() as cursor:
                # Drop table if requested
                if drop_if_exists:
                    cursor.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(
                        sql.Identifier(table_name)
                    ))
                    logger.info(f"[{self.name}] Dropped table {table_name}")
                
                # Build CREATE TABLE statement
                column_defs = []
                for col in schema.columns:
                    pg_type = DATATYPE_TO_PG.get(col.data_type, "VARCHAR(255)")
                    nullable_str = "" if not col.nullable else ""
                    column_defs.append(f'"{col.name}" {pg_type} {nullable_str}'.strip())
                
                create_sql = sql.SQL(
                    "CREATE TABLE IF NOT EXISTS {} ({})"
                ).format(
                    sql.Identifier(table_name),
                    sql.SQL(", ").join(sql.SQL(cd) for cd in column_defs)
                )
                
                cursor.execute(create_sql)
                logger.info(f"[{self.name}] Created table {table_name}")
        
        except Exception as e:
            logger.error(f"[{self.name}] Table creation failed: {str(e)}")
            raise
    
    def load(self, dataset: DataSet) -> int:
        """
        Load data into PostgreSQL.
        
        Args:
            dataset: DataSet to load
            
        Returns:
            Number of rows loaded
        """
        if not self.connection:
            raise RuntimeError("Not connected to sink")
        
        table_name = self.config.get("table_name")
        if not table_name:
            raise ValueError("table_name configuration required")
        
        try:
            rows_loaded = 0
            
            with self.connection.cursor() as cursor:
                for row in dataset.rows:
                    # Build INSERT statement
                    columns = list(row.data.keys())
                    values = [row.data[col] for col in columns]
                    
                    insert_sql = sql.SQL(
                        "INSERT INTO {} ({}) VALUES ({})"
                    ).format(
                        sql.Identifier(table_name),
                        sql.SQL(", ").join(sql.Identifier(col) for col in columns),
                        sql.SQL(", ").join(sql.Placeholder() * len(columns))
                    )
                    
                    cursor.execute(insert_sql, values)
                    rows_loaded += 1
            
            logger.info(f"[{self.name}] Loaded {rows_loaded} rows into {table_name}")
            return rows_loaded
        
        except Exception as e:
            logger.error(f"[{self.name}] Load failed: {str(e)}")
            raise


# Register connectors
from .base import ConnectorRegistry
ConnectorRegistry.register_source("postgres", PostgreSQLSource)
ConnectorRegistry.register_sink("postgres", PostgreSQLSink)
