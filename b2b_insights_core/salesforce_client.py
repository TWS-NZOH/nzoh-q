"""
Salesforce Client Module
Handles Salesforce connections using embedded encrypted credentials
"""

from simple_salesforce import Salesforce
from pathlib import Path
import sys

# Add config to path
config_path = Path(__file__).parent.parent / 'config'
sys.path.insert(0, str(config_path))

try:
    from embedded_credentials_manager import EmbeddedCredentialsManager
except ImportError:
    # Fallback to old credentials manager if embedded not available
    from credentials_manager import CredentialsManager
    EmbeddedCredentialsManager = None

class SalesforceClient:
    """Manages Salesforce connections with embedded encrypted credentials"""
    
    def __init__(self, config_dir=None):
        """
        Initialize Salesforce client
        
        Args:
            config_dir: Directory containing credentials (optional, for fallback)
        """
        # Try embedded credentials first
        if EmbeddedCredentialsManager:
            try:
                self.credentials_manager = EmbeddedCredentialsManager()
                self.use_embedded = True
            except Exception:
                # Fallback to file-based credentials
                from credentials_manager import CredentialsManager
                self.credentials_manager = CredentialsManager(config_dir)
                self.use_embedded = False
        else:
            from credentials_manager import CredentialsManager
            self.credentials_manager = CredentialsManager(config_dir)
            self.use_embedded = False
        
        self.sf = None
        self._connected = False
    
    def connect(self):
        """
        Connect to Salesforce using embedded or stored credentials
        
        Returns:
            Salesforce connection object
        """
        if self._connected and self.sf is not None:
            return self.sf
        
        try:
            if self.use_embedded:
                credentials = self.credentials_manager.get_credentials()
            else:
                credentials = self.credentials_manager.load_credentials()
            
            if credentials['environment'] == 'uat':
                self.sf = Salesforce(
                    username=credentials['username'],
                    password=credentials['password'],
                    security_token=credentials['security_token'],
                    domain='test'
                )
            else:
                self.sf = Salesforce(
                    username=credentials['username'],
                    password=credentials['password'],
                    security_token=credentials['security_token']
                )
            
            self._connected = True
            return self.sf
            
        except PermissionError as e:
            raise PermissionError(str(e))
        except FileNotFoundError:
            raise FileNotFoundError(
                "Credentials not configured. Please run the setup script first."
            )
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Salesforce: {str(e)}")
    
    def get_connection(self):
        """Get or create Salesforce connection"""
        if not self._connected:
            return self.connect()
        return self.sf
    
    def test_connection(self):
        """Test the Salesforce connection"""
        try:
            sf = self.get_connection()
            # Simple query to test connection
            result = sf.query("SELECT Id FROM User LIMIT 1")
            return True, "Connection successful"
        except Exception as e:
            return False, str(e)
    
    def get_user_initials(self):
        """Get user initials from Windows username (if using embedded credentials)"""
        if self.use_embedded and hasattr(self.credentials_manager, 'get_user_initials'):
            return self.credentials_manager.get_user_initials()
        return None

