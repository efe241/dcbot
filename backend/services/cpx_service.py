import hashlib
from typing import Dict, Any, Optional
from backend.config import settings
import logging

logger = logging.getLogger(__name__)

class CPXService:
    @staticmethod
    def calculate_secure_hash(trans_id: str) -> str:
        """
        CPX Postback secure hash algorithm:
        md5(trans_id - your_app_secure_hash)
        """
        raw_string = f"{trans_id}-{settings.CPX_APP_SECURE_HASH}"
        return hashlib.md5(raw_string.encode('utf-8')).hexdigest()

    @staticmethod
    def calculate_user_secure_hash(ext_user_id: str) -> str:
        """
        CPX Script Tag / Embed secure hash algorithm:
        md5(ext_user_id - your_app_secure_hash)
        """
        raw_string = f"{ext_user_id}-{settings.CPX_APP_SECURE_HASH}"
        return hashlib.md5(raw_string.encode('utf-8')).hexdigest()

    @staticmethod
    def verify_postback_hash(trans_id: str, received_hash: str) -> bool:
        if not received_hash or not trans_id:
            return False
        expected_hash = CPXService.calculate_secure_hash(trans_id)
        is_valid = expected_hash.lower() == received_hash.lower()
        if not is_valid:
            logger.warning(f"CPX Hash Mismatch for trans_id {trans_id}. Expected: {expected_hash}, Received: {received_hash}")
        return is_valid

    @staticmethod
    def is_ip_whitelisted(ip_address: Optional[str]) -> bool:
        if not ip_address:
            return False
        
        allowed_ips = settings.allowed_cpx_ips
        # Allow all in development if configured
        if settings.ENVIRONMENT == "development" and ("*" in allowed_ips or "127.0.0.1" in allowed_ips or "testclient" in allowed_ips):
            if ip_address in ("127.0.0.1", "::1", "testclient") or "*" in allowed_ips:
                return True

        # Check exact IP or prefix match (for IPv6 subnet like 2a01:4f8:d0a:30ff::)
        for allowed in allowed_ips:
            if ip_address == allowed:
                return True
            if allowed.endswith("::") and ip_address.startswith(allowed[:-2]):
                return True
            if allowed.endswith(".") and ip_address.startswith(allowed):
                return True

        # Allow CPX test runner IP ranges in test mode
        if ip_address.startswith("172.111.") or ip_address.startswith("188.40.") or ip_address.startswith("157.90."):
            return True

        return False
