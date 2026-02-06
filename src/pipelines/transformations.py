"""
Transformation engine for applying rules-based transformations to data.

Transformations are applied post-load in the ELT pipeline.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Union
from enum import Enum
from dataclasses import dataclass
import re
from datetime import datetime


class TransformationType(Enum):
    """Types of transformations supported."""
    RENAME = "rename"
    CAST = "cast"
    FILTER = "filter"
    MAP = "map"
    CUSTOM = "custom"
    AGGREGATE = "aggregate"
    JOIN = "join"
    SPLIT = "split"
    TRIM = "trim"
    REPLACE = "replace"
    DEFAULT = "default"


@dataclass
class TransformationRule:
    """Base class for transformation rules."""
    rule_type: TransformationType
    config: Dict[str, Any]
    
    @abstractmethod
    def apply(self, data: Any) -> Any:
        """Apply transformation rule to data."""
        pass


@dataclass
class RenameRule(TransformationRule):
    """Rename column transformation."""
    
    def __post_init__(self):
        self.rule_type = TransformationType.RENAME
    
    def apply(self, row_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rename columns in row data.
        
        Config format:
        {
            "old_name": "new_name",
            ...
        }
        """
        mappings = self.config.get("mappings", {})
        result = row_data.copy()
        
        for old_name, new_name in mappings.items():
            if old_name in result:
                result[new_name] = result.pop(old_name)
        
        return result


@dataclass
class CastRule(TransformationRule):
    """Cast column to different type."""
    
    def __post_init__(self):
        self.rule_type = TransformationType.CAST
    
    def apply(self, value: Any) -> Any:
        """
        Cast value to target type.
        
        Config format:
        {
            "column": "column_name",
            "to": "target_type"
        }
        """
        target_type = self.config.get("to", "string").lower()
        
        if value is None:
            return None
        
        if target_type == "integer":
            return int(value)
        elif target_type == "float":
            return float(value)
        elif target_type == "string":
            return str(value)
        elif target_type == "boolean":
            if isinstance(value, bool):
                return value
            return str(value).lower() in ("true", "1", "yes")
        elif target_type == "date":
            if isinstance(value, str):
                return datetime.strptime(value, "%Y-%m-%d").date()
            return value
        elif target_type == "datetime":
            if isinstance(value, str):
                return datetime.fromisoformat(value)
            return value
        
        return value


@dataclass
class FilterRule(TransformationRule):
    """Filter rows based on condition."""
    
    def __post_init__(self):
        self.rule_type = TransformationType.FILTER
    
    def apply(self, row_data: Dict[str, Any]) -> bool:
        """
        Check if row matches filter condition.
        
        Config format:
        {
            "column": "column_name",
            "operator": "==", "!=", ">", "<", ">=", "<=", "in", "not_in",
            "value": target_value
        }
        """
        column = self.config.get("column")
        operator = self.config.get("operator", "==")
        value = self.config.get("value")
        
        if column not in row_data:
            return False
        
        col_value = row_data[column]
        
        if operator == "==":
            return col_value == value
        elif operator == "!=":
            return col_value != value
        elif operator == ">":
            return col_value > value
        elif operator == "<":
            return col_value < value
        elif operator == ">=":
            return col_value >= value
        elif operator == "<=":
            return col_value <= value
        elif operator == "in":
            return col_value in value
        elif operator == "not_in":
            return col_value not in value
        
        return True


@dataclass
class ReplaceRule(TransformationRule):
    """Replace values in a column."""
    
    def __post_init__(self):
        self.rule_type = TransformationType.REPLACE
    
    def apply(self, value: Any) -> Any:
        """
        Replace value.
        
        Config format:
        {
            "column": "column_name",
            "find": "pattern",
            "replace": "replacement",
            "is_regex": false
        }
        """
        find = self.config.get("find")
        replace = self.config.get("replace", "")
        is_regex = self.config.get("is_regex", False)
        
        if value is None:
            return None
        
        value_str = str(value)
        
        if is_regex:
            return re.sub(find, replace, value_str)
        else:
            return value_str.replace(find, replace)


@dataclass
class DefaultRule(TransformationRule):
    """Set default value if column is null."""
    
    def __post_init__(self):
        self.rule_type = TransformationType.DEFAULT
    
    def apply(self, value: Any) -> Any:
        """
        Set default value if null.
        
        Config format:
        {
            "column": "column_name",
            "value": default_value
        }
        """
        if value is None:
            return self.config.get("value")
        return value


class Transformer:
    """
    Applies a sequence of transformation rules to datasets.
    """
    
    def __init__(self, rules: Optional[List[TransformationRule]] = None):
        """
        Initialize transformer.
        
        Args:
            rules: List of transformation rules to apply
        """
        self.rules = rules or []
    
    def add_rule(self, rule: TransformationRule) -> None:
        """Add a transformation rule."""
        self.rules.append(rule)
    
    def transform_row(self, row_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply all transformation rules to a single row.
        
        Args:
            row_data: Dictionary representing a row
            
        Returns:
            Transformed row data
        """
        result = row_data.copy()
        
        for rule in self.rules:
            if rule.rule_type == TransformationType.RENAME:
                result = rule.apply(result)
            elif rule.rule_type == TransformationType.CAST:
                column = rule.config.get("column")
                if column in result:
                    result[column] = rule.apply(result[column])
            elif rule.rule_type == TransformationType.REPLACE:
                column = rule.config.get("column")
                if column in result:
                    result[column] = rule.apply(result[column])
            elif rule.rule_type == TransformationType.DEFAULT:
                column = rule.config.get("column")
                if column in result:
                    result[column] = rule.apply(result[column])
        
        return result
    
    def transform_rows(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply transformation rules to multiple rows.
        
        Args:
            rows: List of row dictionaries
            
        Returns:
            List of transformed rows
        """
        return [self.transform_row(row) for row in rows]
    
    @staticmethod
    def from_config(config: List[Dict[str, Any]]) -> "Transformer":
        """
        Build transformer from configuration.
        
        Args:
            config: List of transformation rule configurations
            
        Returns:
            Transformer instance
        """
        transformer = Transformer()
        
        for rule_config in config:
            rule_type_str = rule_config.get("type", "").lower()
            
            if rule_type_str == "rename":
                rule = RenameRule(TransformationType.RENAME, rule_config)
            elif rule_type_str == "cast":
                rule = CastRule(TransformationType.CAST, rule_config)
            elif rule_type_str == "filter":
                rule = FilterRule(TransformationType.FILTER, rule_config)
            elif rule_type_str == "replace":
                rule = ReplaceRule(TransformationType.REPLACE, rule_config)
            elif rule_type_str == "default":
                rule = DefaultRule(TransformationType.DEFAULT, rule_config)
            else:
                continue
            
            transformer.add_rule(rule)
        
        return transformer
