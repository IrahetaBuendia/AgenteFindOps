"""
Herramienta de integración con GCP Recommender API para insights de FinOps y dimensionamiento.
"""

import json
import logging
from typing import Optional
try:
    from google.cloud import recommender_v1
except ImportError:
    recommender_v1 = None
from config.settings import configuracion

logger = logging.getLogger(__name__)

# Tipos de recomendadores comunes en GCP FinOps
RECOMMANDERS_MAP = {
    "COST": "google.compute.instance.MachineTypeRecommender",
    "IDLE_RESOURCES": "google.compute.instance.IdleResourceRecommender",
    "DISKS": "google.compute.disk.IdleResourceRecommender"
}


def get_recommender_insights(project_id: Optional[str] = None, category: str = "COST") -> str:
    """
    Obtiene recomendaciones activas de optimización de costos y right-sizing de recursos en GCP.
    
    Args:
        project_id: ID del proyecto en GCP (por defecto usa el configurado en el sistema).
        category: Categoría de optimización ('COST', 'IDLE_RESOURCES', 'DISKS').
        
    Returns:
        JSON con la lista de recomendaciones, impacto estimado en costo y acciones sugeridas.
    """
    proyecto = project_id or configuracion.gcp_project_id
    recommender_id = RECOMMANDERS_MAP.get(category.upper(), RECOMMANDERS_MAP["COST"])
    ubicacion = configuracion.gcp_location
    
    logger.info("Consultando Recommender API para el proyecto '%s' (categoría: %s)", proyecto, category)
    
    try:
        cliente = recommender_v1.RecommenderClient()
        parent = f"projects/{proyecto}/locations/{ubicacion}/recommenders/{recommender_id}"
        
        solicitud = recommender_v1.ListRecommendationsRequest(parent=parent)
        recomendaciones_iter = cliente.list_recommendations(request=solicitud)
        
        lista_recomendaciones = []
        for rec in recomendaciones_iter:
            impacto = rec.primary_impact
            ahorro_estimado = None
            if impacto and impacto.cost_projection and impacto.cost_projection.cost:
                costo = impacto.cost_projection.cost
                ahorro_estimado = f"{costo.units + (costo.nanos / 1e9):.2f} {costo.currency_code}"
            
            lista_recomendaciones.append({
                "nombre_recomendacion": rec.name,
                "descripcion": rec.description,
                "prioridad": rec.priority.name if hasattr(rec.priority, "name") else str(rec.priority),
                "ahorro_estimado_mensual": ahorro_estimado,
                "estado": rec.state_info.state.name if hasattr(rec.state_info.state, "name") else str(rec.state_info.state),
                "tipo_recomendador": rec.recommender_subtype
            })
            
        logger.info("Recomendaciones encontradas: %d", len(lista_recomendaciones))
        return json.dumps({
            "proyecto": proyecto,
            "categoria": category,
            "total_recomendaciones": len(lista_recomendaciones),
            "recomendaciones": lista_recomendaciones
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error("Error al consultar GCP Recommender API: %s", str(e))
        return json.dumps({
            "error": f"Fallo al consultar GCP Recommender API: {str(e)}"
        }, ensure_ascii=False)
