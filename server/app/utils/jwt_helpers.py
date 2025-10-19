"""JWT token helper functions."""
from datetime import datetime, timezone, timedelta
import jwt
import logging

from config import secret_key, access_token_expire_sec, refresh_token_expire_sec


def encode_jwt_token(user_id, expires_in_seconds):
    """
    Encode a JWT token with user_id and expiration.
    
    Args:
        user_id: User ID to encode in token
        expires_in_seconds: Token expiration time in seconds
        
    Returns:
        str: Encoded JWT token
        
    Raises:
        jwt.PyJWTError: If encoding fails
    """
    try:
        payload = {
            "user_id": user_id,
            "exp": datetime.now(tz=timezone.utc) + timedelta(seconds=expires_in_seconds)
        }
        token = jwt.encode(payload, secret_key, algorithm="HS256")
        return token
    except jwt.PyJWTError as e:
        logging.error(f"JWT encoding error: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"Error encoding JWT token: {str(e)}")
        raise


def decode_jwt_token(token):
    """
    Decode and verify a JWT token.
    
    Args:
        token: JWT token string to decode
        
    Returns:
        dict: Decoded payload with user_id, or None if invalid/expired
        
    Note:
        Returns None for expired or invalid tokens (logs warning).
        Re-raises other exceptions.
    """
    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        user_id = payload.get("user_id")
        if not user_id:
            logging.warning("JWT token missing required field: user_id")
            return None
        return payload
    except jwt.ExpiredSignatureError:
        logging.warning("JWT token expired")
        return None
    except jwt.InvalidTokenError:
        logging.warning("Invalid JWT token")
        return None
    except Exception as e:
        logging.error(f"Error decoding JWT token: {str(e)}")
        raise


def generate_access_token(user_id, expires_in=None):
    """
    Generate an access token for a user.
    
    Args:
        user_id: User ID
        expires_in: Optional expiration time in seconds (uses config default if None)
        
    Returns:
        str: JWT access token
    """
    if expires_in is None:
        expires_in = access_token_expire_sec
    return encode_jwt_token(user_id, expires_in)


def generate_refresh_token_jwt(user_id, expires_in=None):
    """
    Generate a refresh token JWT (without saving to DB).
    
    Args:
        user_id: User ID
        expires_in: Optional expiration time in seconds (uses config default if None)
        
    Returns:
        str: JWT refresh token
    """
    if expires_in is None:
        expires_in = refresh_token_expire_sec
    return encode_jwt_token(user_id, expires_in)


def verify_token_and_get_user_id(token):
    """
    Verify token and extract user_id.
    
    Args:
        token: JWT token string
        
    Returns:
        str: user_id if valid, None if invalid/expired
    """
    payload = decode_jwt_token(token)
    if payload:
        return payload.get("user_id")
    return None
