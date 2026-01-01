"""
IBM IAM Token Manager
Handles automatic token generation and refresh for IBM Cloud services.
Tokens expire every 60 minutes, so we refresh 5 minutes before expiry.
"""

import os
import time
import requests
import threading
from typing import Optional


class TokenManager:
    """Manages IBM IAM tokens with automatic refresh."""
    
    IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"
    REFRESH_BUFFER_SECONDS = 300  # Refresh 5 minutes before expiry
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the token manager.
        
        Args:
            api_key: IBM Cloud API key. If not provided, reads from IBM_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("IBM_API_KEY")
        self._token: Optional[str] = None
        self._token_expiry: float = 0
        self._lock = threading.Lock()
        
        if not self.api_key:
            raise ValueError(
                "IBM API key not provided. Set IBM_API_KEY environment variable "
                "or pass api_key parameter."
            )
    
    def get_token(self) -> str:
        """
        Get a valid access token, refreshing if necessary.
        
        Returns:
            Valid IBM IAM access token.
            
        Raises:
            Exception: If token generation fails.
        """
        with self._lock:
            # Check if token is still valid (with buffer)
            if self._token and time.time() < (self._token_expiry - self.REFRESH_BUFFER_SECONDS):
                return self._token
            
            # Need to refresh token
            self._refresh_token()
            return self._token
    
    def _refresh_token(self) -> None:
        """Fetch a new token from IBM IAM."""
        try:
            response = requests.post(
                self.IAM_TOKEN_URL,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                    "apikey": self.api_key
                },
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            self._token = data["access_token"]
            # expires_in is in seconds, convert to absolute timestamp
            expires_in = data.get("expires_in", 3600)
            self._token_expiry = time.time() + expires_in
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to generate IBM IAM token: {str(e)}")
        except (KeyError, ValueError) as e:
            raise Exception(f"Invalid response from IBM IAM: {str(e)}")
    
    def get_token_info(self) -> dict:
        """
        Get information about the current token.
        
        Returns:
            Dict with token status information.
        """
        with self._lock:
            if not self._token:
                return {
                    "valid": False,
                    "message": "No token available"
                }
            
            time_remaining = self._token_expiry - time.time()
            if time_remaining <= 0:
                return {
                    "valid": False,
                    "message": "Token expired"
                }
            
            return {
                "valid": True,
                "expires_in_seconds": int(time_remaining),
                "expires_in_minutes": int(time_remaining / 60),
                "message": f"Token valid for {int(time_remaining / 60)} minutes"
            }
    
    def force_refresh(self) -> str:
        """
        Force a token refresh regardless of expiry.
        
        Returns:
            New access token.
        """
        with self._lock:
            self._refresh_token()
            return self._token


# Singleton instance for app-wide use
_token_manager: Optional[TokenManager] = None


def get_token_manager() -> TokenManager:
    """
    Get the singleton TokenManager instance.
    
    Returns:
        TokenManager instance.
    """
    global _token_manager
    if _token_manager is None:
        _token_manager = TokenManager()
    return _token_manager


def get_bearer_token() -> str:
    """
    Convenience function to get a Bearer token string.
    
    Returns:
        Bearer token string ready for Authorization header.
    """
    manager = get_token_manager()
    return f"Bearer {manager.get_token()}"

