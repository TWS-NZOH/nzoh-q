"""
Salesforce Client Module
Handles Salesforce connections using environment variables (Azure App Service / Key Vault).
"""

from simple_salesforce import Salesforce
from pathlib import Path
import sys

# Add config to path
config_path = Path(__file__).parent.parent / "config"
sys.path.insert(0, str(config_path))

from env_credentials_manager import EnvCredentialsManager


class SalesforceClient:
    """Manages Salesforce connections using env vars (SALESFORCE_USERNAME, etc.)."""

    def __init__(self, config_dir=None):
        """Initialize Salesforce client. Requires Azure/env credentials to be set."""
        self.credentials_manager = EnvCredentialsManager()
        if not self.credentials_manager.is_available():
            raise ValueError(
                "Salesforce credentials not set. Configure SALESFORCE_USERNAME, "
                "SALESFORCE_PASSWORD, and SALESFORCE_SECURITY_TOKEN in App Service / Key Vault."
            )
        self.sf = None
        self._connected = False

    def connect(self):
        """
        Connect to Salesforce using env credentials.

        Returns:
            Salesforce connection object
        """
        if self._connected and self.sf is not None:
            return self.sf

        try:
            credentials = self.credentials_manager.get_credentials()

            if credentials["environment"] == "uat":
                self.sf = Salesforce(
                    username=credentials["username"],
                    password=credentials["password"],
                    security_token=credentials["security_token"],
                    domain="test",
                )
            else:
                self.sf = Salesforce(
                    username=credentials["username"],
                    password=credentials["password"],
                    security_token=credentials["security_token"],
                )

            self._connected = True
            return self.sf

        except Exception as e:
            raise ConnectionError(f"Failed to connect to Salesforce: {str(e)}")

    def get_connection(self):
        """Get or create Salesforce connection."""
        if not self._connected:
            return self.connect()
        return self.sf

    def test_connection(self):
        """Test the Salesforce connection."""
        try:
            sf = self.get_connection()
            result = sf.query("SELECT Id FROM User LIMIT 1")
            return True, "Connection successful"
        except Exception as e:
            return False, str(e)
