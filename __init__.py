"""
GovBizOps - Python library for collecting government contract opportunities
"""

__version__ = "0.1.0"

from .client import SAMGovClient
from .collector import OpportunityCollector

__all__ = ["SAMGovClient", "OpportunityCollector"]