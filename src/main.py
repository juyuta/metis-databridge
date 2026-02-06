"""
Metis DataBridge - Data migration and ETL framework.

Main entry point for pipeline execution.
"""

import sys
import logging
import json
from pathlib import Path
from typing import Optional

from config.loader import ConfigLoader


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def _resolve_config_path(config_or_job: str) -> str:
    """
    Resolve config path from either a full path or a job name.
    
    Args:
        config_or_job: Either a full path to pipeline.yml or a job name
        
    Returns:
        Full path to pipeline YAML configuration
        
    Examples:
        "01_customer_migration_simple" -> "jobs/01_customer_migration_simple/pipeline.yml"
        "jobs/01_customer_migration_simple/pipeline.yml" -> same path
        "/full/path/to/pipeline.yml" -> same path
    """
    path = Path(config_or_job)
    
    # If it's already a file path that exists, use it directly
    if path.exists() and path.is_file():
        return str(path)
    
    # If it looks like a full path but doesn't exist, try it anyway
    if str(path).endswith('.yml') or str(path).endswith('.yaml'):
        return str(path)
    
    # Otherwise, treat it as a job name and construct the path
    jobs_dir = Path(__file__).parent.parent / "jobs"
    job_config = jobs_dir / config_or_job / "pipeline.yml"
    
    if job_config.exists():
        logger.info(f"Resolved job '{config_or_job}' to: {job_config}")
        return str(job_config)
    
    # If job config doesn't exist, return the attempted path for error handling
    return str(job_config)


def run_pipeline(config_path: str, output_report: Optional[str] = None) -> int:
    """
    Execute a pipeline from configuration.
    
    Args:
        config_path: Path to pipeline YAML configuration or job name
        output_report: Optional path to save execution report JSON
        
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        # Resolve job name or config path
        resolved_config = _resolve_config_path(config_path)
        
        logger.info(f"Starting Metis DataBridge")
        logger.info(f"Configuration file: {resolved_config}")
        
        # Load configuration and build pipeline
        pipeline = ConfigLoader.build_pipeline(resolved_config)
        
        # Execute pipeline
        logger.info("Executing ELT pipeline...")
        execution = pipeline.execute()
        
        # Generate report
        report = pipeline.get_execution_report()
        
        logger.info(f"Pipeline execution completed with status: {execution.status.value}")
        
        # Print summary
        print("\n" + "="*60)
        print(f"Pipeline: {execution.pipeline_name}")
        print(f"Status: {execution.status.value.upper()}")
        print(f"Duration: {execution.duration_seconds():.2f}s" if execution.duration_seconds() else "N/A")
        print(f"Rows Extracted: {execution.rows_extracted}")
        print(f"Rows Loaded: {execution.rows_loaded}")
        print(f"Rows Transformed: {execution.rows_transformed}")
        print("="*60)
        
        # Print validation results
        if execution.validation_results:
            print("\nValidation Results:")
            for result in execution.validation_results:
                status = "✓ PASS" if result.passed else "✗ FAIL"
                print(f"  {status}: {result.rule_name} - {result.message}")
        
        # Save report if requested
        if output_report:
            report_path = Path(output_report)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(report_path, "w") as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Execution report saved to: {output_report}")
        
        # Return exit code based on success
        return 0 if execution.succeeded() else 1
    
    except Exception as e:
        logger.error(f"Pipeline execution failed: {str(e)}", exc_info=True)
        print(f"\nERROR: {str(e)}", file=sys.stderr)
        return 1


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Metis DataBridge - Data Migration & ETL Framework",
        prog="metis-databridge"
    )
    
    parser.add_argument(
        "config",
        help="Path to pipeline configuration YAML file or job name (e.g., '01_customer_migration_simple')"
    )
    
    parser.add_argument(
        "--report",
        "-r",
        help="Path to save execution report JSON",
        default=None
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run pipeline
    exit_code = run_pipeline(args.config, args.report)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
