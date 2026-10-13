"""
Servidor Principal FastAPI para el Agente FinOps en Google Cloud Run.
"""

import json
import logging
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel

from config.settings import configuracion
from src.agent.core import AgenteFinOps
from src.tools.remediator import trigger_resource_action
from src.integrations.pubsub_consumer import procesar_mensaje_pubsub
from src.integrations.slack_bot import slack_chatops

# Configuración básica de logs en español
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("FinOpsAgentApp")

app = FastAPI(
    title="AgenteFindOps - Monitoreo de Infraestructura y FinOps en GCP",
    description="Servicio Serverless en Cloud Run para monitoreo de costos, optimización y remediación interactiva con Gemini 1.5",
    version="1.0.0"
)

agente = AgenteFinOps()


class SolicitudChat(BaseModel):
    mensaje: str
    usuario: str = "usuario_default"
    canal: str = "slack"


class SolicitudAprobacionHITL(BaseModel):
    token_confirmacion: str
    resource_id: str
    action: str
    usuario: str = "operador_finops"


@app.get("/health")
def estado_salud():
    """
    Endpoint de comprobación de salud para Cloud Run.
    """
    return {
        "estado": "SALUDABLE",
        "servicio": "Agente FinOps GCP",
        "proyecto": configuracion.gcp_project_id,
        "region": configuracion.gcp_location
    }


@app.post("/api/chat")
async def chat_interactivo(solicitud: SolicitudChat):
    """
    Endpoint para interacción directa o bots en lenguaje natural.
    """
    logger.info("Recibida consulta de chat del usuario '%s': %s", solicitud.usuario, solicitud.mensaje)
    resultado = agente.procesar_mensaje(solicitud.mensaje)
    return resultado


@app.post("/api/hitl/confirmar")
async def confirmar_accion_hitl(solicitud: SolicitudAprobacionHITL):
    """
    Endpoint para confirmar la ejecución de una acción destructiva/remediación.
    """
    logger.info(
        "Confirmación HITL recibida de '%s' para acción '%s' en recurso '%s'",
        solicitud.usuario, solicitud.action, solicitud.resource_id
    )
    resultado_raw = trigger_resource_action(
        resource_id=solicitud.resource_id,
        action=solicitud.action,
        confirmation_token=solicitud.token_confirmacion,
        usuario_solicitante=solicitud.usuario
    )
    return json.loads(resultado_raw)


@app.post("/api/webhooks/pubsub")
async def webhook_pubsub(request: Request, background_tasks: BackgroundTasks):
    """
    Recepción de eventos de alertas de presupuesto y métricas de Cloud Pub/Sub.
    """
    body = await request.json()
    datos_alerta = procesar_mensaje_pubsub(body)
    
    if "error" in datos_alerta:
        raise HTTPException(status_code=400, detail=datos_alerta["error"])

    logger.info("Procesando alerta entrante de Pub/Sub en segundo plano...")
    
    # Procesar la alerta de forma asíncrona para responder rápido a Pub/Sub
    def tarea_analisis_alerta(alerta_dict: Dict[str, Any]):
        mensaje_analisis = f"ALERTA_PRESUPUESTO_PUBSUB: {json.dumps(alerta_dict, ensure_ascii=False)}"
        resultado = agente.procesar_mensaje(mensaje_analisis)
        slack_chatops.enviar_alerta_con_hitl(
            canal=configuracion.slack_default_channel,
            titulo="Anomalía de Costos Detectada",
            resumen=resultado.get("respuesta", "Se detectó variación presupuestaria."),
            recurso_id="múltiples-recursos-gcp",
            accion="revisión_inmediata",
            token_confirmacion="N/A"
        )

    background_tasks.add_task(tarea_analisis_alerta, datos_alerta.get("alerta", {}))
    return {"estado": "ALERTA_RECIBIDA_Y_EN_PROCESAMIENTO"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=configuracion.host_servidor,
        port=configuracion.puerto_servidor,
        reload=False
    )
