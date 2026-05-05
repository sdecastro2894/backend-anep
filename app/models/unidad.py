"""
Modelo ORM para 'unidades'.
Cada unidad temática pertenece a una planificación anual o por_unidad.
Implementa la regla del 15% de clases para emergentes.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Unidad(Base):
    __tablename__ = "unidades"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    planificacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("planificaciones.id", ondelete="CASCADE"), nullable=False, index=True
    )

    titulo: Mapped[str] = mapped_column(String(200), nullable=False)  # ej: "Ecuaciones de primer grado"
    orden: Mapped[int] = mapped_column(Integer, nullable=False)  # Posición en la planificación anual

    # Total de clases planificadas para esta unidad
    clases_totales: Mapped[int] = mapped_column(Integer, nullable=False)

    # Clases reservadas para emergentes (por defecto: 15% de clases_totales, redondeado)
    # El docente puede editar este valor en porcentaje o cantidad directa
    clases_emergentes: Mapped[int] = mapped_column(Integer, nullable=False)
    porcentaje_emergentes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)

    # ¿Incluye evaluación en esta unidad?
    tiene_evaluacion: Mapped[bool] = mapped_column(Boolean, default=False)
    # "formativa" | "sumativa" | "ambas" | None
    tipo_evaluacion: Mapped[str | None] = mapped_column(String(20), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # --- Relaciones ---
    planificacion: Mapped["Planificacion"] = relationship("Planificacion", back_populates="unidades")
    clases: Mapped[list["ClasePlanificada"]] = relationship(
        "ClasePlanificada", back_populates="unidad", cascade="all, delete-orphan"
    )

    @property
    def clases_efectivas(self) -> int:
        """Clases disponibles para contenido real (sin emergentes)."""
        return self.clases_totales - self.clases_emergentes

    def __repr__(self) -> str:
        return f"<Unidad '{self.titulo}' orden={self.orden}>"