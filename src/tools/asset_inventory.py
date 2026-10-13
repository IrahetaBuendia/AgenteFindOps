"""
Herramienta para identificación de recursos huérfanos y discos sin vincular en Compute Engine.
"""

import json
import logging
from typing import Optional
try:
    from google.cloud import compute_v1
except ImportError:
    compute_v1 = None
from config.settings import configuracion

logger = logging.getLogger(__name__)


def list_unattached_disks(project_id: Optional[str] = None) -> str:
    """
    Identifica todos los discos persistentes en Compute Engine que no se encuentran adjuntos a ninguna máquina virtual.
    
    Args:
        project_id: ID del proyecto en GCP (por defecto usa el configurado en el sistema).
        
    Returns:
        JSON con el listado de discos huérfanos, su tamaño en GB, zona, tipo de disco y costo estimado.
    """
    proyecto = project_id or configuracion.gcp_project_id
    logger.info("Buscando discos persistentes sin vincular en el proyecto '%s'...", proyecto)
    
    if compute_v1 is None:
        return json.dumps({
            "error": "Librería google-cloud-compute no instalada en este entorno."
        }, ensure_ascii=False)

    try:
        cliente_discos = compute_v1.DisksClient()
        solicitud = compute_v1.AggregatedListDisksRequest(project=proyecto)
        
        discos_huerfanos = []
        
        for zona, respuesta_zona in cliente_discos.aggregated_list(request=solicitud):
            if respuesta_zona.disks:
                for disco in respuesta_zona.disks:
                    # Si la lista de users (instancias vinculadas) está vacía, el disco está huérfano
                    if not disco.users:
                        zona_nombre = zona.split("/")[-1] if "/" in zona else zona
                        tamano_gb = disco.size_gb
                        # Estimación base aproximada: $0.04 USD por GB/mes para disco estándar pd-standard
                        costo_estimado_usd = round(tamano_gb * 0.04, 2)
                        
                        discos_huerfanos.append({
                            "id_disco": disco.id,
                            "nombre_disco": disco.name,
                            "zona": zona_nombre,
                            "tamano_gb": tamano_gb,
                            "tipo_disco": disco.type_.split("/")[-1] if disco.type_ else "desconocido",
                            "fecha_creacion": disco.creation_timestamp,
                            "costo_mensual_estimado_usd": costo_estimado_usd
                        })

        total_ahorro_estimado = sum(d["costo_mensual_estimado_usd"] for d in discos_huerfanos)
        
        logger.info("Se encontraron %d discos sin vincular. Ahorro potencial: $%.2f USD/mes",
                    len(discos_huerfanos), total_ahorro_estimado)
                    
        return json.dumps({
            "proyecto": proyecto,
            "total_discos_sin_vincular": len(discos_huerfanos),
            "ahorro_mensual_potencial_usd": round(total_ahorro_estimado, 2),
            "discos": discos_huerfanos
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error("Error al consultar discos huérfanos en Compute Engine: %s", str(e))
        return json.dumps({
            "error": f"Fallo al listar discos persistentes sin vincular: {str(e)}"
        }, ensure_ascii=False)
