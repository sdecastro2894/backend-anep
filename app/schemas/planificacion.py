"""
Schemas Pydantic para planificaciones generadas por Gemini.
"""
import uuid
from datetime import datetime
from pydantic import BaseModel, field_validator


# ===========================================================================
# Planificación Anual
# ===========================================================================

class PlanificacionAnualRequest(BaseModel):
    """Request para generar una planificación anual."""
    asignacion_id: uuid.UUID
    directivas: str = ""           # Indicaciones libres del docente
    semanas_lectivas: int = 38     # Uruguay: ~38 semanas lectivas
    porcentaje_emergentes: int = 15  # % de clases para emergentes

    @field_validator("semanas_lectivas")
    @classmethod
    def semanas_validas(cls, v: int) -> int:
        if v < 10 or v > 52:
            raise ValueError("Las semanas lectivas deben estar entre 10 y 52")
        return v

    @field_validator("porcentaje_emergentes")
    @classmethod
    def porcentaje_valido(cls, v: int) -> int:
        if v < 0 or v > 50:
            raise ValueError("El porcentaje de emergentes debe estar entre 0 y 50")
        return v


# ===========================================================================
# Planificación por Unidad
# ===========================================================================

class PlanificacionUnidadRequest(BaseModel):
    """Request para generar la planificación de una unidad."""
    asignacion_id: uuid.UUID
    titulo_unidad: str
    horas_docentes: int             # Horas asignadas a esta unidad
    porcentaje_emergentes: int = 15
    incluir_evaluacion: bool = False
    tipo_evaluacion: str | None = None  # "formativa" | "sumativa" | "ambas"
    contenidos: list[str] = []
    objetivos: list[str] = []

    @field_validator("tipo_evaluacion")
    @classmethod
    def tipo_evaluacion_valido(cls, v: str | None) -> str | None:
        if v and v not in ("formativa", "sumativa", "ambas"):
            raise ValueError("tipo_evaluacion debe ser: formativa, sumativa o ambas")
        return v


# ===========================================================================
# Planificación Diaria
# ===========================================================================

class PlanificacionDiariaRequest(BaseModel):
    """Request para generar la planificación de una clase individual."""
    asignacion_id: uuid.UUID
    titulo_clase: str
    objetivo: str
    contenido_principal: str
    estrategia_sugerida: str = ""
    duracion_minutos: int = 45
    contexto_clases_anteriores: str = ""  # Resumen de clases previas


# ===========================================================================
# Respuestas de Planificación
# ===========================================================================

class PlanificacionResponse(BaseModel):
    """Respuesta con los datos de una planificación guardada."""
    id: uuid.UUID
    asignacion_id: uuid.UUID
    tipo: str
    version: int
    contenido: dict
    estado: str
    notas_docente: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PlanificacionListResponse(BaseModel):
    """Respuesta resumida para listar planificaciones."""
    id: uuid.UUID
    asignacion_id: uuid.UUID
    tipo: str
    version: int
    estado: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ===========================================================================
# Borrador de Replanificación
# ===========================================================================

class BorradorAccionRequest(BaseModel):
    """Para aprobar, rechazar o pedir cambios en un borrador."""
    accion: str   # "aprobar" | "rechazar" | "cambios"
    comentario: str = ""

    @field_validator("accion")
    @classmethod
    def accion_valida(cls, v: str) -> str:
        if v not in ("aprobar", "rechazar", "cambios"):
            raise ValueError("accion debe ser: aprobar, rechazar o cambios")
        return v