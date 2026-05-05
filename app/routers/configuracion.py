"""
Router de configuración inicial.
Endpoints para gestionar grupos, asignaciones y archivos base.
"""
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.docente import Docente
from app.models.grupo import Grupo
from app.models.asignacion import Asignacion
from app.models.archivo import ArchivoBase
from app.routers.auth import get_current_docente
from app.schemas.configuracion import (
    GrupoCreate, GrupoUpdate, GrupoResponse,
    AsignacionCreate, AsignacionUpdate, AsignacionResponse,
    ArchivoBaseResponse,
)
from app.services.supabase_storage import subir_archivo, eliminar_archivo

router = APIRouter()

# Tamaño máximo de archivo: 10 MB
MAX_FILE_SIZE = 10 * 1024 * 1024

# Tipos de archivo permitidos
TIPOS_PERMITIDOS = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "text/plain",
}


# ===========================================================================
# GRUPOS
# ===========================================================================

@router.post(
    "/grupos",
    response_model=GrupoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo grupo",
)
def crear_grupo(
    payload: GrupoCreate,
    docente: Docente = Depends(get_current_docente),
    db: Session = Depends(get_db),
):
    """
    Crea un nuevo grupo para el docente autenticado.
    Ej: { "nombre": "8vo D", "anio": "2025", "institucion": "Liceo 5" }
    """
    grupo = Grupo(
        docente_id=docente.id,
        nombre=payload.nombre,
        anio=payload.anio,
        institucion=payload.institucion,
    )
    db.add(grupo)
    db.commit()
    db.refresh(grupo)
    return grupo


@router.get(
    "/grupos",
    response_model=list[GrupoResponse],
    summary="Listar grupos del docente",
)
def listar_grupos(
    docente: Docente = Depends(get_current_docente),
    db: Session = Depends(get_db),
):
    """Retorna todos los grupos del docente autenticado."""
    return db.query(Grupo).filter(Grupo.docente_id == docente.id).all()


@router.get(
    "/grupos/{grupo_id}",
    response_model=GrupoResponse,
    summary="Obtener grupo por ID",
)
def obtener_grupo(
    grupo_id: uuid.UUID,
    docente: Docente = Depends(get_current_docente),
    db: Session = Depends(get_db),
):
    grupo = _get_grupo_o_404(grupo_id, docente.id, db)
    return grupo


@router.patch(
    "/grupos/{grupo_id}",
    response_model=GrupoResponse,
    summary="Actualizar grupo",
)
def actualizar_grupo(
    grupo_id: uuid.UUID,
    payload: GrupoUpdate,
    docente: Docente = Depends(get_current_docente),
    db: Session = Depends(get_db),
):
    grupo = _get_grupo_o_404(grupo_id, docente.id, db)

    # Actualizar solo los campos enviados (PATCH parcial)
    datos = payload.model_dump(exclude_unset=True)
    for campo, valor in datos.items():
        setattr(grupo, campo, valor)

    db.commit()
    db.refresh(grupo)
    return grupo


@router.delete(
    "/grupos/{grupo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar grupo",
)
def eliminar_grupo(
    grupo_id: uuid.UUID,
    docente: Docente = Depends(get_current_docente),
    db: Session = Depends(get_db),
):
    """
    Elimina un grupo y todas sus asignaciones asociadas (CASCADE).
    """
    grupo = _get_grupo_o_404(grupo_id, docente.id, db)
    db.delete(grupo)
    db.commit()


# ===========================================================================
# ASIGNACIONES
# ===========================================================================

@router.post(
    "/asignaciones",
    response_model=AsignacionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nueva asignación",
)
def crear_asignacion(
    payload: AsignacionCreate,
    docente: Docente = Depends(get_current_docente),
    db: Session = Depends(get_db),
):
    """
    Crea una asignación: vincula un docente con un grupo, materia y horario.
    Verifica que el grupo pertenece al docente antes de crear.
    """
    # Verificar que el grupo existe y pertenece al docente
    grupo = _get_grupo_o_404(payload.grupo_id, docente.id, db)

    # Verificar que no existe ya esa combinación docente+grupo+materia
    existente = db.query(Asignacion).filter(
        Asignacion.docente_id == docente.id,
        Asignacion.grupo_id == payload.grupo_id,
        Asignacion.materia == payload.materia,
    ).first()

    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe una asignación de '{payload.materia}' para ese grupo",
        )

    asignacion = Asignacion(
        docente_id=docente.id,
        grupo_id=payload.grupo_id,
        materia=payload.materia,
        horario=payload.horario,
        minutos_por_hora_docente=payload.minutos_por_hora_docente,
    )
    db.add(asignacion)
    db.commit()
    db.refresh(asignacion)

    return AsignacionResponse.from_orm_with_grupo(asignacion)


@router.get(
    "/asignaciones",
    response_model=list[AsignacionResponse],
    summary="Listar asignaciones del docente",
)
def listar_asignaciones(
    docente: Docente = Depends(get_current_docente),
    db: Session = Depends(get_db),
):
    """
    Retorna todas las asignaciones del docente con info del grupo incluida.
    """
    asignaciones = (
        db.query(Asignacion)
        .filter(Asignacion.docente_id == docente.id)
        .all()
    )
    return [AsignacionResponse.from_orm_with_grupo(a) for a in asignaciones]


@router.get(
    "/asignaciones/{asignacion_id}",
    response_model=AsignacionResponse,
    summary="Obtener asignación por ID",
)
def obtener_asignacion(
    asignacion_id: uuid.UUID,
    docente: Docente = Depends(get_current_docente),
    db: Session = Depends(get_db),
):
    asignacion = _get_asignacion_o_404(asignacion_id, docente.id, db)
    return AsignacionResponse.from_orm_with_grupo(asignacion)


@router.patch(
    "/asignaciones/{asignacion_id}",
    response_model=AsignacionResponse,
    summary="Actualizar asignación",
)
def actualizar_asignacion(
    asignacion_id: uuid.UUID,
    payload: AsignacionUpdate,
    docente: Docente = Depends(get_current_docente),
    db: Session = Depends(get_db),
):
    asignacion = _get_asignacion_o_404(asignacion_id, docente.id, db)

    datos = payload.model_dump(exclude_unset=True)
    for campo, valor in datos.items():
        setattr(asignacion, campo, valor)

    db.commit()
    db.refresh(asignacion)
    return AsignacionResponse.from_orm_with_grupo(asignacion)


@router.delete(
    "/asignaciones/{asignacion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar asignación",
)
def eliminar_asignacion(
    asignacion_id: uuid.UUID,
    docente: Docente = Depends(get_current_docente),
    db: Session = Depends(get_db),
):
    asignacion = _get_asignacion_o_404(asignacion_id, docente.id, db)
    db.delete(asignacion)
    db.commit()


# ===========================================================================
# ARCHIVOS BASE
# ===========================================================================

@router.post(
    "/archivos",
    response_model=ArchivoBaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Subir archivo base (PDF, Word, TXT)",
)
async def subir_archivo_base(
    archivo: UploadFile = File(...),
    tipo: str = Form(...),  # "anep_pdf" | "anep_word" | "anep_txt" | "ficha_docente"
    asignacion_id: str | None = Form(None),
    docente: Docente = Depends(get_current_docente),
    db: Session = Depends(get_db),
):
    """
    Sube un archivo a Supabase Storage y registra los metadatos en la DB.

    - tipo: "anep_pdf", "anep_word", "anep_txt" o "ficha_docente"
    - asignacion_id: UUID de la asignación relacionada (opcional)
    - El archivo debe ser PDF, Word o texto plano, máximo 10MB
    """
    # Validar tipo
    tipos_validos = {"anep_pdf", "anep_word", "anep_txt", "ficha_docente"}
    if tipo not in tipos_validos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo inválido. Válidos: {tipos_validos}",
        )

    # Validar content-type del archivo
    if archivo.content_type not in TIPOS_PERMITIDOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de archivo no permitido: {archivo.content_type}",
        )

    # Leer contenido y validar tamaño
    contenido = await archivo.read()
    if len(contenido) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="El archivo supera el límite de 10MB",
        )

    # Parsear asignacion_id si viene
    asignacion_uuid = None
    if asignacion_id:
        try:
            asignacion_uuid = uuid.UUID(asignacion_id)
            # Verificar que la asignación pertenece al docente
            _get_asignacion_o_404(asignacion_uuid, docente.id, db)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="asignacion_id inválido",
            )

    # Subir a Supabase Storage
    try:
        resultado = subir_archivo(
            contenido=contenido,
            nombre_archivo=archivo.filename,
            docente_id=docente.id,
            tipo=tipo,
            asignacion_id=asignacion_uuid,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al subir archivo a Storage: {str(e)}",
        )

    # Registrar metadatos en la DB
    archivo_db = ArchivoBase(
        docente_id=docente.id,
        asignacion_id=asignacion_uuid,
        nombre=archivo.filename,
        tipo=tipo,
        storage_path=resultado["storage_path"],
        storage_url=resultado["storage_url"],
        mime_type=archivo.content_type,
        tamanio_bytes=len(contenido),
    )
    db.add(archivo_db)
    db.commit()
    db.refresh(archivo_db)

    return archivo_db


@router.get(
    "/archivos",
    response_model=list[ArchivoBaseResponse],
    summary="Listar archivos del docente",
)
def listar_archivos(
    asignacion_id: uuid.UUID | None = None,
    docente: Docente = Depends(get_current_docente),
    db: Session = Depends(get_db),
):
    """
    Lista los archivos del docente.
    Si se pasa asignacion_id, filtra por esa asignación.
    """
    query = db.query(ArchivoBase).filter(ArchivoBase.docente_id == docente.id)
    if asignacion_id:
        query = query.filter(ArchivoBase.asignacion_id == asignacion_id)
    return query.all()


@router.delete(
    "/archivos/{archivo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar archivo",
)
def eliminar_archivo_base(
    archivo_id: uuid.UUID,
    docente: Docente = Depends(get_current_docente),
    db: Session = Depends(get_db),
):
    """
    Elimina el archivo de Supabase Storage y su registro en la DB.
    """
    archivo = db.query(ArchivoBase).filter(
        ArchivoBase.id == archivo_id,
        ArchivoBase.docente_id == docente.id,
    ).first()

    if not archivo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archivo no encontrado",
        )

    # Eliminar de Storage primero
    eliminar_archivo(archivo.storage_path, archivo.tipo)

    # Eliminar de la DB
    db.delete(archivo)
    db.commit()


# ===========================================================================
# Helpers internos
# ===========================================================================

def _get_grupo_o_404(grupo_id: uuid.UUID, docente_id: uuid.UUID, db: Session) -> Grupo:
    """Busca un grupo por ID verificando que pertenece al docente. Lanza 404 si no existe."""
    grupo = db.query(Grupo).filter(
        Grupo.id == grupo_id,
        Grupo.docente_id == docente_id,
    ).first()
    if not grupo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grupo no encontrado",
        )
    return grupo


def _get_asignacion_o_404(
    asignacion_id: uuid.UUID, docente_id: uuid.UUID, db: Session
) -> Asignacion:
    """Busca una asignación verificando que pertenece al docente. Lanza 404 si no existe."""
    asignacion = db.query(Asignacion).filter(
        Asignacion.id == asignacion_id,
        Asignacion.docente_id == docente_id,
    ).joinedload(Asignacion.grupo).first() if False else (
        db.query(Asignacion)
        .filter(
            Asignacion.id == asignacion_id,
            Asignacion.docente_id == docente_id,
        )
        .first()
    )
    if not asignacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asignación no encontrada",
        )
    return asignacion