"""
Modelo ORM para 'planificaciones'.
Soporta los tres tipos: anual, por_unidad, diaria.
Tiene versionado: nunca se sobreescribe, se crea una nueva versión.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class Planificacion(Base):
    __tablename__ = "planificaciones"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asignacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("asignaciones.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # "anual" | "por_unidad" | "diaria"
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)

    # Versionado: la versión más alta es la vigente
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # El contenido estructurado generado por Gemini, adaptado según el tipo:
    # - anual: { objetivos_generales, objetivos_especificos, cronograma_macro }
    # - por_unidad: { titulo, clases, evaluaciones, porcentaje_emergentes }
    # - diaria: { objetivo, dinamica, cronograma_minutos, recursos }
    contenido: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # "borrador" | "vigente" | "archivada"
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="borrador")

    notas_docente: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # --- Relaciones ---
    asignacion: Mapped["Asignacion"] = relationship("Asignacion", back_populates="planificaciones")
    unidades: Mapped[list["Unidad"]] = relationship(
        "Unidad", back_populates="planificacion", cascade="all, delete-orphan"
    )
    borradores: Mapped[list["BorradorReplanificacion"]] = relationship(
        "BorradorReplanificacion", back_populates="planificacion", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Planificacion tipo={self.tipo} v{self.version} estado={self.estado}>"