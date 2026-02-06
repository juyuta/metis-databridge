"""
Data validation framework for quality checks in the ELT pipeline.

Validations run after transformation before or after loading.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class ValidationLevel(Enum):
    """Severity levels for validation failures."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationResult:
    """Result of a validation check."""
    rule_name: str
    passed: bool
    level: ValidationLevel
    message: str
    row_count: Optional[int] = None
    failed_count: Optional[int] = None
    details: Dict[str, Any] = field(default_factory=dict)


class ValidationRule(ABC):
    """Base class for validation rules."""
    
    def __init__(self, name: str, config: Dict[str, Any], level: ValidationLevel = ValidationLevel.ERROR):
        """
        Initialize validation rule.
        
        Args:
            name: Name of the validation rule
            config: Rule configuration
            level: Severity level for failures
        """
        self.name = name
        self.config = config
        self.level = level
    
    @abstractmethod
    def validate(self, data: Any) -> ValidationResult:
        """Execute validation check."""
        pass


class RowCountRule(ValidationRule):
    """Validate row count is within expected range."""
    
    def validate(self, rows: List[Dict[str, Any]]) -> ValidationResult:
        """
        Validate row count.
        
        Config:
        {
            "min": minimum_count,
            "max": maximum_count,
            "exact": expected_count
        }
        """
        row_count = len(rows)
        min_count = self.config.get("min")
        max_count = self.config.get("max")
        exact_count = self.config.get("exact")
        
        passed = True
        message = f"Row count: {row_count}"
        
        if exact_count is not None:
            passed = row_count == exact_count
            message = f"Row count {row_count} {'==' if passed else '!='} expected {exact_count}"
        elif min_count is not None or max_count is not None:
            if min_count is not None:
                passed = passed and row_count >= min_count
            if max_count is not None:
                passed = passed and row_count <= max_count
            message = f"Row count {row_count} "
            if min_count and max_count:
                message += f"within range [{min_count}, {max_count}]"
            elif min_count:
                message += f">= {min_count}"
            elif max_count:
                message += f"<= {max_count}"
        
        return ValidationResult(
            rule_name=self.name,
            passed=passed,
            level=self.level,
            message=message,
            row_count=row_count
        )


class NullCheckRule(ValidationRule):
    """Check for null values in specified columns."""
    
    def validate(self, rows: List[Dict[str, Any]]) -> ValidationResult:
        """
        Validate no null values in specified columns.
        
        Config:
        {
            "columns": ["col1", "col2"],
            "allow_null": false
        }
        """
        columns = self.config.get("columns", [])
        allow_null = self.config.get("allow_null", False)
        
        null_rows = []
        
        for i, row in enumerate(rows):
            for col in columns:
                if col in row and row[col] is None:
                    if not allow_null:
                        null_rows.append((i, col))
        
        passed = len(null_rows) == 0
        message = f"Null check on columns {columns}: "
        
        if passed:
            message += "PASSED - No nulls found"
        else:
            message += f"FAILED - Found {len(null_rows)} null values"
        
        return ValidationResult(
            rule_name=self.name,
            passed=passed,
            level=self.level,
            message=message,
            failed_count=len(null_rows),
            details={"null_locations": null_rows}
        )


class DuplicateCheckRule(ValidationRule):
    """Check for duplicate values in specified columns."""
    
    def validate(self, rows: List[Dict[str, Any]]) -> ValidationResult:
        """
        Check for duplicates.
        
        Config:
        {
            "columns": ["col1", "col2"],
            "allow_duplicates": false
        }
        """
        columns = self.config.get("columns", [])
        allow_duplicates = self.config.get("allow_duplicates", False)
        
        seen = {}
        duplicates = []
        
        for i, row in enumerate(rows):
            key = tuple(row.get(col) for col in columns)
            
            if key in seen:
                if not allow_duplicates:
                    duplicates.append((seen[key], i))
            else:
                seen[key] = i
        
        passed = len(duplicates) == 0 or allow_duplicates
        message = f"Duplicate check on columns {columns}: "
        
        if passed:
            message += "PASSED"
        else:
            message += f"FAILED - Found {len(duplicates)} duplicates"
        
        return ValidationResult(
            rule_name=self.name,
            passed=passed,
            level=self.level,
            message=message,
            failed_count=len(duplicates),
            details={"duplicate_pairs": duplicates}
        )


class CustomRuleValidator(ValidationRule):
    """Custom validation rule using a predicate function."""
    
    def __init__(self, name: str, config: Dict[str, Any], predicate: Callable, 
                 level: ValidationLevel = ValidationLevel.ERROR):
        """
        Initialize custom rule.
        
        Args:
            name: Rule name
            config: Configuration
            predicate: Function that returns True if row is valid
            level: Severity level
        """
        super().__init__(name, config, level)
        self.predicate = predicate
    
    def validate(self, rows: List[Dict[str, Any]]) -> ValidationResult:
        """Apply custom validation predicate to all rows."""
        failed_rows = []
        
        for i, row in enumerate(rows):
            if not self.predicate(row):
                failed_rows.append(i)
        
        passed = len(failed_rows) == 0
        
        return ValidationResult(
            rule_name=self.name,
            passed=passed,
            level=self.level,
            message=f"Custom validation: {'PASSED' if passed else f'FAILED on {len(failed_rows)} rows'}",
            failed_count=len(failed_rows),
            details={"failed_rows": failed_rows}
        )


class Validator:
    """
    Orchestrates multiple validation rules.
    """
    
    def __init__(self, rules: Optional[List[ValidationRule]] = None):
        """
        Initialize validator.
        
        Args:
            rules: List of validation rules
        """
        self.rules = rules or []
        self.results: List[ValidationResult] = []
    
    def add_rule(self, rule: ValidationRule) -> None:
        """Add a validation rule."""
        self.rules.append(rule)
    
    def validate(self, rows: List[Dict[str, Any]]) -> List[ValidationResult]:
        """
        Run all validation rules.
        
        Args:
            rows: List of rows to validate
            
        Returns:
            List of validation results
        """
        self.results = []
        
        for rule in self.rules:
            result = rule.validate(rows)
            self.results.append(result)
        
        return self.results
    
    def passed(self) -> bool:
        """Check if all validations passed."""
        return all(r.passed for r in self.results if r.level == ValidationLevel.ERROR)
    
    def get_failures(self) -> List[ValidationResult]:
        """Get all failed validations."""
        return [r for r in self.results if not r.passed]
    
    def get_errors(self) -> List[ValidationResult]:
        """Get error-level failures."""
        return [r for r in self.results if not r.passed and r.level == ValidationLevel.ERROR]
    
    def get_warnings(self) -> List[ValidationResult]:
        """Get warning-level failures."""
        return [r for r in self.results if not r.passed and r.level == ValidationLevel.WARNING]
    
    @staticmethod
    def from_config(config: List[Dict[str, Any]]) -> "Validator":
        """
        Build validator from configuration.
        
        Args:
            config: List of validation rule configurations
            
        Returns:
            Validator instance
        """
        validator = Validator()
        
        for rule_config in config:
            rule_type = rule_config.get("type", "").lower()
            name = rule_config.get("name", rule_type)
            level_str = rule_config.get("level", "error").lower()
            level = ValidationLevel[level_str.upper()] if level_str else ValidationLevel.ERROR
            
            if rule_type == "row_count":
                rule = RowCountRule(name, rule_config, level)
            elif rule_type == "null_check":
                rule = NullCheckRule(name, rule_config, level)
            elif rule_type == "duplicate_check":
                rule = DuplicateCheckRule(name, rule_config, level)
            else:
                continue
            
            validator.add_rule(rule)
        
        return validator
