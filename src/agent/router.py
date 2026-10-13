"""
Enrutador dinámico de modelos de IA (Gemini 1.5 Flash vs Gemini 1.5 Pro).
"""

import logging
from config.settings import configuracion

logger = logging.getLogger(__name__)

# Palabras clave que requieren el razonamiento profundo de Gemini 1.5 Pro
PALABRAS_CLAVE_ANALISIS_COMPLEJO = [
    "anomalía", "anomalia", "varianza", "root-cause", "causa raíz",
    "bigquery", "facturación histórica", "proyección", "agregación",
    "sku", "análisis profundo", "diagnóstico", "cost breakdown"
]


def seleccionar_modelo_optimo(mensaje_o_evento: str) -> str:
    """
    Selecciona entre Gemini 1.5 Flash y Gemini 1.5 Pro según la complejidad del mensaje.
    
    - Gemini 1.5 Flash: Consultas directas, parsing rápido, listados de recursos, preguntas simples.
    - Gemini 1.5 Pro: Análisis de anomalías, agregaciones complejas en BigQuery y diagnósticos root-cause.
    
    Args:
        mensaje_o_evento: Texto de la consulta del usuario o payload del evento de alerta.
        
    Returns:
        Nombre del modelo de Vertex AI a utilizar.
    """
    texto_minusculas = mensaje_o_evento.lower()
    
    es_analisis_complejo = any(clave in texto_minusculas for clave in PALABRAS_CLAVE_ANALISIS_COMPLEJO)
    longitud_elevada = len(mensaje_o_evento) > 600
    
    if es_analisis_complejo or longitud_elevada:
        logger.info("Enrutando tarea hacia Gemini 1.5 Pro (Razonamiento Complejo/FinOps)")
        return configuracion.modelo_analitico
    
    logger.info("Enrutando tarea hacia Gemini 1.5 Flash (Respuesta Rápida/Parsing)")
    return configuracion.modelo_rapido
