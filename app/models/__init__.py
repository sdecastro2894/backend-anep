# Importar todos los modelos aquí para que Alembic los detecte automáticamente
from app.models.docente import Docente
from app.models.grupo import Grupo
from app.models.asignacion import Asignacion
from app.models.archivo import ArchivoBase
from app.models.planificacion import Planificacion
from app.models.unidad import Unidad
from app.models.clase_planificada import ClasePlanificada
from app.models.desarrollo_diario import DesarrolloDiario
from app.models.borrador_replanificacion import BorradorReplanificacion

__all__ = [
    "Docente", "Grupo", "Asignacion", "ArchivoBase",
    "Planificacion", "Unidad", "ClasePlanificada",
    "DesarrolloDiario", "BorradorReplanificacion",
]