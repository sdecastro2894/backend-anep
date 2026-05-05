"""
Modelo ORM para la tabla 'docentes'.
Representa a cada usuario/docente registrado en el sistema.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, BigInteger, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Docente(Base):
    __tablename__ = "docentes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # chat_id de Telegram. Nullable porque el docente puede registrarse
    # por la web antes de vincular su cuenta de Telegram.
    telegram_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, unique=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # --- Relaciones ---
    grupos: Mapped[list["Grupo"]] = relationship(
        "Grupo", back_populates="docente", cascade="all, delete-orphan"
    )
    asignaciones: Mapped[list["Asignacion"]] = relationship(
        "Asignacion", back_populates="docente", cascade="all, delete-orphan"
    )
    archivos: Mapped[list["ArchivoBase"]] = relationship(
        "ArchivoBase", back_populates="docente", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Docente id={self.id} email={self.email}>"