"""
Modelo ORM para 'desarrollo_diario'.
Registra lo que realmente pasó en cada clase.
Puede venir de Telegram (bot) o de edición manual en la web.
"""
import uuid
from datetime import datetime, date
from sqlalchemy import String, DateTime, Date, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class DesarrolloDiario(Base):
    __tablename__ = "desarrollo_diario"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asignacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("asignaciones.id", ondelete="CASCADE"), nullable=False, index=True
    )

    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Texto exacto que envió el docente (por Telegram o formulario web)
    texto_original: Mapped[str] = mapped_column(Text, nullable=False)

    # Texto procesado y estructurado por Gemini (1-2 párrafos formales)
    texto_estructurado: Mapped[str] = mapped_column(Text, nullable=False)

    # "telegram" | "manual"
    origen: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")

    # True cuando el docente revisó y aprobó el texto estructurado por Gemini
    revisado: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # --- Relaciones ---
    asignacion: Mapped["Asignacion"] = relationship("Asignacion", back_populates="desarrollos_diarios")

    def __repr__(self) -> str:
        return f"<DesarrolloDiario fecha={self.fecha} origen={self.origen}>"