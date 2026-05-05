"""
Schemas Pydantic para configuración inicial del docente:
grupos, asignaciones y archivos base.
"""
import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Grupos
# ---------------------------------------------------------------------------
class GrupoCreate(BaseModel):
    """Datos para crear un nuevo grupo."""
    nombre: str          # ej: "8vo D"
    anio: str            # ej: "2025"
    institucion: str     # ej: "Liceo 5 Montevideo"

    @field_validator("nombre", "anio", "institucion")
    @classmethod
    def no_vacio(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El campo no puede estar vacío")
        return v.strip()


class GrupoUpdate(BaseModel):
    """Todos los campos son opcionales para actualización parcial."""
    nombre: str | None = None
    anio: str | None = None
    institucion: str | None = None


class GrupoResponse(BaseModel):
    """Respuesta con datos de un grupo."""
    id: uuid.UUID
    docente_id: uuid.UUID
    nombre: str
    anio: str
    institucion: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Asignaciones
# ---------------------------------------------------------------------------
DIAS_VALIDOS = {"Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"}


class AsignacionCreate(BaseModel):
    grupo_id: uuid.UUID
    materia: str
    horario: list[dict]  # [{"dia": "Lunes", "bloques": 2}, ...]
    minutos_por_hora_docente: int = 45

    @field_validator("materia")
    @classmethod
    def materia_no_vacia(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("La materia no puede estar vacía")
        return v.strip()

    @field_validator("minutos_por_hora_docente")
    @classmethod
    def minutos_validos(cls, v: int) -> int:
        if v < 30 or v > 120:
            raise ValueError("Los minutos por hora docente deben estar entre 30 y 120")
        return v

    @field_validator("horario")
    @classmethod
    def horario_valido(cls, v: list[dict]) -> list[dict]:
        if not v:
            raise ValueError("Debe especificar al menos un día en el horario")
        for bloque in v:
            if "dia" not in bloque or "bloques" not in bloque:
                raise ValueError("Cada bloque debe tener 'dia' y 'bloques'")
            if bloque["dia"] not in DIAS_VALIDOS:
                raise ValueError(f"Día inválido: {bloque['dia']}")
            if bloque["bloques"] < 1:
                raise ValueError("Los bloques deben ser mayor a 0")
        return v


class AsignacionUpdate(BaseModel):
    materia: str | None = None
    horario: list[dict] | None = None
    minutos_por_hora_docente: int | None = None


class AsignacionResponse(BaseModel):
    id: uuid.UUID
    docente_id: uuid.UUID
    grupo_id: uuid.UUID
    materia: str
    horario: list[dict]
    minutos_por_hora_docente: int
    total_minutos_semanales: int
    total_horas_docentes_semanales: float
    created_at: datetime
    grupo_nombre: str | None = None
    grupo_anio: str | None = None
    grupo_institucion: str | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_grupo(cls, asignacion) -> "AsignacionResponse":
        return cls(
            id=asignacion.id,
            docente_id=asignacion.docente_id,
            grupo_id=asignacion.grupo_id,
            materia=asignacion.materia,
            horario=asignacion.horario,
            minutos_por_hora_docente=asignacion.minutos_por_hora_docente,
            total_minutos_semanales=asignacion.total_minutos_semanales,
            total_horas_docentes_semanales=asignacion.total_horas_docentes_semanales,
            created_at=asignacion.created_at,
            grupo_nombre=asignacion.grupo.nombre if asignacion.grupo else None,
            grupo_anio=asignacion.grupo.anio if asignacion.grupo else None,
            grupo_institucion=asignacion.grupo.institucion if asignacion.grupo else None,
        )


# ---------------------------------------------------------------------------
# Archivos base
# ---------------------------------------------------------------------------
class ArchivoBaseResponse(BaseModel):
    """Respuesta tras subir un archivo a Supabase Storage."""
    id: uuid.UUID
    docente_id: uuid.UUID
    asignacion_id: uuid.UUID | None
    nombre: str
    tipo: str
    storage_path: str
    storage_url: str
    mime_type: str | None
    tamanio_bytes: int | None
    subido_at: datetime

    model_config = {"from_attributes": True}