"""
Router de planificaciones.
Endpoints para generar y gestionar planificaciones con Gemini.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.docente import Docente
from app.models.asignacion import Asignacion
from app.models.planificacion import Planificacion
from app.models.unidad import Unidad
from app.models.clase_planificada import ClasePlanificada
from app.models.borrador_replanificacion import BorradorReplanificacion
from app.routers.auth import get_current_docente
from app.schemas.planificacion import (
    PlanificacionAnualRequest,
    PlanificacionUnidadRequest,
    PlanificacionDiariaRequest,
    PlanificacionResponse,
    PlanificacionListResponse,
    BorradorAccionRequest,
)
from app.services import gemini as gemini_service

router = APIRouter()


# ===========================================================================
# PLANIFICACIÓN ANUAL
# ===========================================================================

@router.post(
    "/anual",
    response_model=PlanificacionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generar planificación anual con Gemini",
)
def generar_planificacion_anual(
    payload: PlanificacionAnualRequest,
    docente: Docente = Depends(get_current_docente),
    db: Session = Depends(get_db),
):
    """
    Genera una planificación anual completa usando Gemini.
    Toma en cuenta la carga horaria real y el porcentaje de emergentes.
    """
    asignacion = _get_asignacion_o_404(payload.asignacion_id, docente.id, db)

    # Calcular próxima versión
    version = _get_proxima_version(payload.asignacion_id, "anual", db)

    # Generar con Gemini
    try:
        contenido = gemini_service.generar_planificacion_anual(
            asignacion=asignacion,
            directivas=payload.directivas,
            semanas_lectivas=payload.semanas_lectivas,
            porcentaje_emergentes=payload.porcentaje_emergentes,
            db=db,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Error al comunicarse con Gemini: {str(e)}",
        )

    # Guardar planificación (estado borrador)
    planificacion = Planificacion(
        asignacion_id=payload.asignacion_id,
        tipo="anual",
        version=version,
        contenido=contenido,
        estado="borrador",
    )
    db.add(planificacion)
    db.flush()

    # Crear registros de unidades si Gemini las generó correctamente
    if "unidades" in contenido and isinstance(contenido["unidades"], list):
        for u in contenido["unidades"]:
            horas = u.get("horas_docentes", 0)
            emergentes = max(1, int(horas * payload.porcentaje_emergentes / 100))
            unidad = Unidad(
                planificacion_id=planificacion.id,
                titulo=u.get("titulo", "Sin título"),
                orden=u.get("orden", 1),
                clases_totales=horas,
                clases_emergentes=emergentes,
                porcentaje_emergentes=payload.porcentaje_emergentes,
                tiene_evaluacion=False,
            )
            db.add(unidad)

    db.commit()
    db.refresh(planificacion)
    return planificacion


@router.get(
    "/anual/{asignacion_id}",
    response_model=list[PlanificacionListResponse],
    summary="Listar planificaciones anuales de una asignación",
)
def listar_planificaciones_anuales(
    asignacion_id: uuid.UUID,
    docente: Docente = Depends(get_current_docente),
    db: Session = Depends(get_db),
):
    _get_asignacion_o_404(asignacion_id, docente.id, db)
    return db.query(Planificacion).filter(
        Planificacion.asignacion_id == asignacion_id,
        Planificacion.tipo == "anual",
    ).order_by(Planificacion.version.desc()).all()


# ===========================================================================
# PLANIFICACIÓN POR UNIDAD
# ===========================================================================

@router.post(
    "/unidad",
    response_model=PlanificacionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generar planificación de una unidad con Gemini",
)
def generar_planificacion_unidad(
    payload: PlanificacionUnidadRequest,
    docente: Docente = Depends(get_current_docente),
    db: Session = Depends(get_db),
):
    """
    Genera la planificación detallada de una unidad temática.
    Implementa la regla del porcentaje de emergentes configurable.
    """
    asignacion = _get_asignacion_o_404(payload.asignacion_id, docente.id, db)
    version = _get_proxima_version(payload.asignacion_id, "por_unidad", db)

    try:
        contenido = gemini_service.generar_planificacion_unidad(
            asignacion=asignacion,
            titulo_unidad=payload.titulo_unidad,
            horas_docentes=payload.horas_docentes,
            porcentaje_emergentes=payload.porcentaje_emergentes,
            incluir_evaluacion=payload.incluir_evaluacion,
            tipo_evaluacion=payload.tipo_evaluacion,
            contenidos=payload.contenidos,
            objetivos=payload.objetivos,
            db=db,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Error al comunicarse con Gemini: {str(e)}",
        )

    planificacion = Planificacion(
        asignacion_id=payload.asignacion_id,
        tipo="por_unidad",
        version=version,
        contenido=contenido,
        estado="borrador",
    )
    db.add(planificacion)

    # Crear unidad y clases planificadas
    if "clases" in contenido:
        emergentes = max(1, int(payload.horas_docentes * payload.porcentaje_emergentes / 100))
        unidad = Unidad(
            planificacion_id=planificacion.id,
            titulo=payload.titulo_unidad,
            orden=1,
            clases_totales=payload.horas_docentes,
            clases_emergentes=emergentes,
            porcentaje_emergentes=payload.porcentaje_emergentes,
            tiene_evaluacion=payload.incluir_evaluacion,
            tipo_evaluacion=payload.tipo_evaluacion,
        )
        db.add(unidad)
        db.flush()  # Para obtener el id de la unidad

        for clase_data in contenido["clases"]:
            clase = ClasePlanificada(
                unidad_id=unidad.id,
                numero_clase=clase_data.get("numero", 1),
                objetivo=clase_data.get("objetivo", ""),
                dinamica=clase_data,
                estado="planificada",
            )
            db.add(clase)

    db.commit()
    db.refresh(planificacion)
    return planificacion


# ===========================================================================
# PLANIFICACIÓN DIARIA
# ===========================================================================

@router.post(
    "/diaria",
    response_model=PlanificacionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generar planificación diaria con Gemini",
)
def generar_planificacion_diaria(
    payload: PlanificacionDiariaRequest,
    docente: Docente = Depends(get_current_docente),
    db: Session = Depends(get_db),
):
    """
    Genera la planificación detallada de una clase individual.
    Incluye cronograma con minutos de cada momento de la clase.
    """
    asignacion = _get_asignacion_o_404(payload.asignacion_id, docente.id, db)
    version = _get_proxima_version(payload.asignacion_id, "diaria", db)

    try:
        contenido = gemini_service.generar_planificacion_diaria(
            asignacion=asignacion,
            titulo_clase=payload.titulo_clase,
            objetivo=payload.objetivo,
            contenido_principal=payload.contenido_principal,
            estrategia_sugerida=payload.estrategia_sugerida,
            duracion_minutos=payload.duracion_minutos,
            contexto_clases_anteriores=payload.contexto_clases_anteriores,
            db=db,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Error al comunicarse con Gemini: {str(e)}",
        )

    planificacion = Planificacion(
        asignacion_id=payload.asignacion_id,
        tipo="diaria",
        version=version,
        contenido=contenido,
        estado="borrador",
    )
    db.add(planificacion)
    db.commit()
    db.refresh(planificacion)
    return planificacion


# ===========================================================================
# GESTIÓN DE PLANIFICACIONES
# ===========================================================================

@router.get(
    "/{planificacion_id}",
    response_model=PlanificacionResponse,
    summary="Obtener planificación por ID",
)
def obtener_planificacion(
    planificacion_id: uuid.UUID,
    docente: Docente = Depends(get_current_docente),
    db: Session = Depends(get_db),
):
    return _get_planificacion_o_404(planificacion_id, docente.id, db)


@router.patch(
    "/{planificacion_id}/estado",
    response_model=PlanificacionResponse,
    summary="Cambiar estado de planificación",
)
def cambiar_estado(
    planificacion_id: uuid.UUID,
    estado: str,
    docente: Docente = Depends(get_current_docente),
    db: Session = Depends(get_db),
):
    """
    Cambia el estado de una planificación: borrador → vigente → archivada.
    Al marcar una como vigente, archiva las anteriores del mismo tipo.
    """
    estados_validos = {"borrador", "vigente", "archivada"}
    if estado not in estados_validos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Estado inválido. Válidos: {estados_validos}",
        )

    planificacion = _get_planificacion_o_404(planificacion_id, docente.id, db)

    # Si se marca como vigente, archivar las anteriores del mismo tipo
    if estado == "vigente":
        db.query(Planificacion).filter(
            Planificacion.asignacion_id == planificacion.asignacion_id,
            Planificacion.tipo == planificacion.tipo,
            Planificacion.estado == "vigente",
            Planificacion.id != planificacion_id,
        ).update({"estado": "archivada"})

    planificacion.estado = estado
    db.commit()
    db.refresh(planificacion)
    return planificacion


# ===========================================================================
# BORRADORES DE REPLANIFICACIÓN
# ===========================================================================

@router.post(
    "/{planificacion_id}/replanificar",
    summary="Generar borrador de replanificación",
)
def generar_replanificacion(
    planificacion_id: uuid.UUID,
    docente: Docente = Depends(get_current_docente),
    db: Session = Depends(get_db),
):
    """
    Analiza los desarrollos diarios recientes y genera un borrador de
    replanificación. El docente debe aprobarlo manualmente.
    NUNCA modifica la planificación vigente automáticamente.
    """
    planificacion = _get_planificacion_o_404(planificacion_id, docente.id, db)
    asignacion = planificacion.asignacion

    # Obtener desarrollos diarios recientes (últimos 10)
    from app.models.desarrollo_diario import DesarrolloDiario
    desarrollos = db.query(DesarrolloDiario).filter(
        DesarrolloDiario.asignacion_id == asignacion.id,
    ).order_by(DesarrolloDiario.fecha.desc()).limit(10).all()

    if not desarrollos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay desarrollos diarios registrados para analizar",
        )

    desarrollos_texto = [d.texto_estructurado for d in desarrollos]

    # Obtener unidades pendientes
    unidades = db.query(Unidad).filter(
        Unidad.planificacion_id == planificacion_id,
    ).all()

    unidades_data = [
        {
            "orden": u.orden,
            "titulo": u.titulo,
            "horas_restantes": u.clases_totales,
        }
        for u in unidades
    ]

    try:
        propuesta = gemini_service.generar_borrador_replanificacion(
            asignacion=asignacion,
            planificacion_actual=planificacion.contenido,
            desarrollos_recientes=desarrollos_texto,
            unidades_pendientes=unidades_data,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Error al comunicarse con Gemini: {str(e)}",
        )

    borrador = BorradorReplanificacion(
        planificacion_id=planificacion_id,
        contenido_propuesto=propuesta,
        estado="pendiente",
        motivo=propuesta.get("motivo", ""),
    )
    db.add(borrador)
    db.commit()
    db.refresh(borrador)

    return {
        "borrador_id": str(borrador.id),
        "estado": borrador.estado,
        "motivo": borrador.motivo,
        "propuesta": propuesta,
    }


@router.patch(
    "/borradores/{borrador_id}/accion",
    summary="Aprobar, rechazar o pedir cambios en borrador",
)
def accion_borrador(
    borrador_id: uuid.UUID,
    payload: BorradorAccionRequest,
    docente: Docente = Depends(get_current_docente),
    db: Session = Depends(get_db),
):
    """
    El docente decide qué hacer con el borrador de replanificación.
    - aprobar: aplica los cambios a la planificación vigente
    - rechazar: descarta el borrador
    - cambios: marca el borrador para revisión adicional
    """
    borrador = db.query(BorradorReplanificacion).filter(
        BorradorReplanificacion.id == borrador_id,
    ).first()

    if not borrador:
        raise HTTPException(status_code=404, detail="Borrador no encontrado")

    # Verificar que la planificación pertenece al docente
    _get_planificacion_o_404(borrador.planificacion_id, docente.id, db)

    mapa_estados = {
        "aprobar": "aprobado",
        "rechazar": "rechazado",
        "cambios": "cambios_solicitados",
    }

    borrador.estado = mapa_estados[payload.accion]
    borrador.comentario_docente = payload.comentario
    db.commit()

    return {
        "borrador_id": str(borrador.id),
        "nuevo_estado": borrador.estado,
        "mensaje": f"Borrador {borrador.estado} correctamente",
    }


# ===========================================================================
# Helpers internos
# ===========================================================================

def _get_asignacion_o_404(
    asignacion_id: uuid.UUID, docente_id: uuid.UUID, db: Session
) -> Asignacion:
    asignacion = (
        db.query(Asignacion)
        .filter(
            Asignacion.id == asignacion_id,
            Asignacion.docente_id == docente_id,
        )
        .first()
    )
    if not asignacion:
        raise HTTPException(status_code=404, detail="Asignación no encontrada")
    return asignacion


def _get_planificacion_o_404(
    planificacion_id: uuid.UUID, docente_id: uuid.UUID, db: Session
) -> Planificacion:
    planificacion = (
        db.query(Planificacion)
        .join(Asignacion)
        .filter(
            Planificacion.id == planificacion_id,
            Asignacion.docente_id == docente_id,
        )
        .first()
    )
    if not planificacion:
        raise HTTPException(status_code=404, detail="Planificación no encontrada")
    return planificacion


def _get_proxima_version(
    asignacion_id: uuid.UUID, tipo: str, db: Session
) -> int:
    """Retorna el número de versión siguiente para una planificación."""
    from sqlalchemy import func
    max_version = db.query(func.max(Planificacion.version)).filter(
        Planificacion.asignacion_id == asignacion_id,
        Planificacion.tipo == tipo,
    ).scalar()
    return (max_version or 0) + 1