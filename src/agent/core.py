"""
Núcleo del Agente FinOps con soporte para Vertex AI y LangChain.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage

from config.settings import configuracion
from src.agent.prompts import PROMPT_SISTEMA_FINOPS
from src.agent.router import seleccionar_modelo_optimo
from src.tools import (
    query_billing_data,
    get_recommender_insights,
    list_unattached_disks,
    trigger_resource_action,
    obtener_herramientas_langchain
)

logger = logging.getLogger(__name__)

# Mapa de funciones directas para ejecución de herramientas
HERRAMIENTAS_MAP = {
    "query_billing_data": query_billing_data,
    "get_recommender_insights": get_recommender_insights,
    "list_unattached_disks": list_unattached_disks,
    "trigger_resource_action": trigger_resource_action,
}


class AgenteFinOps:
    """
    Agente de IA para optimización de FinOps e infraestructura en Google Cloud Platform.
    """

    def __init__(self, override_modelo: Optional[str] = None):
        self.override_modelo = override_modelo
        self.herramientas = obtener_herramientas_langchain()

    def _obtener_cliente_llm(self, modelo_nombre: str):
        """
        Instancia el cliente de Vertex AI para Gemini con herramientas vinculadas.
        """
        try:
            from langchain_google_vertexai import ChatVertexAI
            llm = ChatVertexAI(
                model_name=modelo_nombre,
                project=configuracion.gcp_project_id,
                location=configuracion.gcp_location,
                temperature=0.2,
                max_output_tokens=2048
            )
            return llm.bind_tools(self.herramientas)
        except Exception as e:
            logger.warning("No se pudo conectar con Vertex AI (%s). Se utilizará procesador local de respaldo.", str(e))
            return None

    def procesar_mensaje(self, mensaje_usuario: str, historial: Optional[List[Any]] = None) -> Dict[str, Any]:
        """
        Procesa una consulta de usuario o evento de alerta, ejecutando herramientas si es necesario.
        
        Args:
            mensaje_usuario: Consulta en lenguaje natural o payload de alerta.
            historial: Mensajes previos de la conversación.
            
        Returns:
            Diccionario con la respuesta final y herramientas invocadas.
        """
        modelo_seleccionado = self.override_modelo or seleccionar_modelo_optimo(mensaje_usuario)
        logger.info("Iniciando procesamiento con el modelo: %s", modelo_seleccionado)

        llm_con_herramientas = self._obtener_cliente_llm(modelo_seleccionado)
        
        mensajes = [SystemMessage(content=PROMPT_SISTEMA_FINOPS)]
        if historial:
            mensajes.extend(historial)
        mensajes.append(HumanMessage(content=mensaje_usuario))

        herramientas_ejecutadas = []

        if llm_con_herramientas:
            try:
                # Invocación inicial del LLM
                respuesta_ai = llm_con_herramientas.invoke(mensajes)
                
                # Bucle de Function Calling (Tool Calls)
                while respuesta_ai.tool_calls:
                    mensajes.append(respuesta_ai)
                    
                    for tool_call in respuesta_ai.tool_calls:
                        nombre_herramienta = tool_call["name"]
                        args = tool_call["args"]
                        tool_call_id = tool_call.get("id", "tool_call_id")
                        
                        logger.info("Invocando herramienta '%s' con argumentos: %s", nombre_herramienta, args)
                        
                        funcion = HERRAMIENTAS_MAP.get(nombre_herramienta)
                        if funcion:
                            resultado_herramienta = funcion(**args)
                        else:
                            resultado_herramienta = json.dumps({"error": f"Herramienta '{nombre_herramienta}' no encontrada"})

                        herramientas_ejecutadas.append({
                            "nombre": nombre_herramienta,
                            "argumentos": args,
                            "resultado": resultado_herramienta
                        })
                        
                        mensajes.append(ToolMessage(
                            tool_call_id=tool_call_id,
                            name=nombre_herramienta,
                            content=resultado_herramienta
                        ))
                    
                    # Llamar al modelo nuevamente con las salidas de las herramientas
                    respuesta_ai = llm_con_herramientas.invoke(mensajes)

                return {
                    "modelo_utilizado": modelo_seleccionado,
                    "respuesta": respuesta_ai.content,
                    "herramientas_ejecutadas": herramientas_ejecutadas
                }

            except Exception as e:
                logger.error("Error durante el ciclo de inferencia con Vertex AI: %s", str(e))
                # Fallback al modo heurístico
                return self._procesar_modo_heuristico(mensaje_usuario)
        else:
            return self._procesar_modo_heuristico(mensaje_usuario)

    def _procesar_modo_heuristico(self, mensaje_usuario: str) -> Dict[str, Any]:
        """
        Modo de contingencia/desarrollo local: detecta intención por reglas y ejecuta herramientas correspondientes.
        """
        logger.info("Procesando consulta en modo de respaldo heurístico.")
        texto = mensaje_usuario.lower()
        herramientas_ejecutadas = []
        
        if "disco" in texto or "huerfano" in texto or "unattached" in texto:
            res = list_unattached_disks()
            herramientas_ejecutadas.append({"nombre": "list_unattached_disks", "argumentos": {}, "resultado": res})
            datos = json.loads(res)
            
            if "discos" in datos and datos["discos"]:
                detalles = "\n".join([f"- **{d['nombre_disco']}** ({d['tamano_gb']} GB en `{d['zona']}`): Costo aprox. **${d['costo_mensual_estimado_usd']} USD/mes**" for d in datos["discos"]])
                respuesta = (
                    f"### 🔍 Reporte de Discos Persistentes Sin Vincular\n\n"
                    f"Se identificaron **{datos['total_discos_sin_vincular']} discos huérfanos** en el proyecto `{datos['proyecto']}`.\n\n"
                    f"{detalles}\n\n"
                    f"💰 **Ahorro potencial total:** `${datos['ahorro_mensual_potencial_usd']} USD/mes`.\n\n"
                    f"_Para eliminarlos y generar ahorro, puedes autorizar la acción de remediación correspondiente._"
                )
            else:
                respuesta = "✅ No se encontraron discos persistentes huérfanos en el proyecto. La asignación de almacenamiento es óptima."

        elif "recomienda" in texto or "right-sizing" in texto or "sugerencia" in texto:
            res = get_recommender_insights()
            herramientas_ejecutadas.append({"nombre": "get_recommender_insights", "argumentos": {}, "resultado": res})
            respuesta = f"### 💡 Recomendaciones de GCP Recommender API\n\n```json\n{res}\n```"

        elif "factura" in texto or "costo" in texto or "anomalía" in texto or "sku" in texto:
            sql_ejemplo = (
                f"SELECT service.description AS servicio, sku.description AS sku, SUM(cost) AS costo_total "
                f"FROM `{configuracion.gcp_project_id}.{configuracion.bigquery_billing_dataset}.{configuracion.bigquery_billing_table}` "
                f"WHERE DATE(_PARTITIONTIME) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY) "
                f"GROUP BY 1, 2 ORDER BY costo_total DESC LIMIT 5"
            )
            res = query_billing_data(sql_ejemplo)
            herramientas_ejecutadas.append({"nombre": "query_billing_data", "argumentos": {"query_sql": sql_ejemplo}, "resultado": res})
            respuesta = f"### 📊 Análisis de Costos Recientes (BigQuery FinOps)\n\nSe analizó la facturación de los últimos 7 días:\n```json\n{res}\n```"

        else:
            respuesta = (
                "👋 Hola, soy el **Agente de Monitoreo de Infraestructura y FinOps en GCP**.\n\n"
                "Puedo ayudarte con:\n"
                "- 📊 Análisis de variaciones y consultas de facturación en BigQuery (`query_billing_data`).\n"
                "- 💡 Recomendaciones de dimensionamiento e instancias ociosas (`get_recommender_insights`).\n"
                "- 💾 Detección de discos persistentes huérfanos (`list_unattached_disks`).\n"
                "- 🛠️ Acciones de remediación seguras con confirmación humana HITL (`trigger_resource_action`).\n\n"
                "¿En qué recurso o análisis de costo te gustaría profundizar hoy?"
            )

        return {
            "modelo_utilizado": "modo_local_heuristico",
            "respuesta": respuesta,
            "herramientas_ejecutadas": herramientas_ejecutadas
        }
