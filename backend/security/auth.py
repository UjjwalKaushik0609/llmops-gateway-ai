"""
Security utilities: JWT tokens, password hashing, API key encryption,
prompt injection detection, and PII masking.
"""
import re
import base64
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List

from jose import JWTError, jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet

from backend.config import settings
from backend.models.schemas import SecurityScanResult
import structlog

logger = structlog.get_logger()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ─── Password Utils ────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ─── JWT Utils ─────────────────────────────────────────────────────────────────

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(data: Dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError as e:
        logger.warning("JWT decode failed", error=str(e))
        return None


# ─── API Key Encryption ────────────────────────────────────────────────────────

def get_fernet() -> Fernet:
    """Get Fernet cipher from settings or generate a new key."""
    if settings.encryption_key:
        key = settings.encryption_key.encode()
        # Ensure it's valid base64
        try:
            Fernet(key)
            return Fernet(key)
        except Exception:
            pass
    # Generate and use a new key (for development)
    key = Fernet.generate_key()
    return Fernet(key)


_fernet = get_fernet()


def encrypt_api_key(api_key: str) -> str:
    """Encrypt an API key for storage."""
    return _fernet.encrypt(api_key.encode()).decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt an API key from storage."""
    return _fernet.decrypt(encrypted_key.encode()).decode()


# ─── Prompt Security Agent ─────────────────────────────────────────────────────

# Prompt injection patterns
INJECTION_PATTERNS = [
    r"ignore previous instructions",
    r"disregard (all |your |the )?instructions",
    r"forget (everything|all instructions)",
    r"you are now",
    r"act as (a |an )?(?!helpful|assistant)",
    r"pretend (you are|to be)",
    r"jailbreak",
    r"dan mode",
    r"developer mode",
    r"bypass (safety|filters|restrictions)",
    r"override (your|all) (safety|instructions|training)",
    r"system prompt",
    r"reveal (your|the) (system|original) (prompt|instructions)",
    r"</?system>",
    r"\[INST\]",
    r"###instruction###",
    r"prompt injection",
]

# PII patterns
PII_PATTERNS = {
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "phone": r"\b(\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    "ssn": r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b",
    "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
    "ip_address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
}

# Sensitive secret patterns (not PII, but must never reach an LLM provider)
SECRET_PATTERNS = {
    "api_key_pattern": r"\b(sk-|pk-|api-|key-)[A-Za-z0-9_\-]{20,}\b",
    "aws_key": r"\b(AKIA|ASIA)[A-Z0-9]{16}\b",
}

SENSITIVE_KEYWORDS = [
    "password", "passwd", "secret", "private key", "bearer token",
    "access token", "ssh key", "database uri", "connection string",
]


def scan_prompt(prompt: str) -> SecurityScanResult:
    """
    Scan a prompt for security issues:
    - Prompt injection attacks
    - PII (Personal Identifiable Information)
    - Sensitive data (API keys, passwords, etc.)
    """
    flags = []
    risk_score = 0.0
    sanitized = prompt

    # Check for prompt injection
    injection_detected = False
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, prompt, re.IGNORECASE):
            injection_detected = True
            flags.append(f"prompt_injection:{pattern[:30]}")
            risk_score += 0.4

    # Check for PII
    pii_detected = False
    pii_found = []
    for pii_type, pattern in PII_PATTERNS.items():
        matches = re.findall(pattern, prompt, re.IGNORECASE)
        if matches:
            pii_detected = True
            pii_found.append(pii_type)
            flags.append(f"pii:{pii_type}")
            risk_score += 0.2
            # Mask PII in sanitized prompt
            sanitized = re.sub(pattern, f"[REDACTED_{pii_type.upper()}]", sanitized, flags=re.IGNORECASE)

    # Check for sensitive secrets (API keys, AWS keys, etc.) via regex
    sensitive_detected = False
    for secret_type, pattern in SECRET_PATTERNS.items():
        matches = re.findall(pattern, prompt, re.IGNORECASE)
        if matches:
            sensitive_detected = True
            flags.append(f"secret:{secret_type}")
            risk_score += 0.3
            sanitized = re.sub(pattern, f"[REDACTED_{secret_type.upper()}]", sanitized, flags=re.IGNORECASE)

    # Check for sensitive keywords (password, private key, etc.)
    for keyword in SENSITIVE_KEYWORDS:
        if keyword.lower() in prompt.lower():
            sensitive_detected = True
            flags.append(f"sensitive_keyword:{keyword}")
            risk_score += 0.1

    risk_score = min(risk_score, 1.0)
    is_safe = risk_score < 0.4

    if injection_detected:
        logger.warning("Prompt injection detected", flags=flags)

    return SecurityScanResult(
        is_safe=is_safe,
        prompt_injection_detected=injection_detected,
        pii_detected=pii_detected,
        sensitive_data_detected=sensitive_detected,
        sanitized_prompt=sanitized,
        flags=flags,
        risk_score=round(risk_score, 2),
    )
