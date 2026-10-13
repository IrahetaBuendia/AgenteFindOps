"""
Manejador de integración con Slack (ChatOps) y formateo de bloques interactivos.
"""

import logging
from typing import Dict, Any, List
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from config.settings import configuracion

logger = logging.getLogger(__name__)


class SlackChatOps:
    """
    Cliente para envío de alertas y manejo de interacciones en Slack.
    """

    def __init__(self):
        self.token = configuracion.slack_bot_token
        self.cliente = WebClient(token=self.token) if self.token else None

    def enviar_alerta_con_hitl(
        self,
        canal: str,
        titulo: str,
        resumen: str,
        recurso_id: str,
        accion: str,
        token_confirmacion: str
    ) -> bool:
        """
        Publica un mensaje enriquecido en Slack con botones interactivos para confirmación HITL.
        """
        bloques = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 Alerta FinOps: {titulo}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": resumen
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Recurso Afectado:*\n`{recurso_id}`"},
                    {"type": "mrkdwn", "text": f"*Acción Propuesta:*\n`{accion}`"},
                    {"type": "mrkdwn", "text": f"*Token de Seguridad:*\n`{token_confirmacion}`"},
                    {"type": "mrkdwn", "text": "*Gobernanza:*\n`Human-in-the-Loop Requerido`"}
                ]
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "✅ Autorizar y Ejecutar", "emoji": True},
                        "style": "primary",
                        "value": f"{token_confirmacion}:{recurso_id}:{accion}",
                        "action_id": "aprobar_remediacion_hitl"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "❌ Cancelar Acción", "emoji": True},
                        "style": "danger",
                        "value": f"cancelar:{token_confirmacion}",
                        "action_id": "rechazar_remediacion_hitl"
                    }
                ]
            }
        ]

        if not self.cliente:
            logger.info("[Simulación Slack] Mensaje que se enviaría al canal '%s':\n%s", canal, resumen)
            return True

        try:
            self.cliente.chat_postMessage(channel=canal, blocks=bloques, text=titulo)
            logger.info("Alerta con botones HITL enviada exitosamente al canal de Slack: %s", canal)
            return True
        except SlackApiError as e:
            logger.error("Error al enviar mensaje a Slack: %s", e.response["error"])
            return False


# Instancia única de ChatOps
slack_chatops = SlackChatOps()
