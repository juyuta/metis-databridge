"""
Base connector classes for data sources and sinks.

Follows the ELT pattern:
- Source: Extracts raw data from external systems
- Sink: Loads data into target systems
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class DataType(Enum):
    """Supported data types."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    TIMESTAMP = "timestamp"
    BYTES = "bytes"
    DECIMAL = "decimal"
    JSON = "json"
    NULL = "null"


@dataclass
class Column:
    """Represents a column in a dataset."""
    name: str
    data_type: DataType
    nullable: bool = True
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "data_type": self.data_type.value,
            "nullable": self.nullable,
            "description": self.description,
            "metadata": self.metadata,
        }


@dataclass
class Schema:
    """Represents the structure of a dataset."""
    columns: List[Column]
    
    def get_column(self, name: str) -> Optional[Column]:
        """Get a column by name."""
        return next((c for c in self.columns if c.name == name), None)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "columns": [c.to_dict() for c in self.columns]
        }


@dataclass
class DataRow:
    """Represents a single row of data."""
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value by key."""
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set value by key."""
        self.data[key] = value


@dataclass
class DataSet:
    """Represents a collection of rows with schema."""
    schema: Schema
    rows: List[DataRow]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def row_count(self) -> int:
        """Get number of rows."""
        return len(self.rows)
    
    def add_row(self, row: DataRow) -> None:
        """Add a row to the dataset."""
        self.rows.append(row)
    
    def to_dict_list(self) -> List[Dict[str, Any]]:
        """Convert dataset to list of dictionaries."""
        return [row.data for row in self.rows]


class Source(ABC):
    """
    Abstract base class for data sources.
    
    Responsible for extracting data from external systems in the ELT pipeline.
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize source.
        
        Args:
            name: Logical name of the source
            config: Source configuration from YAML
        """
        self.name = name
        self.config = config
    
    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the source system."""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to the source system."""
        pass
    
    @abstractmethod
    def get_schema(self) -> Schema:
        """Get the schema of the data source."""
        pass
    
    @abstractmethod
    def extract(self, query: Optional[str] = None) -> DataSet:
        """
        Extract data from source.
        
        Args:
            query: Optional extraction query/filter
            
        Returns:
            DataSet containing extracted data
        """
        pass
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


class Sink(ABC):
    """
    Abstract base class for data sinks/targets.
    
    Responsible for loading data into target systems in the ELT pipeline.
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize sink.
        
        Args:
            name: Logical name of the sink
            config: Sink configuration from YAML
        """
        self.name = name
        self.config = config
    
    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the target system."""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to the target system."""
        pass
    
    @abstractmethod
    def load(self, dataset: DataSet) -> int:
        """
        Load data to target system.
        
        Args:
            dataset: DataSet to load
            
        Returns:
            Number of rows loaded
        """
        pass
    
    @abstractmethod
    def create_table(self, schema: Schema, table_name: str) -> None:
        """
        Create table in target system based on schema.
        
        Args:
            schema: Schema definition
            table_name: Name of table to create
        """
        pass
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


class ConnectorRegistry:
    """Registry for managing available connectors."""
    
    _sources: Dict[str, type] = {}
    _sinks: Dict[str, type] = {}
    
    @classmethod
    def register_source(cls, name: str, source_class: type) -> None:
        """Register a source connector."""
        cls._sources[name] = source_class
    
    @classmethod
    def register_sink(cls, name: str, sink_class: type) -> None:
        """Register a sink connector."""
        cls._sinks[name] = sink_class
    
    @classmethod
    def get_source(cls, name: str) -> Optional[type]:
        """Get source connector by name."""
        return cls._sources.get(name)
    
    @classmethod
    def get_sink(cls, name: str) -> Optional[type]:
        """Get sink connector by name."""
        return cls._sinks.get(name)
    
    @classmethod
    def list_sources(cls) -> List[str]:
        """List all registered sources."""
        return list(cls._sources.keys())
    
    @classmethod
    def list_sinks(cls) -> List[str]:
        """List all registered sinks."""
        return list(cls._sinks.keys())
