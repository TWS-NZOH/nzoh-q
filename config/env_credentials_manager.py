"""
Environment-based Credentials Manager
Reads Salesforce credentials from environment variables (e.g. Azure App Service / Key Vault).
Used when SALESFORCE_USERNAME, SALESFORCE_PASSWORD, SALESFORCE_SECURITY_TOKEN are set.
"""

import os


# Env var names (match Azure App Service / Key Vault references)
ENV_USERNAME = "SALESFORCE_USERNAME"
ENV_PASSWORD = "SALESFORCE_PASSWORD"
ENV_SECURITY_TOKEN = "SALESFORCE_SECURITY_TOKEN"
ENV_ENVIRONMENT = "SALESFORCE_ENVIRONMENT"  # optional: 'live' (default) or 'uat'
ENV_USER_INITIALS = "NZOH_Q_USER_INITIALS"  # optional: initials to use on Azure when no Windows user


class EnvCredentialsManager:
    """Reads Salesforce credentials from environment variables."""

    def __init__(self):
        pass

    def is_available(self):
        """Return True if all required credential env vars are set."""
        return bool(
            os.environ.get(ENV_USERNAME)
            and os.environ.get(ENV_PASSWORD)
            and os.environ.get(ENV_SECURITY_TOKEN)
        )

    def get_credentials(self):
        """
        Get credentials from environment.

        Returns:
            dict with keys: username, password, security_token, environment
        """
        if not self.is_available():
            raise ValueError(
                f"Environment credentials not set. Required: {ENV_USERNAME}, {ENV_PASSWORD}, {ENV_SECURITY_TOKEN}"
            )
        environment = (os.environ.get(ENV_ENVIRONMENT) or "live").strip().lower()
        if environment not in ("live", "uat"):
            environment = "live"
        return {
            "username": os.environ[ENV_USERNAME].strip(),
            "password": os.environ[ENV_PASSWORD].strip(),
            "security_token": os.environ[ENV_SECURITY_TOKEN].strip(),
            "environment": environment,
        }

    def get_user_initials(self):
        """
        Return user initials when running in env-based mode (e.g. Azure).
        Uses NZOH_Q_USER_INITIALS if set; otherwise None (caller may treat as single-service identity).
        """
        raw = os.environ.get(ENV_USER_INITIALS)
        if not raw:
            return None
        return raw.strip().upper()
