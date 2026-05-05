"""
Modelo ORM para 'borradores_replanificacion'.
El sistema NUNCA modifica la planificación vigente automáticamente.
Genera un borrador y el docente decide qué hacer con él.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class BorradorReplanificacion(Base):
    __tablename__ = "borradores_replanificacion"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    planificacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("planificaciones.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # El contenido propuesto por Gemini para reemplazar (parcialmente) la planificación vigente
    contenido_propuesto: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # "pendiente" | "aprobado" | "rechazado" | "cambios_solicitados"
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="pendiente")

    # Explicación de por qué se generó este borrador
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Comentarios del docente al aprobar/rechazar/pedir cambios
    comentario_docente: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # --- Relaciones ---
    planificacion: Mapped["Planificacion"] = relationship("Planificacion", back_populates="borradores")

    def __repr__(self) -> str:
        return f"<BorradorReplanificacion estado={self.estado} plan_id={self.planificacion_id}>"