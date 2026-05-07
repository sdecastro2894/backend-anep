"""
Router de Desarrollo Diario.
Endpoints para listar y editar los registros de desarrollo diario.
"""
import uuid
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.models.docente import Docente
from app.models.asignacion import Asignacion
from app.models.desarrollo_diario import DesarrolloDiario
from app.routers.auth import get_current_docente

router = APIRouter()


class DesarrolloUpdate(BaseModel):
    texto_estructurado: str
    revisado: bool = True


class DesarrolloResponse(BaseModel):
    id: uuid.UUID
    asignacion_id: uuid.UUID
    fecha: date
    texto_original: str
    texto_estructurado: str
    origen: str
    revisado: bool

    model_config = {"from_attributes": True}


@router.get(
    "/lista",
    response_model=list[DesarrolloResponse],
    summary="Listar desarrollos diarios de una asignación",
)
def listar_desarrollos(
    asignacion_id: uuid.UUID,
    limite: int = 30,
    docente: Docente = Depends(get_current_docente),
    db: Session = Depends(get_db),
):
    """
    Retorna los últimos N desarrollos diarios de una asignación,
    ordenados del más reciente al más antiguo.
    """
    # Verificar que la asignación pertenece al docente
    asignacion = db.query(Asignacion).filter(
        Asignacion.id == asignacion_id,
        Asignacion.docente_id == docente.id,
    ).first()

    if not asignacion:
        raise HTTPException(status_code=404, detail="Asignación no encontrada")

    desarrollos = (
        db.query(DesarrolloDiario)
        .filter(DesarrolloDiario.asignacion_id == asignacion_id)
        .order_by(DesarrolloDiario.fecha.desc())
        .limit(limite)
        .all()
    )

    return desarrollos


@router.patch(
    "/{desarrollo_id}",
    response_model=DesarrolloResponse,
    summary="Editar desarrollo diario",
)
def editar_desarrollo(
    desarrollo_id: uuid.UUID,
    payload: DesarrolloUpdate,
    docente: Docente = Depends(get_current_docente),
    db: Session = Depends(get_db),
):
    """
    Permite al docente editar manualmente el texto estructurado
    de un desarrollo diario. Marca el registro como revisado.
    """
    # Buscar el desarrollo verificando que pertenece al docente
    desarrollo = (
        db.query(DesarrolloDiario)
        .join(Asignacion)
        .filter(
            DesarrolloDiario.id == desarrollo_id,
            Asignacion.docente_id == docente.id,
        )
        .first()
    )

    if not desarrollo:
        raise HTTPException(status_code=404, detail="Desarrollo no encontrado")

    desarrollo.texto_estructurado = payload.texto_estructurado
    desarrollo.revisado = payload.revisado
    db.commit()
    db.refresh(desarrollo)

    return desarrollo