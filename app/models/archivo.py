"""
Modelo ORM para 'archivos_base'.
Registra los metadatos de archivos subidos a Supabase Storage.
El archivo REAL vive en Supabase Storage; acá guardamos la referencia.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class ArchivoBase(Base):
    __tablename__ = "archivos_base"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    docente_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("docentes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Nullable: un archivo puede ser general (sin asignación específica) o para una asignación concreta
    asignacion_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("asignaciones.id", ondelete="SET NULL"), nullable=True, index=True
    )

    nombre: Mapped[str] = mapped_column(String(255), nullable=False)  # Nombre original del archivo
    tipo: Mapped[str] = mapped_column(
        String(20), nullable=False
        # Valores posibles: "anep_pdf", "anep_word", "anep_txt", "ficha_docente"
    )
    storage_path: Mapped[str] = mapped_column(
        Text, nullable=False
        # Ruta dentro del bucket. ej: "docente_uuid/2025/matematicas/programa.pdf"
    )
    storage_url: Mapped[str] = mapped_column(
        Text, nullable=False
        # URL firmada o pública para acceder al archivo en Supabase Storage
    )
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tamanio_bytes: Mapped[int | None] = mapped_column(nullable=True)

    subido_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # --- Relaciones ---
    docente: Mapped["Docente"] = relationship("Docente", back_populates="archivos")
    asignacion: Mapped["Asignacion | None"] = relationship("Asignacion", back_populates="archivos")

    def __repr__(self) -> str:
        return f"<ArchivoBase {self.nombre} tipo={self.tipo}>"