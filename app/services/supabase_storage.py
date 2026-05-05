"""
Servicio para interactuar con Supabase Storage.
Maneja la subida, descarga y eliminación de archivos en los buckets.
También extrae el texto de PDFs y documentos Word para dárselo a Gemini.
"""
import uuid
import io
import re
from typing import Optional

from supabase import create_client, Client

from app.core.config import settings


# ---------------------------------------------------------------------------
# Cliente de Supabase (singleton)
# ---------------------------------------------------------------------------
def get_supabase_client() -> Client:
    """
    Retorna un cliente de Supabase con la service_key (permisos elevados).
    Usamos service_key en el backend para bypasear RLS desde el servidor.
    La anon_key se usa solo desde el frontend cuando implementemos acceso directo.
    """
    return create_client(settings.supabase_url, settings.supabase_service_key)


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------
def _limpiar_nombre_archivo(nombre: str) -> str:
    """
    Limpia el nombre del archivo para que sea válido en Supabase Storage.
    Reemplaza espacios, tildes y caracteres especiales.
    """
    reemplazos = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
        'ñ': 'ni', 'Ñ': 'NI', ' ': '_', '@': '', '-': '-',
    }
    nombre_limpio = nombre
    for char, reemplazo in reemplazos.items():
        nombre_limpio = nombre_limpio.replace(char, reemplazo)
    # Eliminar cualquier otro carácter que no sea alfanumérico, punto, guión o guión bajo
    nombre_limpio = re.sub(r'[^\w.\-]', '_', nombre_limpio)
    return nombre_limpio


def _get_content_type(nombre_archivo: str) -> str:
    """Determina el MIME type según la extensión del archivo."""
    nombre_lower = nombre_archivo.lower()
    tipos = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
        ".txt": "text/plain",
    }
    for ext, mime in tipos.items():
        if nombre_lower.endswith(ext):
            return mime
    return "application/octet-stream"


# ---------------------------------------------------------------------------
# Subida de archivos
# ---------------------------------------------------------------------------
def subir_archivo(
    contenido: bytes,
    nombre_archivo: str,
    docente_id: uuid.UUID,
    tipo: str,  # "anep_pdf" | "anep_word" | "anep_txt" | "ficha_docente"
    asignacion_id: Optional[uuid.UUID] = None,
) -> dict:
    """
    Sube un archivo a Supabase Storage y retorna los metadatos.

    Estructura de carpetas en el bucket:
        archivos-anep/{docente_id}/{asignacion_id}/{uuid}_{nombre}
        fichas-docente/{docente_id}/{asignacion_id}/{uuid}_{nombre}

    Args:
        contenido: Bytes del archivo
        nombre_archivo: Nombre original del archivo
        docente_id: UUID del docente propietario
        tipo: Tipo de archivo para determinar el bucket
        asignacion_id: UUID de la asignación relacionada (opcional)

    Returns:
        Dict con storage_path y storage_url
    """
    supabase = get_supabase_client()

    # Determinar bucket según tipo
    bucket = settings.bucket_fichas if tipo == "ficha_docente" else settings.bucket_anep

    # Limpiar nombre del archivo para evitar caracteres inválidos en Storage
    nombre_limpio = _limpiar_nombre_archivo(nombre_archivo)

    # Construir path único para evitar colisiones
    archivo_uuid = uuid.uuid4()
    if asignacion_id:
        storage_path = f"{docente_id}/{asignacion_id}/{archivo_uuid}_{nombre_limpio}"
    else:
        storage_path = f"{docente_id}/general/{archivo_uuid}_{nombre_limpio}"

    # Determinar content-type
    content_type = _get_content_type(nombre_archivo)

    # Subir a Supabase Storage
    supabase.storage.from_(bucket).upload(
        path=storage_path,
        file=contenido,
        file_options={"content-type": content_type, "upsert": "false"},
    )

    # Generar URL firmada (válida por 10 años = acceso permanente en la práctica)
    url_response = supabase.storage.from_(bucket).create_signed_url(
        path=storage_path,
        expires_in=60 * 60 * 24 * 365 * 10,  # 10 años en segundos
    )

    return {
        "storage_path": storage_path,
        "storage_url": url_response["signedURL"],
        "bucket": bucket,
    }


def eliminar_archivo(storage_path: str, tipo: str) -> bool:
    """
    Elimina un archivo de Supabase Storage.

    Returns:
        True si se eliminó correctamente, False si hubo error.
    """
    supabase = get_supabase_client()
    bucket = settings.bucket_fichas if tipo == "ficha_docente" else settings.bucket_anep

    try:
        supabase.storage.from_(bucket).remove([storage_path])
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Extracción de texto para contexto de Gemini
# ---------------------------------------------------------------------------
def extraer_texto_archivo(contenido: bytes, nombre_archivo: str) -> str:
    """
    Extrae el texto de un archivo para usarlo como contexto en Gemini.
    Soporta PDF, Word (.docx) y texto plano (.txt).

    Args:
        contenido: Bytes del archivo
        nombre_archivo: Nombre del archivo (para determinar el tipo)

    Returns:
        Texto extraído como string. Vacío si no se pudo extraer.
    """
    nombre_lower = nombre_archivo.lower()

    try:
        if nombre_lower.endswith(".pdf"):
            return _extraer_texto_pdf(contenido)
        elif nombre_lower.endswith(".docx"):
            return _extraer_texto_docx(contenido)
        elif nombre_lower.endswith(".txt"):
            return contenido.decode("utf-8", errors="ignore")
        else:
            return ""
    except Exception as e:
        print(f"Error extrayendo texto de {nombre_archivo}: {e}")
        return ""


def _extraer_texto_pdf(contenido: bytes) -> str:
    """Extrae texto de un PDF usando PyPDF2."""
    import PyPDF2

    reader = PyPDF2.PdfReader(io.BytesIO(contenido))
    partes = []
    for pagina in reader.pages:
        texto = pagina.extract_text()
        if texto:
            partes.append(texto)
    return "\n".join(partes)


def _extraer_texto_docx(contenido: bytes) -> str:
    """Extrae texto de un documento Word (.docx) usando python-docx."""
    from docx import Document

    doc = Document(io.BytesIO(contenido))
    parrafos = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(parrafos)