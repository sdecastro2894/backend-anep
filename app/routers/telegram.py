"""
Router del Webhook de Telegram.
Recibe los updates de Telegram, los procesa y responde.

IMPORTANTE: Este endpoint debe ser público (sin autenticación JWT)
porque Telegram lo llama directamente.
La seguridad se maneja verificando el token en la URL.
"""
import httpx
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.services.telegram import procesar_mensaje_telegram

router = APIRouter()


async def _enviar_respuesta_telegram(chat_id: int, texto: str) -> None:
    """
    Envía un mensaje de respuesta al docente via Telegram Bot API.

    Args:
        chat_id: ID del chat de Telegram
        texto: Texto a enviar (soporta Markdown)
    """
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": texto,
        "parse_mode": "Markdown",
    }
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload, timeout=10.0)
    except Exception as e:
        print(f"Error enviando mensaje a Telegram: {e}")


@router.post(
    "/webhook/{token}",
    include_in_schema=False,  # No mostrar en Swagger (es un endpoint interno)
)
async def telegram_webhook(
    token: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Endpoint que recibe los updates de Telegram.

    Telegram llama a este endpoint cada vez que el bot recibe un mensaje.
    La URL tiene el token como parámetro para verificar que el llamado
    es legítimo (seguridad básica por oscuridad).

    Flujo:
    1. Verificar token en la URL
    2. Parsear el update de Telegram
    3. Extraer chat_id y texto del mensaje
    4. Procesar con el servicio de Telegram
    5. Enviar respuesta al docente
    """
    # Verificar token en la URL para seguridad básica
    if token != settings.telegram_bot_token:
        raise HTTPException(status_code=403, detail="Token inválido")

    # Parsear el body del update de Telegram
    try:
        update = await request.json()
    except Exception:
        # Retornar 200 siempre para que Telegram no reintente
        return {"ok": True}

    # Extraer mensaje del update
    message = update.get("message") or update.get("edited_message")
    if not message:
        # Puede ser otro tipo de update (inline query, etc.), ignorar
        return {"ok": True}

    chat_id = message.get("chat", {}).get("id")
    texto = message.get("text", "")

    if not chat_id or not texto:
        return {"ok": True}

    # Ignorar comandos del sistema excepto /start
    if texto.startswith("/") and texto != "/start":
        return {"ok": True}

    # Manejar el comando /start
    if texto == "/start":
        await _enviar_respuesta_telegram(
            chat_id=chat_id,
            texto=(
                "👋 ¡Hola! Soy tu asistente docente.\n\n"
                "Para vincular tu cuenta, ingresá a la app web y "
                f"pegá tu *chat_id*: `{chat_id}`\n\n"
                "Una vez vinculado, podés enviarme mensajes como:\n"
                "_'Hoy en 8vo D de Matemáticas dimos ecuaciones de primer grado...'_"
            ),
        )
        return {"ok": True}

    # Procesar mensaje normal
    respuesta = procesar_mensaje_telegram(
        chat_id=chat_id,
        texto=texto,
        db=db,
    )

    # Enviar respuesta al docente
    await _enviar_respuesta_telegram(chat_id=chat_id, texto=respuesta)

    # Siempre retornar 200 a Telegram
    return {"ok": True}


@router.post(
    "/configurar-webhook",
    summary="Configurar URL del Webhook en Telegram",
    tags=["Telegram"],
)
async def configurar_webhook():
    """
    Registra la URL del webhook en Telegram.
    Llamar a este endpoint UNA VEZ después de desplegar en Render.
    Requiere que RENDER_URL esté configurado en el .env
    """
    if not settings.render_url:
        raise HTTPException(
            status_code=400,
            detail="RENDER_URL no está configurado en el .env",
        )

    webhook_url = (
        f"{settings.render_url}/api/telegram/webhook/{settings.telegram_bot_token}"
    )

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/setWebhook"

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json={"url": webhook_url})
        resultado = response.json()

    return {
        "webhook_url": webhook_url,
        "telegram_response": resultado,
    }


@router.get(
    "/info-webhook",
    summary="Ver estado actual del Webhook",
    tags=["Telegram"],
)
async def info_webhook():
    """Consulta el estado actual del webhook configurado en Telegram."""
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/getWebhookInfo"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()