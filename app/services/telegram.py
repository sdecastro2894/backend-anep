"""
Servicio de Telegram.
Maneja la lógica de procesamiento de mensajes recibidos via Webhook.
Identifica al docente por chat_id, detecta la asignación mencionada,
estructura el texto con Gemini y guarda el desarrollo diario.
"""
import re
from datetime import date, datetime
from sqlalchemy.orm import Session

from app.models.docente import Docente
from app.models.asignacion import Asignacion
from app.models.grupo import Grupo
from app.models.desarrollo_diario import DesarrolloDiario
from app.services import gemini as gemini_service


def procesar_mensaje_telegram(
    chat_id: int,
    texto: str,
    db: Session,
) -> str:
    """
    Procesa un mensaje recibido del bot de Telegram.

    Flujo:
    1. Identifica al docente por chat_id
    2. Intenta identificar el grupo y materia mencionados en el mensaje
    3. Estructura el texto con Gemini
    4. Guarda el desarrollo diario en la DB
    5. Retorna una respuesta para enviarle al docente

    Args:
        chat_id: ID del chat de Telegram del docente
        texto: Texto del mensaje enviado
        db: Sesión de base de datos

    Returns:
        Texto de respuesta para enviar al docente via Telegram
    """
    # 1. Identificar docente por chat_id
    docente = db.query(Docente).filter(
        Docente.telegram_chat_id == chat_id,
        Docente.is_active == True,
    ).first()

    if not docente:
        return (
            "❌ Tu cuenta de Telegram no está vinculada a ningún docente en el sistema.\n\n"
            "Para vincularla, ingresá a la app web y en tu perfil pegá tu chat_id: "
            f"`{chat_id}`"
        )

    # 2. Identificar asignación mencionada en el mensaje
    asignacion = _identificar_asignacion(texto, docente, db)

    if not asignacion:
        # Si no se pudo identificar, pedir aclaración
        asignaciones = db.query(Asignacion).filter(
            Asignacion.docente_id == docente.id
        ).all()

        lista = "\n".join([
            f"  • {a.grupo.nombre} - {a.materia}"
            for a in asignaciones
        ])

        return (
            f"🤔 No pude identificar el grupo y materia en tu mensaje.\n\n"
            f"Tus asignaciones registradas son:\n{lista}\n\n"
            f"Intentá mencionar el grupo y materia más claramente. "
            f"Por ejemplo: 'Hoy en 8vo D de Matemáticas dimos...'"
        )

    # 3. Estructurar el texto con Gemini
    try:
        texto_estructurado = gemini_service.estructurar_desarrollo_diario(
            texto_original=texto,
            asignacion=asignacion,
        )
    except Exception as e:
        # Si Gemini falla, guardar el texto original sin estructurar
        texto_estructurado = texto
        print(f"Error estructurando con Gemini: {e}")

    # 4. Guardar desarrollo diario
    hoy = date.today()

    # Verificar si ya existe un registro para hoy en esta asignación
    existente = db.query(DesarrolloDiario).filter(
        DesarrolloDiario.asignacion_id == asignacion.id,
        DesarrolloDiario.fecha == hoy,
    ).first()

    if existente:
        # Actualizar el existente (puede haber enviado dos mensajes del mismo día)
        existente.texto_original = texto
        existente.texto_estructurado = texto_estructurado
        existente.revisado = False
        existente.updated_at = datetime.utcnow()
        db.commit()
        accion = "actualizado"
    else:
        # Crear nuevo registro
        desarrollo = DesarrolloDiario(
            asignacion_id=asignacion.id,
            fecha=hoy,
            texto_original=texto,
            texto_estructurado=texto_estructurado,
            origen="telegram",
            revisado=False,
        )
        db.add(desarrollo)
        db.commit()
        accion = "registrado"

    # 5. Retornar respuesta al docente
    return (
        f"✅ Desarrollo diario {accion} correctamente.\n\n"
        f"📚 *{asignacion.grupo.nombre} - {asignacion.materia}*\n"
        f"📅 {hoy.strftime('%d/%m/%Y')}\n\n"
        f"📝 *Texto estructurado:*\n{texto_estructurado}\n\n"
        f"_Si querés editar este registro, ingresá a la app web._"
    )


def _identificar_asignacion(
    texto: str,
    docente: Docente,
    db: Session,
) -> Asignacion | None:
    """
    Intenta identificar qué asignación (grupo + materia) menciona el docente
    en su mensaje de Telegram.

    Estrategia:
    1. Busca coincidencias de nombre de grupo y materia en el texto
    2. Usa comparación flexible (sin tildes, case-insensitive)
    3. Retorna la asignación con más coincidencias

    Args:
        texto: Texto del mensaje
        docente: Docente autenticado
        db: Sesión de base de datos

    Returns:
        La asignación identificada o None si no se pudo determinar
    """
    texto_normalizado = _normalizar_texto(texto)

    asignaciones = db.query(Asignacion).filter(
        Asignacion.docente_id == docente.id
    ).all()

    if not asignaciones:
        return None

    # Si solo tiene una asignación, retornarla directamente
    if len(asignaciones) == 1:
        return asignaciones[0]

    # Puntuar cada asignación según cuántos términos coinciden en el texto
    puntuaciones = []

    for asignacion in asignaciones:
        puntos = 0

        # Buscar nombre del grupo
        nombre_grupo = _normalizar_texto(asignacion.grupo.nombre)
        if nombre_grupo in texto_normalizado:
            puntos += 3  # Mayor peso al nombre del grupo

        # Buscar palabras del nombre del grupo por separado
        for palabra in nombre_grupo.split():
            if len(palabra) > 2 and palabra in texto_normalizado:
                puntos += 1

        # Buscar materia
        materia = _normalizar_texto(asignacion.materia)
        if materia in texto_normalizado:
            puntos += 3

        # Buscar palabras de la materia
        for palabra in materia.split():
            if len(palabra) > 3 and palabra in texto_normalizado:
                puntos += 1

        puntuaciones.append((asignacion, puntos))

    # Ordenar por puntuación descendente
    puntuaciones.sort(key=lambda x: x[1], reverse=True)

    # Retornar la de mayor puntuación si tiene al menos 2 puntos
    if puntuaciones[0][1] >= 2:
        return puntuaciones[0][0]

    return None


def _normalizar_texto(texto: str) -> str:
    """
    Normaliza texto para comparación flexible:
    - Convierte a minúsculas
    - Elimina tildes
    - Elimina caracteres especiales
    """
    texto = texto.lower()
    reemplazos = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'ü': 'u', 'ñ': 'n',
    }
    for char, reemplazo in reemplazos.items():
        texto = texto.replace(char, reemplazo)
    return texto