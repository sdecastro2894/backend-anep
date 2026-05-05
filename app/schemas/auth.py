"""
Schemas Pydantic para autenticación.
Definen la estructura de los datos que entran y salen de los endpoints de auth.
"""
import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator


# ---------------------------------------------------------------------------
# Registro
# ---------------------------------------------------------------------------
class DocenteCreate(BaseModel):
    """Datos necesarios para registrar un nuevo docente."""
    nombre: str
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return v

    @field_validator("nombre")
    @classmethod
    def nombre_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El nombre no puede estar vacío")
        return v.strip()


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
class LoginRequest(BaseModel):
    """Credenciales para iniciar sesión."""
    email: EmailStr
    password: str


# ---------------------------------------------------------------------------
# Respuestas
# ---------------------------------------------------------------------------
class TokenResponse(BaseModel):
    """Respuesta del endpoint de login con el JWT."""
    access_token: str
    token_type: str = "bearer"
    docente_id: uuid.UUID
    nombre: str
    email: str


class DocenteResponse(BaseModel):
    """Datos públicos de un docente (sin contraseña)."""
    id: uuid.UUID
    nombre: str
    email: str
    telegram_chat_id: int | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}  # Permite crear desde objetos ORM


# ---------------------------------------------------------------------------
# Vincular Telegram
# ---------------------------------------------------------------------------
class TelegramLinkRequest(BaseModel):
    """Para vincular el chat_id de Telegram al docente."""
    telegram_chat_id: int