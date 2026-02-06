"""
Column mapping framework for metadata-driven transformations.

Supports loading mappings from CSV files containing source → target column definitions
with data types, precision, scale, and other transformation metadata.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path
from enum import Enum

try:
    import pandas as pd
except ImportError:
    raise ImportError("pandas package required. Install with: pip install pandas")

from connectors.base import DataType


logger = logging.getLogger(__name__)


@dataclass
class ColumnMapping:
    """Represents a single column mapping from source to target."""
    source_column: str
    target_column: str
    source_data_type: Optional[DataType] = None
    target_data_type: Optional[DataType] = None
    source_precision: Optional[int] = None
    source_scale: Optional[int] = None
    target_precision: Optional[int] = None
    target_scale: Optional[int] = None
    nullable: bool = True
    default_value: Optional[Any] = None
    transformation_rule: Optional[str] = None
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert mapping to dictionary."""
        return {
            "source_column": self.source_column,
            "target_column": self.target_column,
            "source_data_type": self.source_data_type.value if self.source_data_type else None,
            "target_data_type": self.target_data_type.value if self.target_data_type else None,
            "source_precision": self.source_precision,
            "source_scale": self.source_scale,
            "target_precision": self.target_precision,
            "target_scale": self.target_scale,
            "nullable": self.nullable,
            "default_value": self.default_value,
            "transformation_rule": self.transformation_rule,
            "description": self.description,
            "metadata": self.metadata,
        }


class MappingRegistry:
    """
    Registry for managing column mappings.
    
    Loads mappings from CSV files with columns:
    - source_column (required)
    - target_column (required)
    - source_data_type
    - target_data_type
    - source_precision
    - source_scale
    - target_precision
    - target_scale
    - nullable
    - default_value
    - transformation_rule
    - description
    """
    
    def __init__(self):
        """Initialize mapping registry."""
        self.mappings: Dict[str, ColumnMapping] = {}  # key: source_column
        self.target_map: Dict[str, ColumnMapping] = {}  # key: target_column
    
    def add_mapping(self, mapping: ColumnMapping) -> None:
        """Add a column mapping."""
        self.mappings[mapping.source_column] = mapping
        self.target_map[mapping.target_column] = mapping
        logger.debug(f"Added mapping: {mapping.source_column} → {mapping.target_column}")
    
    def get_mapping_by_source(self, source_column: str) -> Optional[ColumnMapping]:
        """Get mapping by source column name."""
        return self.mappings.get(source_column)
    
    def get_mapping_by_target(self, target_column: str) -> Optional[ColumnMapping]:
        """Get mapping by target column name."""
        return self.target_map.get(target_column)
    
    def get_all_mappings(self) -> List[ColumnMapping]:
        """Get all mappings."""
        return list(self.mappings.values())
    
    def get_source_columns(self) -> List[str]:
        """Get all source column names."""
        return list(self.mappings.keys())
    
    def get_target_columns(self) -> List[str]:
        """Get all target column names."""
        return [m.target_column for m in self.mappings.values()]
    
    def rename_columns(self, row_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rename columns according to mappings.
        
        Args:
            row_data: Dictionary with source column names as keys
            
        Returns:
            Dictionary with target column names as keys
        """
        result = {}
        
        for source_col, value in row_data.items():
            mapping = self.get_mapping_by_source(source_col)
            
            if mapping:
                # Apply mapping
                target_col = mapping.target_column
                result[target_col] = value
            else:
                # Keep column as-is if no mapping exists
                result[source_col] = value
        
        return result
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert mappings to pandas DataFrame for inspection."""
        data = [m.to_dict() for m in self.get_all_mappings()]
        return pd.DataFrame(data)
    
    @staticmethod
    def from_csv(csv_path: str) -> "MappingRegistry":
        """
        Load mappings from CSV file.
        
        CSV must contain at minimum:
        - source_column
        - target_column
        
        Optional columns:
        - source_data_type
        - target_data_type
        - source_precision
        - source_scale
        - target_precision
        - target_scale
        - nullable
        - default_value
        - transformation_rule
        - description
        
        Args:
            csv_path: Path to CSV mapping file
            
        Returns:
            MappingRegistry instance
        """
        csv_path = Path(csv_path)
        
        if not csv_path.exists():
            raise FileNotFoundError(f"Mapping file not found: {csv_path}")
        
        try:
            df = pd.read_csv(csv_path)
            
            # Validate required columns
            required_cols = {"source_column", "target_column"}
            missing_cols = required_cols - set(df.columns)
            
            if missing_cols:
                raise ValueError(f"CSV missing required columns: {missing_cols}")
            
            registry = MappingRegistry()
            
            for _, row in df.iterrows():
                # Parse data types
                source_dtype_str = row.get("source_data_type")
                target_dtype_str = row.get("target_data_type")
                
                source_dtype = None
                target_dtype = None
                
                if source_dtype_str and pd.notna(source_dtype_str):
                    try:
                        source_dtype = DataType[source_dtype_str.upper()]
                    except KeyError:
                        logger.warning(f"Unknown source data type: {source_dtype_str}")
                
                if target_dtype_str and pd.notna(target_dtype_str):
                    try:
                        target_dtype = DataType[target_dtype_str.upper()]
                    except KeyError:
                        logger.warning(f"Unknown target data type: {target_dtype_str}")
                
                # Parse precision and scale
                source_precision = row.get("source_precision")
                source_scale = row.get("source_scale")
                target_precision = row.get("target_precision")
                target_scale = row.get("target_scale")
                
                source_precision = int(source_precision) if pd.notna(source_precision) else None
                source_scale = int(source_scale) if pd.notna(source_scale) else None
                target_precision = int(target_precision) if pd.notna(target_precision) else None
                target_scale = int(target_scale) if pd.notna(target_scale) else None
                
                # Parse nullable
                nullable = True
                if "nullable" in row and pd.notna(row["nullable"]):
                    nullable_str = str(row["nullable"]).lower()
                    nullable = nullable_str in ("true", "yes", "1", "y")
                
                # Parse default value
                default_value = row.get("default_value")
                if pd.isna(default_value):
                    default_value = None
                
                # Create mapping
                mapping = ColumnMapping(
                    source_column=row["source_column"].strip(),
                    target_column=row["target_column"].strip(),
                    source_data_type=source_dtype,
                    target_data_type=target_dtype,
                    source_precision=source_precision,
                    source_scale=source_scale,
                    target_precision=target_precision,
                    target_scale=target_scale,
                    nullable=nullable,
                    default_value=default_value,
                    transformation_rule=row.get("transformation_rule"),
                    description=row.get("description"),
                )
                
                registry.add_mapping(mapping)
            
            logger.info(f"Loaded {len(registry.get_all_mappings())} mappings from {csv_path}")
            return registry
        
        except Exception as e:
            logger.error(f"Failed to load mappings from CSV: {str(e)}")
            raise


class MappingTransformer:
    """
    Applies column mappings to transform data.
    
    Handles:
    - Column renaming
    - Data type casting
    - Precision/scale adjustments
    - Default value application
    """
    
    def __init__(self, mapping_registry: MappingRegistry):
        """
        Initialize mapping transformer.
        
        Args:
            mapping_registry: Registry containing column mappings
        """
        self.mapping = mapping_registry
    
    def transform_row(self, row_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a single row using mappings.
        
        Args:
            row_data: Row data with source column names
            
        Returns:
            Transformed row with target column names and casted values
        """
        # First, rename columns according to mappings
        result = self.mapping.rename_columns(row_data)
        
        # Then apply type casting and other transformations
        for source_col, mapping in self.mapping.mappings.items():
            if source_col in row_data:
                value = row_data[source_col]
                target_col = mapping.target_column
                
                # Apply transformations
                if value is None:
                    # Use default if null
                    if mapping.default_value is not None:
                        result[target_col] = mapping.default_value
                    elif not mapping.nullable:
                        logger.warning(f"Null value in non-nullable column {target_col}")
                else:
                    # Cast to target type
                    if mapping.target_data_type:
                        result[target_col] = self._cast_value(
                            value,
                            mapping.target_data_type,
                            mapping.target_precision,
                            mapping.target_scale
                        )
        
        return result
    
    def transform_rows(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform multiple rows.
        
        Args:
            rows: List of row dictionaries
            
        Returns:
            List of transformed rows
        """
        return [self.transform_row(row) for row in rows]
    
    @staticmethod
    def _cast_value(value: Any, target_type: DataType, 
                   precision: Optional[int] = None,
                   scale: Optional[int] = None) -> Any:
        """
        Cast value to target data type.
        
        Args:
            value: Value to cast
            target_type: Target DataType
            precision: For decimals, total digits
            scale: For decimals, decimal places
            
        Returns:
            Casted value
        """
        if value is None:
            return None
        
        try:
            if target_type == DataType.INTEGER:
                return int(value)
            elif target_type == DataType.FLOAT:
                return float(value)
            elif target_type == DataType.STRING:
                return str(value)
            elif target_type == DataType.BOOLEAN:
                if isinstance(value, bool):
                    return value
                return str(value).lower() in ("true", "1", "yes", "y")
            elif target_type == DataType.DATE:
                if isinstance(value, str):
                    from datetime import datetime
                    return datetime.strptime(value, "%Y-%m-%d").date()
                return value
            elif target_type == DataType.DATETIME:
                if isinstance(value, str):
                    from datetime import datetime
                    return datetime.fromisoformat(value)
                return value
            elif target_type == DataType.DECIMAL:
                from decimal import Decimal
                decimal_val = Decimal(str(value))
                
                # Apply precision and scale if specified
                if precision and scale:
                    # Quantize to scale
                    quantize_str = "0." + "0" * scale
                    decimal_val = decimal_val.quantize(Decimal(quantize_str))
                
                return decimal_val
            else:
                return value
        
        except Exception as e:
            logger.warning(f"Failed to cast {value} to {target_type.value}: {str(e)}")
            return value
