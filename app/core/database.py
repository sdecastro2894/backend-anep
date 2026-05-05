"""
Conexión a PostgreSQL (Supabase) usando SQLAlchemy 2.0.
Define el engine, la sesión y la base declarativa para los modelos ORM.
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import QueuePool

from app.core.config import settings


# ---------------------------------------------------------------------------
# Engine principal
# ---------------------------------------------------------------------------
# pool_pre_ping=True: SQLAlchemy verifica la conexión antes de usarla.
# Fundamental en entornos cloud donde las conexiones pueden caerse.
# pool_size=5, max_overflow=10: límites conservadores para el tier gratuito
# de Supabase (que tiene un máximo de ~20 conexiones simultáneas).
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=300,  # Recicla conexiones cada 5 minutos
    connect_args={
        "connect_timeout": 10,
        "options": "-c timezone=America/Montevideo",  # Zona horaria Uruguay 🇺🇾
    },
)

# ---------------------------------------------------------------------------
# Fábrica de sesiones
# ---------------------------------------------------------------------------
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,  # Control manual de transacciones
    autoflush=False,   # No flush automático antes de queries
    expire_on_commit=False,  # Los objetos siguen accesibles después del commit
)


# ---------------------------------------------------------------------------
# Base declarativa para los modelos ORM
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """
    Clase base que heredan todos los modelos ORM.
    SQLAlchemy 2.0 usa esta sintaxis (en lugar del antiguo declarative_base())
    """
    pass


# ---------------------------------------------------------------------------
# Dependency de FastAPI: sesión de base de datos por request
# ---------------------------------------------------------------------------
def get_db():
    """
    Generador que provee una sesión de DB por cada request HTTP.
    Garantiza que la sesión se cierre siempre, incluso si hay excepciones.

    Uso en un router:
        @router.get("/endpoint")
        def mi_endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()  # Rollback automático si algo falla
        raise
    finally:
        db.close()  # Siempre se cierra la sesión


def check_db_connection() -> bool:
    """
    Verifica que la conexión a la base de datos funciona.
    Útil para el endpoint de health check.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False