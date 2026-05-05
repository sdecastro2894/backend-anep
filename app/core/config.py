"""
Configuración central de la aplicación.
Usa Pydantic Settings para leer variables de entorno desde .env
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """
    Todas las variables de entorno que necesita la app.
    Pydantic las lee automáticamente desde el archivo .env
    o desde las variables de entorno del sistema (Render).
    """

    # --- Entorno ---
    environment: str = "development"
    secret_key: str  # Clave para firmar JWT. Obligatoria.
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 días

    # --- Base de datos (Supabase PostgreSQL) ---
    database_url: str  # postgresql://usuario:pass@host:5432/db

    # --- Supabase (Storage + cliente SDK) ---
    supabase_url: str
    supabase_anon_key: str
    supabase_service_key: str  # Permisos elevados para operaciones de Storage

    # --- Google Gemini ---
    gemini_api_key: str

    # --- Telegram ---
    telegram_bot_token: str
    render_url: str = ""  # URL pública de Render, ej: https://mi-app.onrender.com

    # --- Nombres de buckets en Supabase Storage ---
    bucket_anep: str = "archivos-anep"
    bucket_fichas: str = "fichas-docente"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,  # DATABASE_URL == database_url
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Retorna la instancia de Settings cacheada.
    Usar lru_cache evita releer el .env en cada request.
    Uso: from app.core.config import get_settings; settings = get_settings()
    """
    return Settings()


# Instancia global para importar directamente en otros módulos
settings = get_settings()