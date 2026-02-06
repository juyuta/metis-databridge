"""
Configuration loader for pipeline definitions from YAML files.
"""

import yaml
import logging
from pathlib import Path
from pipelines import PipelineConfig
from typing import Any, Dict, Optional
from connectors.base import ConnectorRegistry, Source, Sink


logger = logging.getLogger(__name__)


class ConfigLoader:
    """Load and parse pipeline configurations from YAML files."""
    
    @staticmethod
    def load_config(config_path: str) -> PipelineConfig:
        """
        Load pipeline configuration from YAML file.
        
        Args:
            config_path: Path to YAML configuration file
            
        Returns:
            PipelineConfig instance
        """
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_path, "r") as f:
                raw_config = yaml.safe_load(f)
            
            logger.info(f"Loaded configuration from {config_path}")
            return ConfigLoader._parse_config(raw_config)
        
        except Exception as e:
            logger.error(f"Failed to load configuration: {str(e)}")
            raise
    
    @staticmethod
    def _parse_config(raw_config: Dict[str, Any]) -> PipelineConfig:
        """
        Parse raw YAML configuration into PipelineConfig.
        
        Expected YAML structure:
        
        pipeline:
          name: pipeline_name
          
        source:
          type: postgres
          config:
            host: localhost
            port: 5432
            database: mydb
            user: postgres
            password: secret
            table: source_table
        
        sink:
          type: postgres
          config:
            host: localhost
            port: 5432
            database: mydb
            user: postgres
            password: secret
            table_name: landing_table
        
        transformations:
          - type: rename
            mappings:
              old_col: new_col
          - type: cast
            column: amount
            to: float
        
        validations:
          - name: row_count_check
            type: row_count
            min: 1
            max: 10000
          - name: null_check
            type: null_check
            columns: [id, name]
        """
        
        # Validate top-level structure
        if "pipeline" not in raw_config:
            raise ValueError("Configuration must contain 'pipeline' section")
        
        if "source" not in raw_config:
            raise ValueError("Configuration must contain 'source' section")
        
        if "sink" not in raw_config:
            raise ValueError("Configuration must contain 'sink' section")
        
        # Parse pipeline metadata
        pipeline_section = raw_config.get("pipeline", {})
        pipeline_name = pipeline_section.get("name")
        
        if not pipeline_name:
            raise ValueError("pipeline.name is required")
        
        # Parse source
        source_section = raw_config.get("source", {})
        source_type = source_section.get("type")
        source_config = source_section.get("config", {})
        
        if not source_type:
            raise ValueError("source.type is required")
        
        # Parse sink
        sink_section = raw_config.get("sink", {})
        sink_type = sink_section.get("type")
        sink_config = sink_section.get("config", {})
        
        if not sink_type:
            raise ValueError("sink.type is required")
        
        # Parse transformations (optional)
        transformations = raw_config.get("transformations")
        
        # Parse validations (optional)
        validations = raw_config.get("validations")
        
        # Parse mapping file (optional)
        mapping_file = pipeline_section.get("mapping_file")
        
        # Parse SQL transformation file (optional)
        sql_transform_file = pipeline_section.get("sql_transform_file")
        
        # Parse metadata (optional)
        metadata = pipeline_section.get("metadata", {})
        
        return PipelineConfig(
            name=pipeline_name,
            source_type=source_type,
            source_config=source_config,
            sink_type=sink_type,
            sink_config=sink_config,
            transformations=transformations,
            validations=validations,
            mapping_file=mapping_file,
            sql_transform_file=sql_transform_file,
            metadata=metadata
        )
    
    @staticmethod
    def instantiate_source(config: PipelineConfig) -> Source:
        """
        Create Source instance from configuration.
        
        Args:
            config: PipelineConfig instance
            
        Returns:
            Instantiated Source
        """
        source_class = ConnectorRegistry.get_source(config.source_type)
        
        if not source_class:
            raise ValueError(f"Unknown source type: {config.source_type}")
        
        return source_class(
            name=f"{config.name}_source",
            config=config.source_config
        )
    
    @staticmethod
    def instantiate_sink(config: PipelineConfig) -> Sink:
        """
        Create Sink instance from configuration.
        
        Args:
            config: PipelineConfig instance
            
        Returns:
            Instantiated Sink
        """
        sink_class = ConnectorRegistry.get_sink(config.sink_type)
        
        if not sink_class:
            raise ValueError(f"Unknown sink type: {config.sink_type}")
        
        return sink_class(
            name=f"{config.name}_sink",
            config=config.sink_config
        )
    
    @staticmethod
    def build_pipeline(config_path: str) -> "Pipeline":
        """
        Load configuration and build complete Pipeline instance.
        
        Args:
            config_path: Path to YAML configuration file
            
        Returns:
            Instantiated Pipeline ready to execute
        """
        from pipelines import Pipeline
        
        # Load configuration
        config = ConfigLoader.load_config(config_path)
        
        # Instantiate connectors
        source = ConfigLoader.instantiate_source(config)
        sink = ConfigLoader.instantiate_sink(config)
        
        # Create pipeline
        pipeline = Pipeline(config, source, sink)
        
        logger.info(f"Built pipeline '{config.name}' from {config_path}")
        return pipeline
