"""
Router de autenticación.
Endpoints: registro, login, perfil, vincular Telegram.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from app.models.docente import Docente
from app.schemas.auth import (
    DocenteCreate,
    LoginRequest,
    TokenResponse,
    DocenteResponse,
    TelegramLinkRequest,
)

router = APIRouter()
security = HTTPBearer()


# ---------------------------------------------------------------------------
# Dependency: obtener el docente autenticado desde el JWT
# ---------------------------------------------------------------------------
def get_current_docente(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Docente:
    """
    Dependency de FastAPI que extrae y valida el JWT del header Authorization.
    Uso en endpoints protegidos:
        @router.get("/ruta")
        def endpoint(docente: Docente = Depends(get_current_docente)):
    """
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    docente_id_str = payload.get("sub")
    if docente_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token malformado",
        )

    try:
        docente_id = uuid.UUID(docente_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token malformado",
        )

    docente = db.query(Docente).filter(Docente.id == docente_id).first()

    if docente is None or not docente.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Docente no encontrado o inactivo",
        )

    return docente


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post(
    "/registro",
    response_model=DocenteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo docente",
)
def registro(payload: DocenteCreate, db: Session = Depends(get_db)):
    """
    Registra un nuevo docente en el sistema.
    Verifica que el email no esté en uso antes de crear el registro.
    """
    # Verificar email duplicado
    existente = db.query(Docente).filter(Docente.email == payload.email).first()
    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una cuenta con ese email",
        )

    docente = Docente(
        nombre=payload.nombre,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(docente)
    db.commit()
    db.refresh(docente)

    return docente


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Iniciar sesión",
)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Autentica al docente y retorna un JWT.
    El token debe enviarse en el header Authorization: Bearer <token>
    en todos los endpoints protegidos.
    """
    docente = db.query(Docente).filter(Docente.email == payload.email).first()

    if docente is None or not verify_password(payload.password, docente.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )

    if not docente.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta desactivada",
        )

    token = create_access_token(subject=str(docente.id))

    return TokenResponse(
        access_token=token,
        docente_id=docente.id,
        nombre=docente.nombre,
        email=docente.email,
    )


@router.get(
    "/me",
    response_model=DocenteResponse,
    summary="Obtener perfil del docente autenticado",
)
def get_me(docente: Docente = Depends(get_current_docente)):
    """Retorna los datos del docente autenticado."""
    return docente


@router.patch(
    "/vincular-telegram",
    response_model=DocenteResponse,
    summary="Vincular cuenta de Telegram",
)
def vincular_telegram(
    payload: TelegramLinkRequest,
    docente: Docente = Depends(get_current_docente),
    db: Session = Depends(get_db),
):
    """
    Vincula el chat_id de Telegram al docente autenticado.
    El docente debe enviar /start al bot y copiar el chat_id que recibe.
    """
    # Verificar que el chat_id no esté vinculado a otro docente
    existente = db.query(Docente).filter(
        Docente.telegram_chat_id == payload.telegram_chat_id
    ).first()

    if existente and existente.id != docente.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ese chat_id ya está vinculado a otra cuenta",
        )

    docente.telegram_chat_id = payload.telegram_chat_id
    db.commit()
    db.refresh(docente)

    return docente