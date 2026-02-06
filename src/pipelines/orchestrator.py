"""
Pipeline orchestrator for ELT workflows.

Manages Extract → Load → Transform → Validate flow.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging

from connectors.base import Source, Sink, DataSet
from pipelines.transformations import Transformer
from pipelines.validation import Validator, ValidationResult
from pipelines.mapping import MappingRegistry, MappingTransformer
from pipelines.sql_transform import SQLTransformationConfig, SQLTransformationExecutor


logger = logging.getLogger(__name__)


class PipelineStatus(Enum):
    """Pipeline execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class PipelineStage(Enum):
    """Stages of ELT pipeline."""
    EXTRACT = "extract"
    LOAD = "load"
    TRANSFORM = "transform"
    VALIDATE = "validate"
    COMPLETE = "complete"


@dataclass
class StageResult:
    """Result of executing a pipeline stage."""
    stage: PipelineStage
    status: PipelineStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    record_count: Optional[int] = None
    duration_seconds: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.completed_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()


@dataclass
class PipelineConfig:
    """Configuration for a pipeline."""
    name: str
    source_type: str
    source_config: Dict[str, Any]
    sink_type: str
    sink_config: Dict[str, Any]
    transformations: Optional[List[Dict[str, Any]]] = None
    validations: Optional[List[Dict[str, Any]]] = None
    mapping_file: Optional[str] = None
    sql_transform_file: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineExecution:
    """Tracks execution of a pipeline."""
    pipeline_name: str
    started_at: datetime
    status: PipelineStatus
    stages: List[StageResult] = field(default_factory=list)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    rows_extracted: int = 0
    rows_loaded: int = 0
    rows_transformed: int = 0
    validation_results: List[ValidationResult] = field(default_factory=list)
    
    def duration_seconds(self) -> Optional[float]:
        """Get total execution duration."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def failed(self) -> bool:
        """Check if pipeline failed."""
        return self.status == PipelineStatus.FAILED
    
    def succeeded(self) -> bool:
        """Check if pipeline succeeded."""
        return self.status == PipelineStatus.COMPLETED


class Pipeline:
    """
    Orchestrates ELT workflow.
    
    Flow: Extract → Load → Transform → Validate
    """
    
    def __init__(self, config: PipelineConfig, source: Source, sink: Sink):
        """
        Initialize pipeline.
        
        Args:
            config: Pipeline configuration
            source: Source connector
            sink: Sink connector
        """
        self.config = config
        self.source = source
        self.sink = sink
        self.transformer: Optional[Transformer] = None
        self.mapping_transformer: Optional[MappingTransformer] = None
        self.sql_executor: Optional[SQLTransformationExecutor] = None
        self.validator: Optional[Validator] = None
        self.execution: Optional[PipelineExecution] = None
    
    def setup_transformations(self) -> None:
        """Initialize transformer from config."""
        if self.config.transformations:
            self.transformer = Transformer.from_config(self.config.transformations)
        else:
            self.transformer = Transformer()
    
    def setup_mappings(self) -> None:
        """Initialize mapping transformer from CSV file if configured."""
        if self.config.mapping_file:
            try:
                mapping_registry = MappingRegistry.from_csv(self.config.mapping_file)
                self.mapping_transformer = MappingTransformer(mapping_registry)
                logger.info(f"[{self.config.name}] Loaded column mappings from {self.config.mapping_file}")
            except Exception as e:
                logger.warning(f"[{self.config.name}] Failed to load mappings: {str(e)}")
    
    def setup_sql_transformations(self) -> None:
        """Initialize SQL transformation executor if configured."""
        if self.config.sql_transform_file:
            try:
                sql_steps = SQLTransformationExecutor.from_sql_file(self.config.sql_transform_file)
                logger.info(f"[{self.config.name}] Loaded {len(sql_steps)} SQL transformation steps")
                # Store for later use
                self._sql_steps = sql_steps
            except Exception as e:
                logger.warning(f"[{self.config.name}] Failed to load SQL transformations: {str(e)}")
    
    def setup_validations(self) -> None:
        """Initialize validator from config."""
        if self.config.validations:
            self.validator = Validator.from_config(self.config.validations)
        else:
            self.validator = Validator()
    
    def extract(self) -> DataSet:
        """
        Extract data from source.
        
        Returns:
            DataSet containing raw data
        """
        logger.info(f"[{self.config.name}] Starting EXTRACT stage")
        
        try:
            with self.source:
                dataset = self.source.extract()
            
            logger.info(f"[{self.config.name}] EXTRACT complete - {dataset.row_count()} rows")
            return dataset
        
        except Exception as e:
            logger.error(f"[{self.config.name}] EXTRACT failed: {str(e)}")
            raise
    
    def load(self, dataset: DataSet) -> int:
        """
        Load data to sink (target system).
        
        Args:
            dataset: DataSet to load
            
        Returns:
            Number of rows loaded
        """
        logger.info(f"[{self.config.name}] Starting LOAD stage")
        
        try:
            with self.sink:
                # Create table if needed
                self.sink.create_table(dataset.schema, self.config.sink_config.get("table_name", "landing"))
                
                # Load data
                rows_loaded = self.sink.load(dataset)
            
            logger.info(f"[{self.config.name}] LOAD complete - {rows_loaded} rows loaded")
            return rows_loaded
        
        except Exception as e:
            logger.error(f"[{self.config.name}] LOAD failed: {str(e)}")
            raise
    
    def transform(self, dataset: DataSet) -> DataSet:
        """
        Apply transformations to dataset.
        
        Supports both:
        - In-memory transformations (mapping + rules)
        - SQL-based transformations (declarative approach)
        
        Args:
            dataset: DataSet to transform
            
        Returns:
            Transformed DataSet (or empty if using SQL transformations)
        """
        logger.info(f"[{self.config.name}] Starting TRANSFORM stage")
        
        try:
            # If SQL transformation is configured, use SQL-based approach
            if self.config.sql_transform_file and hasattr(self, '_sql_steps'):
                logger.info(f"[{self.config.name}] Using SQL-based transformation")
                return self._transform_with_sql(dataset)
            
            # Otherwise use in-memory transformations
            original_rows = dataset.to_dict_list()
            transformed_rows = original_rows
            
            # First apply mapping-based transformations (column rename, type casting)
            if self.mapping_transformer:
                transformed_rows = self.mapping_transformer.transform_rows(transformed_rows)
                logger.info(f"[{self.config.name}] Applied column mappings")
            
            # Then apply rule-based transformations
            if self.transformer:
                transformed_rows = self.transformer.transform_rows(transformed_rows)
            
            # Rebuild dataset with transformed rows
            from connectors.base import DataRow
            
            transformed_dataset = DataSet(
                schema=dataset.schema,
                rows=[DataRow(data=row) for row in transformed_rows],
                metadata=dataset.metadata
            )
            
            logger.info(f"[{self.config.name}] TRANSFORM complete")
            return transformed_dataset
        
        except Exception as e:
            logger.error(f"[{self.config.name}] TRANSFORM failed: {str(e)}")
            raise
    
    def _transform_with_sql(self, dataset: DataSet) -> DataSet:
        """
        Apply SQL-based transformations using database engine.
        
        Args:
            dataset: DataSet (loaded to staging table)
            
        Returns:
            Empty dataset (SQL executed server-side)
        """
        try:
            # For SQL transformations, the data is already in the staging table
            # The SQL executor will work on the database directly
            logger.info(f"[{self.config.name}] Executing SQL transformations")
            
            # Get sink connection for SQL execution
            if hasattr(self.sink, 'connection') and self.sink.connection:
                executor = SQLTransformationExecutor(self.sink.connection)
                
                # Add all SQL steps
                for step in self._sql_steps.values():
                    executor.add_step(step)
                
                # Execute transformations
                results = executor.execute()
                
                logger.info(f"[{self.config.name}] SQL transformations completed: {results}")
            
            # Return empty dataset since transformations are on database side
            return DataSet(schema=dataset.schema, rows=[], metadata={"sql_transform": True})
        
        except Exception as e:
            logger.error(f"[{self.config.name}] SQL transformation failed: {str(e)}")
            raise
    
    def validate(self, dataset: DataSet) -> List[ValidationResult]:
        """
        Run validation checks on dataset.
        
        Args:
            dataset: DataSet to validate
            
        Returns:
            List of validation results
        """
        if not self.validator:
            return []
        
        logger.info(f"[{self.config.name}] Starting VALIDATE stage")
        
        try:
            rows = dataset.to_dict_list()
            results = self.validator.validate(rows)
            
            passed = sum(1 for r in results if r.passed)
            failed = sum(1 for r in results if not r.passed)
            
            logger.info(f"[{self.config.name}] VALIDATE complete - {passed} passed, {failed} failed")
            
            return results
        
        except Exception as e:
            logger.error(f"[{self.config.name}] VALIDATE failed: {str(e)}")
            raise
    
    def execute(self) -> PipelineExecution:
        """
        Execute the complete ELT pipeline.
        
        Flow:
        1. Extract data from source
        2. Load to sink (staging/landing)
        3. Transform data
        4. Validate data
        
        Returns:
            PipelineExecution with results
        """
        self.execution = PipelineExecution(
            pipeline_name=self.config.name,
            started_at=datetime.now(),
            status=PipelineStatus.RUNNING
        )
        
        try:
            # Setup
            self.setup_transformations()
            self.setup_mappings()
            self.setup_sql_transformations()
            self.setup_validations()
            
            # EXTRACT
            start = datetime.now()
            dataset = self.extract()
            self.execution.rows_extracted = dataset.row_count()
            self.execution.stages.append(StageResult(
                stage=PipelineStage.EXTRACT,
                status=PipelineStatus.COMPLETED,
                started_at=start,
                completed_at=datetime.now(),
                record_count=dataset.row_count()
            ))
            
            # LOAD (to staging/landing)
            start = datetime.now()
            rows_loaded = self.load(dataset)
            self.execution.rows_loaded = rows_loaded
            self.execution.stages.append(StageResult(
                stage=PipelineStage.LOAD,
                status=PipelineStatus.COMPLETED,
                started_at=start,
                completed_at=datetime.now(),
                record_count=rows_loaded
            ))
            
            # TRANSFORM
            start = datetime.now()
            transformed_dataset = self.transform(dataset)
            self.execution.rows_transformed = transformed_dataset.row_count()
            self.execution.stages.append(StageResult(
                stage=PipelineStage.TRANSFORM,
                status=PipelineStatus.COMPLETED,
                started_at=start,
                completed_at=datetime.now(),
                record_count=transformed_dataset.row_count()
            ))
            
            # VALIDATE
            start = datetime.now()
            validation_results = self.validate(transformed_dataset)
            self.execution.validation_results = validation_results
            self.execution.stages.append(StageResult(
                stage=PipelineStage.VALIDATE,
                status=PipelineStatus.COMPLETED,
                started_at=start,
                completed_at=datetime.now()
            ))
            
            # Complete
            self.execution.status = PipelineStatus.COMPLETED
            self.execution.completed_at = datetime.now()
            
            logger.info(f"[{self.config.name}] Pipeline completed successfully")
        
        except Exception as e:
            self.execution.status = PipelineStatus.FAILED
            self.execution.error = str(e)
            self.execution.completed_at = datetime.now()
            logger.error(f"[{self.config.name}] Pipeline failed: {str(e)}")
        
        return self.execution
    
    def get_execution_report(self) -> Dict[str, Any]:
        """Generate execution report."""
        if not self.execution:
            return {}
        
        return {
            "pipeline_name": self.execution.pipeline_name,
            "status": self.execution.status.value,
            "started_at": self.execution.started_at.isoformat(),
            "completed_at": self.execution.completed_at.isoformat() if self.execution.completed_at else None,
            "duration_seconds": self.execution.duration_seconds(),
            "rows_extracted": self.execution.rows_extracted,
            "rows_loaded": self.execution.rows_loaded,
            "rows_transformed": self.execution.rows_transformed,
            "stages": [
                {
                    "stage": s.stage.value,
                    "status": s.status.value,
                    "duration_seconds": s.duration_seconds,
                    "record_count": s.record_count,
                    "error": s.error
                }
                for s in self.execution.stages
            ],
            "validations": [
                {
                    "rule_name": v.rule_name,
                    "passed": v.passed,
                    "level": v.level.value,
                    "message": v.message
                }
                for v in self.execution.validation_results
            ]
        }
