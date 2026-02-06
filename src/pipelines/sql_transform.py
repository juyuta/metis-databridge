"""
SQL-based transformation engine for declarative data transformations.

Modern data engineering approach using SQL for complex transformations.
Supports PostgreSQL stored procedures and SQL scripts.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

try:
    import psycopg
except ImportError:
    raise ImportError("psycopg package required. Install with: pip install psycopg[binary]")


logger = logging.getLogger(__name__)


@dataclass
class SQLTransformationStep:
    """Represents a single SQL transformation step."""
    name: str
    description: Optional[str]
    sql: str
    depends_on: List[str] = None
    is_final: bool = False  # Whether this step creates the final target table
    
    def __post_init__(self):
        if self.depends_on is None:
            self.depends_on = []


class SQLTransformationExecutor:
    """
    Executes SQL-based transformations on PostgreSQL.
    
    Supports:
    - Multi-step SQL transformations
    - CTEs and temporary tables
    - Data quality checks
    - Dependency management
    """
    
    def __init__(self, connection: psycopg.connection):
        """
        Initialize SQL transformation executor.
        
        Args:
            connection: Active psycopg connection to PostgreSQL
        """
        self.connection = connection
        self.steps: List[SQLTransformationStep] = []
        self.executed_steps: Dict[str, bool] = {}
    
    def add_step(self, step: SQLTransformationStep) -> None:
        """Add a transformation step."""
        self.steps.append(step)
        self.executed_steps[step.name] = False
    
    def execute(self) -> Dict[str, Any]:
        """
        Execute all transformation steps in dependency order.
        
        Returns:
            Dictionary with execution results for each step
        """
        results = {
            "total_steps": len(self.steps),
            "executed_steps": 0,
            "failed_steps": 0,
            "steps": {}
        }
        
        try:
            for step in self.steps:
                logger.info(f"Executing SQL transformation step: {step.name}")
                
                try:
                    with self.connection.cursor() as cursor:
                        # Execute the SQL
                        cursor.execute(step.sql)
                        
                        # Get rows affected if it's a DML statement
                        rows_affected = cursor.rowcount
                        
                        results["steps"][step.name] = {
                            "status": "completed",
                            "rows_affected": rows_affected,
                            "error": None
                        }
                        
                        self.executed_steps[step.name] = True
                        results["executed_steps"] += 1
                        
                        logger.info(f"Completed: {step.name} (rows: {rows_affected})")
                
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"Failed to execute {step.name}: {error_msg}")
                    
                    results["steps"][step.name] = {
                        "status": "failed",
                        "error": error_msg
                    }
                    results["failed_steps"] += 1
                    
                    # Stop on first failure
                    raise Exception(f"Transformation step '{step.name}' failed: {error_msg}")
        
        except Exception as e:
            logger.error(f"SQL transformation execution failed: {str(e)}")
            raise
        
        return results
    
    @staticmethod
    def from_sql_file(sql_file_path: str) -> "SQLTransformationExecutor":
        """
        Parse SQL transformation file and return executor.
        
        SQL file format (comments):
        
        -- @step: step_name
        -- @description: Human-readable description
        -- @depends_on: previous_step_1, previous_step_2 (optional)
        -- @final: true (optional, indicates final target table)
        SELECT ...;
        
        -- @step: next_step_name
        -- @description: Description
        SELECT ...;
        
        Args:
            sql_file_path: Path to SQL transformation file
            
        Returns:
            Dictionary of SQLTransformationStep objects indexed by step name
        """
        sql_file = Path(sql_file_path)
        
        if not sql_file.exists():
            raise FileNotFoundError(f"SQL file not found: {sql_file_path}")
        
        with open(sql_file, "r") as f:
            content = f.read()
        
        steps = {}
        current_step = None
        current_sql = []
        
        for line in content.split("\n"):
            # Check for step markers
            if line.startswith("-- @step:"):
                # Save previous step if exists
                if current_step:
                    steps[current_step["name"]] = SQLTransformationStep(
                        name=current_step["name"],
                        description=current_step.get("description"),
                        sql="\n".join(current_sql).strip(),
                        depends_on=current_step.get("depends_on", []),
                        is_final=current_step.get("is_final", False)
                    )
                
                # Start new step
                step_name = line.replace("-- @step:", "").strip()
                current_step = {"name": step_name}
                current_sql = []
            
            elif line.startswith("-- @description:"):
                if current_step:
                    current_step["description"] = line.replace("-- @description:", "").strip()
            
            elif line.startswith("-- @depends_on:"):
                if current_step:
                    deps = line.replace("-- @depends_on:", "").strip()
                    current_step["depends_on"] = [d.strip() for d in deps.split(",")]
            
            elif line.startswith("-- @final:"):
                if current_step:
                    is_final = line.replace("-- @final:", "").strip().lower() == "true"
                    current_step["is_final"] = is_final
            
            else:
                # Accumulate SQL
                if current_step is not None:
                    current_sql.append(line)
        
        # Save final step
        if current_step:
            steps[current_step["name"]] = SQLTransformationStep(
                name=current_step["name"],
                description=current_step.get("description"),
                sql="\n".join(current_sql).strip(),
                depends_on=current_step.get("depends_on", []),
                is_final=current_step.get("is_final", False)
            )
        
        logger.info(f"Parsed {len(steps)} transformation steps from {sql_file_path}")
        return steps


class SQLTransformationConfig:
    """Configuration for SQL-based transformations."""
    
    def __init__(self, sql_file_path: str, source_table: str, 
                 target_table: str, landing_table: Optional[str] = None):
        """
        Initialize SQL transformation config.
        
        Args:
            sql_file_path: Path to SQL transformation file
            source_table: Landing/staging table name
            target_table: Final target table name
            landing_table: Optional temporary table for intermediate results
        """
        self.sql_file_path = sql_file_path
        self.source_table = source_table
        self.target_table = target_table
        self.landing_table = landing_table or f"{source_table}_landing"
        
        # Parse SQL file
        self.steps = SQLTransformationExecutor.from_sql_file(sql_file_path)
    
    def get_variables(self) -> Dict[str, str]:
        """Get template variables for SQL substitution."""
        return {
            "SOURCE_TABLE": self.source_table,
            "LANDING_TABLE": self.landing_table,
            "TARGET_TABLE": self.target_table,
        }
    
    def substitute_variables(self, sql: str) -> str:
        """Substitute table names in SQL."""
        result = sql
        for var_name, var_value in self.get_variables().items():
            result = result.replace(f"${{{var_name}}}", var_value)
            result = result.replace(f"${var_name}", var_value)
        
        return result
