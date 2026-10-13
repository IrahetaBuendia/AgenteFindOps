"""
Herramienta para ejecución y análisis de consultas de facturación en BigQuery.
"""

import json
import logging
from typing import Dict, Any
try:
    from google.cloud import bigquery
except ImportError:
    bigquery = None
from config.settings import configuracion

logger = logging.getLogger(__name__)


def query_billing_data(query_sql: str) -> str:
    """
    Ejecuta consultas analíticas SQL en BigQuery sobre la exportación de facturación de GCP.
    
    Args:
        query_sql: Consulta SQL estándar para consultar costos, variaciones de SKUs o tendencias.
        
    Returns:
        Cadena formateada en JSON con las filas de resultados o mensaje de error.
    """
    logger.info("Ejecutando consulta de facturación en BigQuery: %s", query_sql)
    
    # Validación de seguridad: permitir exclusivamente operaciones de lectura (SELECT)
    sql_limpio = query_sql.strip().upper()
    if not sql_limpio.startswith("SELECT") and not sql_limpio.startswith("WITH"):
        return json.dumps({
            "error": "Operación no permitida. Solo se autorizan consultas de tipo lectura (SELECT/WITH)."
        }, ensure_ascii=False)

    if bigquery is None:
        return json.dumps({
            "error": "Librería google-cloud-bigquery no instalada en este entorno."
        }, ensure_ascii=False)

    try:
        cliente_bq = bigquery.Client(project=configuracion.gcp_project_id)
        
        # Configurar límites razonables de escaneo para control de costos de consulta
        job_config = bigquery.QueryJobConfig(
            maximum_bytes_billed=1000 * 1024 * 1024  # Máximo 1 GB por consulta analítica
        )
        
        query_job = cliente_bq.query(query_sql, job_config=job_config)
        resultados = query_job.result()
        
        filas = [dict(row) for row in resultados]
        
        # Convertir tipos no serializables si existen (fechas, decimales)
        for fila in filas:
            for clave, valor in fila.items():
                if hasattr(valor, "isoformat"):
                    fila[clave] = valor.isoformat()
                elif hasattr(valor, "__float__"):
                    fila[clave] = float(valor)

        logger.info("Consulta de BigQuery completada con éxito. Registros obtenidos: %d", len(filas))
        return json.dumps({
            "total_registros": len(filas),
            "datos": filas[:50]  # Limitar a las primeras 50 filas para optimizar tokens
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error("Error al ejecutar consulta en BigQuery: %s", str(e))
        return json.dumps({
            "error": f"Fallo en la ejecución de la consulta en BigQuery: {str(e)}"
        }, ensure_ascii=False)
