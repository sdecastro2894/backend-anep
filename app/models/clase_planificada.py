"""
Modelo ORM para 'clases_planificadas'.
Representa cada clase individual dentro de una unidad.
"""
import uuid
from datetime import datetime, date
from sqlalchemy import String, DateTime, Integer, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class ClasePlanificada(Base):
    __tablename__ = "clases_planificadas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    unidad_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("unidades.id", ondelete="CASCADE"), nullable=False, index=True
    )

    numero_clase: Mapped[int] = mapped_column(Integer, nullable=False)  # Número dentro de la unidad
    fecha_estimada: Mapped[date | None] = mapped_column(Date, nullable=True)  # Puede calcularse después
    objetivo: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Estructura detallada de la clase generada por Gemini:
    # { intro_minutos: 10, desarrollo_minutos: 25, cierre_minutos: 10,
    #   actividades: [...], recursos: [...] }
    dinamica: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # "planificada" | "dada" | "emergente" | "postergada"
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="planificada")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # --- Relaciones ---
    unidad: Mapped["Unidad"] = relationship("Unidad", back_populates="clases")

    def __repr__(self) -> str:
        return f"<ClasePlanificada #{self.numero_clase} estado={self.estado}>"