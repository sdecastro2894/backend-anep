"""
Servicio de integración con Google Gemini.
Implementa la cadena de prompts para generación de planificaciones docentes.
"""
import google.generativeai as genai
from app.core.config import settings
from app.services.supabase_storage import extraer_texto_archivo
from app.models.asignacion import Asignacion
from app.models.archivo import ArchivoBase
from sqlalchemy.orm import Session

# Configurar cliente Gemini
genai.configure(api_key=settings.gemini_api_key)

# Usamos Flash por velocidad y costo en tier gratuito
MODEL_NAME = "gemini-2.5-flash"


def _get_model():
    """Retorna la instancia del modelo Gemini."""
    return genai.GenerativeModel(
        model_name=MODEL_NAME,
        generation_config={
            "temperature": 0.7,      # Creatividad moderada
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
        },
    )


def _construir_contexto_asignacion(asignacion: Asignacion) -> str:
    """
    Construye un bloque de texto con el contexto de la asignación
    para incluir en todos los prompts.
    """
    dias = ", ".join([b["dia"] for b in asignacion.horario])
    bloques_por_dia = ", ".join([f"{b['dia']}: {b['bloques']} bloque(s)" for b in asignacion.horario])

    return f"""
CONTEXTO DE LA ASIGNACIÓN:
- Materia: {asignacion.materia}
- Grupo: {asignacion.grupo.nombre} ({asignacion.grupo.anio})
- Institución: {asignacion.grupo.institucion}
- Días de clase: {dias}
- Detalle de bloques: {bloques_por_dia}
- Duración de cada hora docente: {asignacion.minutos_por_hora_docente} minutos
- Total de horas docentes semanales: {asignacion.total_horas_docentes_semanales}
- Total de minutos semanales: {asignacion.total_minutos_semanales} minutos
"""


def _obtener_contexto_archivos(
    asignacion_id,
    docente_id,
    db: Session,
    max_chars: int = 15000,
) -> str:
    """
    Busca archivos en este orden:
    1. Archivos específicos de la asignación
    2. Archivos globales del docente (asignacion_id = None)
    """
    archivos = db.query(ArchivoBase).filter(
        ArchivoBase.docente_id == docente_id,
        # Trae archivos de esta asignación O archivos globales (sin asignación)
        (ArchivoBase.asignacion_id == asignacion_id) | 
        (ArchivoBase.asignacion_id == None),
    ).all()

    if not archivos:
        return ""

    textos = []
    total_chars = 0

    for archivo in archivos:
        if total_chars >= max_chars:
            break
        textos.append(f"[Archivo: {archivo.nombre} - Tipo: {archivo.tipo}]")
        total_chars += len(textos[-1])

    return "\n".join(textos) if textos else ""


# ===========================================================================
# PLANIFICACIÓN ANUAL
# ===========================================================================

def generar_planificacion_anual(
    asignacion: Asignacion,
    directivas: str,
    semanas_lectivas: int,
    porcentaje_emergentes: int,
    db: Session,
) -> dict:
    """
    Genera una planificación anual completa usando Gemini.

    Args:
        asignacion: La asignación docente con horario y grupo
        directivas: Texto libre con indicaciones del docente
        semanas_lectivas: Cantidad de semanas del año lectivo (ej: 38)
        porcentaje_emergentes: % de clases reservadas para emergentes (default 15)
        db: Sesión de base de datos para obtener archivos de contexto

    Returns:
        Dict con la planificación estructurada
    """
    model = _get_model()
    contexto = _construir_contexto_asignacion(asignacion)
    contexto_archivos = _obtener_contexto_archivos(asignacion.id, asignacion.docente_id, db)

    # Calcular clases totales y disponibles
    clases_totales_anuales = int(asignacion.total_horas_docentes_semanales * semanas_lectivas)
    clases_emergentes = int(clases_totales_anuales * porcentaje_emergentes / 100)
    clases_disponibles = clases_totales_anuales - clases_emergentes

    prompt = f"""
Eres un experto en planificación educativa para educación secundaria y UTU en Uruguay.
Tu tarea es generar una planificación anual detallada y realista.

{contexto}

PARÁMETROS DEL AÑO LECTIVO:
- Semanas lectivas: {semanas_lectivas}
- Total de horas docentes anuales: {clases_totales_anuales}
- Horas reservadas para emergentes ({porcentaje_emergentes}%): {clases_emergentes}
- Horas disponibles para contenido: {clases_disponibles}

DIRECTIVAS DEL DOCENTE:
{directivas if directivas else "Sin directivas adicionales."}

{f"ARCHIVOS DE REFERENCIA DEL DOCENTE:{contexto_archivos}" if contexto_archivos else ""}

INSTRUCCIONES:
1. Generá entre 3 y 6 unidades temáticas coherentes con la materia y el nivel.
2. Distribuí las {clases_disponibles} horas disponibles entre las unidades de forma equilibrada.
3. Para cada unidad indicá: título, descripción breve, cantidad de horas docentes asignadas,
   objetivos específicos (máximo 3), y contenidos principales.
4. Generá objetivos generales del año (máximo 4).
5. Tené en cuenta el contexto uruguayo: programas de ANEP, realidad socioeducativa.
6. Usá lenguaje claro y profesional, apropiado para un documento docente formal.

FORMATO DE RESPUESTA (JSON estricto, sin texto adicional):
{{
  "objetivos_generales": ["objetivo 1", "objetivo 2", "objetivo 3"],
  "total_horas_anuales": {clases_totales_anuales},
  "horas_emergentes": {clases_emergentes},
  "horas_contenido": {clases_disponibles},
  "semanas_lectivas": {semanas_lectivas},
  "unidades": [
    {{
      "orden": 1,
      "titulo": "Título de la unidad",
      "descripcion": "Descripción breve",
      "horas_docentes": 10,
      "objetivos_especificos": ["obj 1", "obj 2"],
      "contenidos": ["contenido 1", "contenido 2", "contenido 3"]
    }}
  ]
}}
"""

    response = model.generate_content(prompt)
    return _parsear_respuesta_json(response.text)


# ===========================================================================
# PLANIFICACIÓN POR UNIDAD
# ===========================================================================

def generar_planificacion_unidad(
    asignacion: Asignacion,
    titulo_unidad: str,
    horas_docentes: int,
    porcentaje_emergentes: int,
    incluir_evaluacion: bool,
    tipo_evaluacion: str | None,
    contenidos: list[str],
    objetivos: list[str],
    db: Session,
) -> dict:
    """
    Genera la planificación detallada de una unidad temática.
    Implementa la regla del 15% de clases para emergentes.
    """
    model = _get_model()
    contexto = _construir_contexto_asignacion(asignacion)
    contexto_archivos = _obtener_contexto_archivos(asignacion.id, asignacion.docente_id, db)

    # Calcular clases disponibles con regla del porcentaje
    clases_emergentes = max(1, int(horas_docentes * porcentaje_emergentes / 100))
    clases_contenido = horas_docentes - clases_emergentes
    # Si hay evaluación, reservar 1 clase para eso
    clases_evaluacion = 1 if incluir_evaluacion else 0
    clases_desarrollo = clases_contenido - clases_evaluacion

    evaluacion_texto = ""
    if incluir_evaluacion and tipo_evaluacion:
        evaluacion_texto = f"""
- La unidad incluye una evaluación {tipo_evaluacion}.
- Reservar 1 clase para la evaluación (clase #{clases_contenido}).
- Describir brevemente el formato de evaluación sugerido.
"""

    prompt = f"""
Eres un experto en planificación educativa para educación secundaria y UTU en Uruguay.
Tu tarea es generar la planificación detallada de una unidad temática.

{contexto}

DATOS DE LA UNIDAD:
- Título: {titulo_unidad}
- Total de horas docentes asignadas: {horas_docentes}
- Horas para emergentes ({porcentaje_emergentes}%): {clases_emergentes}
- Horas para desarrollo de contenido: {clases_desarrollo}
- Objetivos de la unidad: {", ".join(objetivos)}
- Contenidos a desarrollar: {", ".join(contenidos)}

{evaluacion_texto}

{f"ARCHIVOS DE REFERENCIA:{contexto_archivos}" if contexto_archivos else ""}

INSTRUCCIONES:
1. Generá una secuencia de {clases_desarrollo} clases para desarrollar los contenidos.
2. Cada clase debe tener: número, título, objetivo específico, contenido principal,
   estrategia didáctica sugerida y duración en minutos.
3. La secuencia debe ser progresiva: de lo simple a lo complejo.
4. Incluí variedad de estrategias: exposición, trabajo grupal, resolución de problemas, etc.
5. Tené en cuenta la duración real de cada clase ({asignacion.minutos_por_hora_docente} minutos).
{f"6. La clase #{clases_contenido} es para evaluación {tipo_evaluacion}." if incluir_evaluacion else ""}

FORMATO DE RESPUESTA (JSON estricto, sin texto adicional):
{{
  "titulo": "{titulo_unidad}",
  "total_horas": {horas_docentes},
  "horas_emergentes": {clases_emergentes},
  "horas_contenido": {clases_contenido},
  "porcentaje_emergentes": {porcentaje_emergentes},
  "tiene_evaluacion": {str(incluir_evaluacion).lower()},
  "tipo_evaluacion": "{tipo_evaluacion or ""}",
  "clases": [
    {{
      "numero": 1,
      "titulo": "Título de la clase",
      "objetivo": "Objetivo específico",
      "contenido_principal": "Contenido a desarrollar",
      "estrategia_didactica": "Cómo se desarrollará la clase",
      "duracion_minutos": {asignacion.minutos_por_hora_docente},
      "es_evaluacion": false
    }}
  ]
}}
"""

    response = model.generate_content(prompt)
    return _parsear_respuesta_json(response.text)


# ===========================================================================
# PLANIFICACIÓN DIARIA
# ===========================================================================

def generar_planificacion_diaria(
    asignacion: Asignacion,
    titulo_clase: str,
    objetivo: str,
    contenido_principal: str,
    estrategia_sugerida: str,
    duracion_minutos: int,
    contexto_clases_anteriores: str,
    db: Session,
) -> dict:
    """
    Genera la planificación detallada de una clase individual.
    Incluye cronograma interno con los minutos de cada momento.
    """
    model = _get_model()
    contexto = _construir_contexto_asignacion(asignacion)
    contexto_archivos = _obtener_contexto_archivos(asignacion.id, asignacion.docente_id, db)

    prompt = f"""
Eres un experto en planificación educativa para educación secundaria y UTU en Uruguay.
Tu tarea es generar la planificación detallada de una clase individual.

{contexto}

DATOS DE LA CLASE:
- Título: {titulo_clase}
- Objetivo: {objetivo}
- Contenido principal: {contenido_principal}
- Estrategia sugerida: {estrategia_sugerida}
- Duración total: {duracion_minutos} minutos

{f"CONTEXTO DE CLASES ANTERIORES:{contexto_clases_anteriores}" if contexto_clases_anteriores else ""}
{f"FICHAS Y MATERIALES DE REFERENCIA:{contexto_archivos}" if contexto_archivos else ""}

INSTRUCCIONES:
1. Dividí la clase en momentos: inicio, desarrollo y cierre.
2. Para cada momento: descripción de la actividad, duración en minutos, rol del docente y rol del estudiante.
3. El inicio debe incluir motivación/enganche y repaso de clase anterior (máximo 10 min).
4. El desarrollo es el núcleo de la clase (60-70% del tiempo).
5. El cierre debe incluir síntesis y adelanto de próxima clase (últimos 5-10 min).
6. Sugerí materiales o recursos necesarios.
7. Tené en cuenta que la clase dura exactamente {duracion_minutos} minutos. Los tiempos deben sumar exactamente eso.

FORMATO DE RESPUESTA (JSON estricto, sin texto adicional):
{{
  "titulo": "{titulo_clase}",
  "objetivo": "{objetivo}",
  "duracion_total_minutos": {duracion_minutos},
  "momentos": [
    {{
      "nombre": "Inicio",
      "duracion_minutos": 10,
      "descripcion": "Descripción de la actividad",
      "rol_docente": "Qué hace el docente",
      "rol_estudiante": "Qué hacen los estudiantes"
    }},
    {{
      "nombre": "Desarrollo",
      "duracion_minutos": 30,
      "descripcion": "Descripción de la actividad",
      "rol_docente": "Qué hace el docente",
      "rol_estudiante": "Qué hacen los estudiantes"
    }},
    {{
      "nombre": "Cierre",
      "duracion_minutos": 5,
      "descripcion": "Descripción de la actividad",
      "rol_docente": "Qué hace el docente",
      "rol_estudiante": "Qué hacen los estudiantes"
    }}
  ],
  "recursos_necesarios": ["recurso 1", "recurso 2"],
  "tarea_sugerida": "Descripción de tarea para el hogar (opcional)"
}}
"""

    response = model.generate_content(prompt)
    return _parsear_respuesta_json(response.text)


# ===========================================================================
# ESTRUCTURAR DESARROLLO DIARIO (para el bot de Telegram)
# ===========================================================================

def estructurar_desarrollo_diario(
    texto_original: str,
    asignacion: Asignacion,
) -> str:
    """
    Toma el texto libre enviado por el docente via Telegram y lo estructura
    en 1-2 párrafos formales para el registro pedagógico.

    Args:
        texto_original: Texto crudo enviado por el docente
        asignacion: La asignación correspondiente

    Returns:
        Texto estructurado en formato formal
    """
    model = _get_model()
    contexto = _construir_contexto_asignacion(asignacion)

    prompt = f"""
Eres un asistente pedagógico para docentes de educación secundaria y UTU en Uruguay.
Tu tarea es tomar el registro informal de una clase y redactarlo de forma profesional.

{contexto}

REGISTRO INFORMAL DEL DOCENTE:
"{texto_original}"

INSTRUCCIONES:
1. Redactá el desarrollo de la clase en 1 o 2 párrafos formales.
2. Mantené toda la información relevante del texto original.
3. Usá lenguaje pedagógico apropiado para un registro docente oficial.
4. Escribí en tercera persona o en forma impersonal.
5. Si el docente menciona dificultades, emergentes o desvíos del plan, incluilos claramente.
6. NO inventes información que no esté en el texto original.
7. Respondé ÚNICAMENTE con el texto estructurado, sin introducción ni comentarios adicionales.
"""

    response = model.generate_content(prompt)
    return response.text.strip()


# ===========================================================================
# GENERAR BORRADOR DE REPLANIFICACIÓN
# ===========================================================================

def generar_borrador_replanificacion(
    asignacion: Asignacion,
    planificacion_actual: dict,
    desarrollos_recientes: list[str],
    unidades_pendientes: list[dict],
) -> dict:
    """
    Analiza los desarrollos diarios recientes y genera un borrador de
    replanificación si detecta desvíos significativos.

    Returns:
        Dict con el borrador propuesto y el motivo del cambio
    """
    model = _get_model()
    contexto = _construir_contexto_asignacion(asignacion)

    desarrollos_texto = "\n".join([f"- {d}" for d in desarrollos_recientes])
    unidades_texto = "\n".join([
        f"  Unidad {u['orden']}: {u['titulo']} ({u['horas_restantes']} horas restantes)"
        for u in unidades_pendientes
    ])

    prompt = f"""
Eres un experto en planificación educativa para educación secundaria y UTU en Uruguay.
Tu tarea es analizar el avance real de las clases y proponer ajustes a la planificación.

{contexto}

DESARROLLOS DE CLASES RECIENTES:
{desarrollos_texto}

UNIDADES PENDIENTES EN LA PLANIFICACIÓN:
{unidades_texto}

INSTRUCCIONES:
1. Analizá si hay desvíos entre lo planificado y lo realmente dado.
2. Si detectás desvíos significativos (más de 1-2 clases de diferencia), proponé ajustes.
3. Los ajustes pueden ser: redistribuir horas entre unidades, ajustar contenidos, etc.
4. Explicá claramente el motivo del cambio propuesto.
5. Si no hay desvíos significativos, indicalo en el motivo y dejá las unidades sin cambios.

FORMATO DE RESPUESTA (JSON estricto, sin texto adicional):
{{
  "hay_desvio": true,
  "motivo": "Explicación clara de qué ocurrió y por qué se propone el cambio",
  "unidades_ajustadas": [
    {{
      "orden": 1,
      "titulo": "Título de la unidad",
      "horas_originales": 10,
      "horas_propuestas": 12,
      "justificacion": "Por qué se ajusta esta unidad"
    }}
  ]
}}
"""

    response = model.generate_content(prompt)
    return _parsear_respuesta_json(response.text)


# ===========================================================================
# Helper interno: parsear JSON de la respuesta de Gemini
# ===========================================================================

def _parsear_respuesta_json(texto: str) -> dict:
    """
    Parsea la respuesta de Gemini que debe ser JSON.
    Gemini a veces envuelve el JSON en bloques ```json ... ```.
    Esta función los limpia antes de parsear.
    """
    import json
    import re

    # Limpiar bloques de código markdown si los hay
    texto_limpio = re.sub(r"```json\s*", "", texto)
    texto_limpio = re.sub(r"```\s*", "", texto_limpio)
    texto_limpio = texto_limpio.strip()

    try:
        return json.loads(texto_limpio)
    except json.JSONDecodeError as e:
        # Si falla el parseo, retornar la respuesta cruda en un dict
        return {
            "error": "No se pudo parsear la respuesta de Gemini",
            "respuesta_cruda": texto,
            "detalle": str(e),
        }