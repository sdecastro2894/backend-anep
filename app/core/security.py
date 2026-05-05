"""
Utilidades de seguridad: hashing de contraseñas y manejo de tokens JWT.
"""
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ---------------------------------------------------------------------------
# Hashing de contraseñas con bcrypt
# ---------------------------------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

def hash_password(password: str) -> str:
    """Genera el hash bcrypt de una contraseña en texto plano."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si una contraseña en texto plano coincide con su hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# Tokens JWT
# ---------------------------------------------------------------------------
def create_access_token(
    subject: str | Any,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Genera un JWT firmado con el SECRET_KEY.

    Args:
        subject: Identificador del usuario (usamos el email o el UUID).
        expires_delta: Tiempo de expiración. Si no se pasa, usa el default del config.

    Returns:
        Token JWT como string.
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)

    expire = datetime.now(timezone.utc) + expires_delta

    payload = {
        "sub": str(subject),  # Subject: identificador del usuario
        "exp": expire,        # Expiration time
        "iat": datetime.now(timezone.utc),  # Issued at
    }

    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict | None:
    """
    Decodifica y valida un JWT.

    Returns:
        El payload del token si es válido, None si es inválido o expirado.
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        return payload
    except JWTError:
        return None