"""
Módulo de Configuración y Variables de Entorno del Agente FinOps.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfiguracionSistema(BaseSettings):
    """
    Configuración global del sistema cargada desde variables de entorno.
    """
    # Identificación del Proyecto GCP
    gcp_project_id: str = "mi-proyecto-gcp"
    gcp_location: str = "us-central1"
    
    # Configuración de BigQuery para Facturación
    bigquery_billing_dataset: str = "billing_export"
    bigquery_billing_table: str = "gcp_billing_export_v1_000000_000000_000000"
    
    # Configuración de Modelos Vertex AI
    modelo_rapido: str = "gemini-1.5-flash"
    modelo_analitico: str = "gemini-1.5-pro"
    
    # Integración con ChatOps (Slack / Teams)
    slack_bot_token: Optional[str] = None
    slack_signing_secret: Optional[str] = None
    slack_default_channel: str = "#finops-alertas"
    
    # Seguridad y Human-in-the-Loop (HITL)
    requiere_confirmacion_hitl: bool = True
    workflows_remediacion_nombre: str = "remediacion-infraestructura"
    
    # Servidor FastAPI / Cloud Run
    puerto_servidor: int = 8080
    host_servidor: str = "0.0.0.0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


# Instancia única de configuración
configuracion = ConfiguracionSistema()
