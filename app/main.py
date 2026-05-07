"""
Punto de entrada principal de la aplicación FastAPI.
Configura middlewares, routers y sirve el frontend estático.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.database import check_db_connection
from app.routers import auth, configuracion, planificaciones, telegram, desarrollo
# ---------------------------------------------------------------------------
# Lifespan: código que corre al iniciar y apagar la app
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Se ejecuta una vez al arrancar la app.
    Verifica conexión a DB antes de aceptar requests.
    """
    print("🚀 Iniciando Docente App...")
    if check_db_connection():
        print("✅ Conexión a Supabase PostgreSQL: OK")
    else:
        print("❌ ERROR: No se pudo conectar a la base de datos")

    yield  # La app corre aquí

    print("👋 Apagando Docente App...")


# ---------------------------------------------------------------------------
# Instancia principal de FastAPI
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Docente App",
    description="Sistema de gestión y planificación para docentes de educación secundaria y UTU - Uruguay",
    version="0.1.0",
    lifespan=lifespan,
    # En producción ocultamos la documentación automática
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url="/redoc" if settings.environment == "development" else None,
)


# ---------------------------------------------------------------------------
# Middlewares
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        ["*"] if settings.environment == "development"
        else [settings.render_url]
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routers de la API
# ---------------------------------------------------------------------------
app.include_router(auth.router, prefix="/api/auth", tags=["Autenticación"])

app.include_router(configuracion.router, prefix="/api/config", tags=["Configuración"])

app.include_router(planificaciones.router, prefix="/api/planificaciones", tags=["Planificaciones"])

app.include_router(telegram.router, prefix="/api/telegram", tags=["Telegram"])

app.include_router(desarrollo.router, prefix="/api/desarrollo", tags=["Desarrollo Diario"])

# ---------------------------------------------------------------------------
# Health check (útil para Render y para el webhook de Telegram)
# ---------------------------------------------------------------------------
@app.get("/api/health", tags=["Sistema"])
def health_check():
    """
    Endpoint de salud. Render lo usa para verificar que la app está viva.
    También sirve para despertar la app en el tier gratuito.
    """
    db_ok = check_db_connection()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "error",
        "environment": settings.environment,
        "version": "0.1.0",
    }


# ---------------------------------------------------------------------------
# Servir el frontend estático
# El backend sirve los archivos HTML/CSS/JS directamente.
# Esto evita tener que configurar un servidor web separado en Render.
# ---------------------------------------------------------------------------
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(full_path: str):
    """
    Catch-all: cualquier ruta que no sea /api/* retorna el index.html.
    Permite que el frontend maneje su propia navegación por tabs.
    """
    return FileResponse("static/index.html")