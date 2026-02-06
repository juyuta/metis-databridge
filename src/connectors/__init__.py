"""Connectors package - sources and sinks for data movement."""

from .base import (
    Column,
    Schema,
    DataRow,
    DataSet,
    DataType,
    Source,
    Sink,
    ConnectorRegistry,
)

# Import concrete implementations to register them
from . import postgres

__all__ = [
    "Column",
    "Schema",
    "DataRow",
    "DataSet",
    "DataType",
    "Source",
    "Sink",
    "ConnectorRegistry",
    "postgres",
]
