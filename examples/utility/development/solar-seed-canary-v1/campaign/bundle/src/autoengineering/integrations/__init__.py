"""Framework-independent records for scientific integrations.

Importing this package never imports an optional scientific framework.
"""

from .contracts import ExternalTrialLink, IntegrationReceipt, IntegrationSpec

__all__ = ["ExternalTrialLink", "IntegrationReceipt", "IntegrationSpec"]
