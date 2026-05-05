"""
Modelo ORM para la tabla 'grupos'.
Un grupo es una clase o grupo de alumnos (ej: "8vo D", "3er Año Informática").
"""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Grupo(Base):
    __tablename__ = "grupos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    docente_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("docentes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)  # ej: "8vo D"
    anio: Mapped[str] = mapped_column(String(20), nullable=False)     # ej: "2025"
    institucion: Mapped[str] = mapped_column(String(200), nullable=False)  # ej: "Liceo 5 Montevideo"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # --- Relaciones ---
    docente: Mapped["Docente"] = relationship("Docente", back_populates="grupos")
    asignaciones: Mapped[list["Asignacion"]] = relationship(
        "Asignacion", back_populates="grupo", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Grupo {self.nombre} {self.anio}>"