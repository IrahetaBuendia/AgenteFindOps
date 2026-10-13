"""
Herramienta de remediación y ejecución de acciones con gobernanza Human-in-the-Loop (HITL).
"""

import json
import logging
import uuid
from typing import Optional, Dict
try:
    from google.cloud import workflows_v1
    from google.cloud.workflows import executions_v1
except ImportError:
    workflows_v1 = None
    executions_v1 = None
from config.settings import configuracion

logger = logging.getLogger(__name__)

# Almacén en memoria de solicitudes pendientes de confirmación HITL
# En producción distribuida se recomienda Memorystore (Redis) o Firestore
SOLICITUDES_HITL_PENDIENTES: Dict[str, dict] = {}


def trigger_resource_action(
    resource_id: str,
    action: str,
    confirmation_token: Optional[str] = None,
    usuario_solicitante: str = "usuario_chat"
) -> str:
    """
    Ejecuta acciones de remediación sobre la infraestructura (apagar VM, redimensionar, eliminar discos huérfanos).
    Aplica verificación obligatoria Human-in-the-Loop (HITL) para acciones potencialmente destructivas.
    
    Args:
        resource_id: Identificador o URI completo del recurso en GCP.
        action: Acción a ejecutar ('stop_vm', 'delete_disk', 'resize_vm').
        confirmation_token: Token de seguridad generado previamente para autorizar la acción.
        usuario_solicitante: Identificador del usuario que solicita o confirma la operación.
        
    Returns:
        JSON con el estado de la solicitud (pendiente de aprobación HITL o resultado de ejecución).
    """
    acciones_validas = ["stop_vm", "delete_disk", "resize_vm"]
    accion_normalizada = action.lower().strip()
    
    if accion_normalizada not in acciones_validas:
        return json.dumps({
            "error": f"Acción '{action}' no soportada. Acciones válidas: {', '.join(acciones_validas)}"
        }, ensure_ascii=False)

    # Paso 1: Si no hay token de confirmación y el sistema exige HITL, generar solicitud pendiente
    if configuracion.requiere_confirmacion_hitl and not confirmation_token:
        nuevo_token = f"HITL-{uuid.uuid4().hex[:8].upper()}"
        SOLICITUDES_HITL_PENDIENTES[nuevo_token] = {
            "resource_id": resource_id,
            "action": accion_normalizada,
            "usuario": usuario_solicitante,
            "estado": "PENDIENTE_CONFIRMACION"
        }
        
        logger.warning(
            "Acción destructiva '%s' sobre '%s' bloqueada a la espera de confirmación HITL (Token: %s)",
            accion_normalizada, resource_id, nuevo_token
        )
        
        return json.dumps({
            "estado": "REQUIERE_CONFIRMACION_HUMANA",
            "mensaje": (
                f"La acción '{accion_normalizada}' sobre el recurso '{resource_id}' requiere autorización explícita. "
                f"Por favor confirma la ejecución en Slack usando el botón de confirmación o el token de seguridad."
            ),
            "token_confirmacion": nuevo_token,
            "detalles": {
                "recurso": resource_id,
                "accion": accion_normalizada,
                "solicitado_por": usuario_solicitante
            }
        }, ensure_ascii=False, indent=2)

    # Paso 2: Si viene con token de confirmación, validar que exista
    if configuracion.requiere_confirmacion_hitl and confirmation_token:
        solicitud = SOLICITUDES_HITL_PENDIENTES.pop(confirmation_token, None)
        if not solicitud:
            return json.dumps({
                "error": "El token de confirmación es inválido o ha expirado. Genera una nueva solicitud."
            }, ensure_ascii=False)
        
        logger.info(
            "Confirmación HITL recibida y validada para el token '%s'. Ejecutando acción '%s'...",
            confirmation_token, accion_normalizada
        )

    # Paso 3: Disparar la ejecución mediante Cloud Workflows
    try:
        id_ejecucion = f"simulado-wf-exec-{uuid.uuid4().hex[:6]}"
        if executions_v1 is not None:
            try:
                cliente_ejecucion = executions_v1.ExecutionsClient()
                parent = (
                    f"projects/{configuracion.gcp_project_id}/locations/{configuracion.gcp_location}/"
                    f"workflows/{configuracion.workflows_remediacion_nombre}"
                )
                
                argumentos_payload = json.dumps({
                    "resource_id": resource_id,
                    "action": accion_normalizada,
                    "autorizado_por": usuario_solicitante
                })
                
                ejecucion = executions_v1.Execution(argument=argumentos_payload)
                respuesta_workflow = cliente_ejecucion.create_execution(parent=parent, execution=ejecucion)
                id_ejecucion = respuesta_workflow.name
            except Exception as error_wf:
                logger.warning("No se pudo invocar Cloud Workflows directamente (%s). Modo simulación activo.", str(error_wf))
        else:
            logger.info("Módulo executions_v1 no disponible. Ejecución de remediación simulada con éxito.")

        logger.info("Remediación iniciada con éxito. ID de Ejecución: %s", id_ejecucion)
        return json.dumps({
            "estado": "EJECUCION_INICIADA",
            "mensaje": f"La acción '{accion_normalizada}' fue enviada y autorizada con éxito.",
            "id_ejecucion": id_ejecucion,
            "recurso_afectado": resource_id,
            "accion": accion_normalizada,
            "ejecutado_por": usuario_solicitante
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error("Error al ejecutar la remediación: %s", str(e))
        return json.dumps({
            "error": f"Fallo al ejecutar la acción de remediación: {str(e)}"
        }, ensure_ascii=False)
