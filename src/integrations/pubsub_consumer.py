"""
Consumidor y parser de mensajes de alerta desde Cloud Pub/Sub (Budget Alerts y Monitoring).
"""

import base64
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def procesar_mensaje_pubsub(payload_solicitud: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decodifica y procesa mensajes provenientes de suscripciones Push de Cloud Pub/Sub.
    
    Args:
        payload_solicitud: Payload recibido en el webhook de Cloud Run enviado por Pub/Sub.
        
    Returns:
        Diccionario con los datos deserializados de la alerta.
    """
    mensaje_pubsub = payload_solicitud.get("message", {})
    datos_base64 = mensaje_pubsub.get("data")

    if not datos_base64:
        logger.warning("Mensaje de Pub/Sub recibido sin campo 'data'")
        return {"error": "Sin contenido de datos"}

    try:
        datos_decodificados = base64.b64decode(datos_base64).decode("utf-8")
        alerta_json = json.loads(datos_decodificados)
        
        logger.info("Alerta de Pub/Sub decodificada con éxito: %s", alerta_json.get("budgetDisplayName", "Alerta General"))
        return {
            "estado": "DECODIFICADO",
            "alerta": alerta_json,
            "atributos": mensaje_pubsub.get("attributes", {}),
            "id_mensaje": mensaje_pubsub.get("messageId")
        }

    except Exception as e:
        logger.error("Error al decodificar mensaje de Pub/Sub: %s", str(e))
        return {
            "error": f"Error al decodificar mensaje de Pub/Sub: {str(e)}"
        }
