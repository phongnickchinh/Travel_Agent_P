"""
Google OAuth helper functions for verifying tokens and getting user information.
"""

import logging
from typing import Optional, Dict
from google.oauth2 import id_token
from google.auth.transport import requests
from config import google_client_id

logger = logging.getLogger(__name__)


def verify_google_token(token: str) -> Optional[Dict]:
    """
    Verify Google ID token and return user information.
    
    Args:
        token: Google ID token from client
        
    Returns:
        Dictionary containing user info if valid, None otherwise
        {
            'sub': 'google_user_id',
            'email': 'user@gmail.com',
            'name': 'Full Name',
            'picture': 'https://...',
            'email_verified': True
        }
    """
    try:
        # Verify the token
        idinfo = id_token.verify_oauth2_token(
            token, 
            requests.Request(), 
            google_client_id
        )
        
        # Verify that the token was issued by Google
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            logger.warning("Invalid issuer in Google token")
            return None
            
        # Token is valid, return user info
        return {
            'sub': idinfo.get('sub'),  # Google user ID
            'email': idinfo.get('email'),
            'name': idinfo.get('name'),
            'picture': idinfo.get('picture'),
            'email_verified': idinfo.get('email_verified', False),
            'given_name': idinfo.get('given_name'),
            'family_name': idinfo.get('family_name'),
        }
        
    except ValueError as e:
        # Invalid token
        logger.error(f"Invalid Google token: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error verifying Google token: {str(e)}")
        return None


def get_google_user_info(token: str) -> Optional[Dict]:
    """
    Get Google user information from access token.
    This is an alternative method if using access token instead of ID token.
    
    Args:
        token: Google access token
        
    Returns:
        Dictionary containing user info if successful, None otherwise
    """
    try:
        import requests as http_requests
        
        # Call Google's userinfo endpoint
        response = http_requests.get(
            'https://www.googleapis.com/oauth2/v3/userinfo',
            headers={'Authorization': f'Bearer {token}'}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to get Google user info: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Error getting Google user info: {str(e)}")
        return None


def generate_username_from_email(email: str) -> str:
    """
    Generate a unique username from email address.
    
    Args:
        email: Email address
        
    Returns:
        Username derived from email
    """
    import re
    import random
    import string
    
    # Extract username part from email
    username = email.split('@')[0]
    
    # Remove special characters, keep only alphanumeric and underscore
    username = re.sub(r'[^\w]', '_', username)
    
    # Add random suffix to avoid collisions
    random_suffix = ''.join(random.choices(string.digits, k=4))
    username = f"{username}_{random_suffix}"
    
    return username[:100]  # Limit to 100 characters


def generate_device_id_for_oauth() -> str:
    """
    Generate a device ID for OAuth users who don't provide one.
    
    Returns:
        Generated device ID
    """
    import uuid
    return f"oauth_{uuid.uuid4().hex[:16]}"
