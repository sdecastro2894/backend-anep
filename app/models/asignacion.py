"""
Modelo ORM para la tabla 'asignaciones'.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class Asignacion(Base):
    __tablename__ = "asignaciones"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    docente_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("docentes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    grupo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("grupos.id", ondelete="CASCADE"), nullable=False, index=True
    )

    materia: Mapped[str] = mapped_column(String(150), nullable=False)

    # horario = [
    #   {"dia": "Lunes",     "bloques": 2},
    #   {"dia": "Martes",    "bloques": 2},
    #   {"dia": "Miércoles", "bloques": 1},
    # ]
    horario: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)

    # Duración de UNA hora docente en esa institución (default 45)
    minutos_por_hora_docente: Mapped[int] = mapped_column(Integer, nullable=False, default=45)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # --- Relaciones ---
    docente: Mapped["Docente"] = relationship("Docente", back_populates="asignaciones")
    grupo: Mapped["Grupo"] = relationship("Grupo", back_populates="asignaciones")
    archivos: Mapped[list["ArchivoBase"]] = relationship(
        "ArchivoBase", back_populates="asignacion", cascade="all, delete-orphan"
    )
    planificaciones: Mapped[list["Planificacion"]] = relationship(
        "Planificacion", back_populates="asignacion", cascade="all, delete-orphan"
    )
    desarrollos_diarios: Mapped[list["DesarrolloDiario"]] = relationship(
        "DesarrolloDiario", back_populates="asignacion", cascade="all, delete-orphan"
    )

    @property
    def total_minutos_semanales(self) -> int:
        """Total de minutos de clase por semana."""
        return sum(bloque["bloques"] for bloque in self.horario) * self.minutos_por_hora_docente

    @property
    def total_horas_docentes_semanales(self) -> float:
        """Total en horas docentes."""
        return sum(bloque["bloques"] for bloque in self.horario)

    def __repr__(self) -> str:
        return f"<Asignacion {self.materia} | grupo_id={self.grupo_id}>"