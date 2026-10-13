"""
Módulo de registro e inicialización de herramientas del Agente FinOps.
"""

from typing import List, Callable
from langchain_core.tools import tool, StructuredTool
from pydantic import BaseModel, Field

from src.tools.bigquery_billing import query_billing_data
from src.tools.recommender import get_recommender_insights
from src.tools.asset_inventory import list_unattached_disks
from src.tools.remediator import trigger_resource_action


# Esquemas Pydantic para Function Calling en LangChain / Vertex AI

class EsquemaConsultaFacturacion(BaseModel):
    query_sql: str = Field(
        description="Consulta SQL analítica sobre la tabla de exportación de costos en BigQuery."
    )


class EsquemaRecomendaciones(BaseModel):
    project_id: str = Field(
        default="",
        description="ID del proyecto de GCP para obtener sugerencias de costo o tamaño."
    )
    category: str = Field(
        default="COST",
        description="Categoría de optimización ('COST', 'IDLE_RESOURCES', 'DISKS')."
    )


class EsquemaDiscosHuerfanos(BaseModel):
    project_id: str = Field(
        default="",
        description="ID del proyecto de GCP para identificar discos no vinculados."
    )


class EsquemaAccionRecurso(BaseModel):
    resource_id: str = Field(
        description="ID o URI del recurso GCP sobre el que se aplicará la acción."
    )
    action: str = Field(
        description="Acción a realizar: 'stop_vm', 'delete_disk' o 'resize_vm'."
    )
    confirmation_token: str = Field(
        default="",
        description="Token de confirmación HITL si la acción ya fue autorizada."
    )


def obtener_herramientas_langchain() -> List[StructuredTool]:
    """
    Construye y retorna la lista de herramientas estructuradas de LangChain.
    """
    return [
        StructuredTool.from_function(
            func=query_billing_data,
            name="query_billing_data",
            description="Ejecuta consultas SQL analíticas sobre la tabla de exportación de costos en BigQuery.",
            args_schema=EsquemaConsultaFacturacion
        ),
        StructuredTool.from_function(
            func=get_recommender_insights,
            name="get_recommender_insights",
            description="Obtiene sugerencias de optimización de costo y tamaño de máquinas desde GCP Recommender API.",
            args_schema=EsquemaRecomendaciones
        ),
        StructuredTool.from_function(
            func=list_unattached_disks,
            name="list_unattached_disks",
            description="Identifica discos persistentes no vinculados a ningún Compute Engine y calcula su costo mensual.",
            args_schema=EsquemaDiscosHuerfanos
        ),
        StructuredTool.from_function(
            func=trigger_resource_action,
            name="trigger_resource_action",
            description="Ejecuta remediaciones (detener VM, redimensionar, eliminar discos) tras aprobación HITL.",
            args_schema=EsquemaAccionRecurso
        ),
    ]


__all__ = [
    "query_billing_data",
    "get_recommender_insights",
    "list_unattached_disks",
    "trigger_resource_action",
    "obtener_herramientas_langchain"
]
