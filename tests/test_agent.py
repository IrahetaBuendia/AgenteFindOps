"""
Pruebas unitarias para el Agente FinOps, herramientas y flujo Human-in-the-Loop (HITL).
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from src.agent.router import seleccionar_modelo_optimo
from src.tools.bigquery_billing import query_billing_data
from src.tools.remediator import trigger_resource_action, SOLICITUDES_HITL_PENDIENTES
from src.tools.asset_inventory import list_unattached_disks
from src.agent.core import AgenteFinOps


def test_enrutador_modelos():
    """
    Verifica que las consultas complejas y de anomalías vayan a Pro y las simples a Flash.
    """
    consulta_simple = "¿Qué discos huérfanos tenemos?"
    modelo_flash = seleccionar_modelo_optimo(consulta_simple)
    assert "flash" in modelo_flash

    consulta_compleja = "Explica la causa raíz y la anomalía de costos en el SKU de Compute Engine con varianza histórica"
    modelo_pro = seleccionar_modelo_optimo(consulta_compleja)
    assert "pro" in modelo_pro


def test_seguridad_query_billing_data():
    """
    Comprueba que solo se permitan consultas SELECT/WITH y se bloqueen inyecciones o mutaciones.
    """
    # Consulta de mutación prohibida
    resultado_drop = query_billing_data("DROP TABLE mi_tabla")
    datos_drop = json.loads(resultado_drop)
    assert "error" in datos_drop
    assert "Operación no permitida" in datos_drop["error"]

    # Consulta SELECT permitida (simulando cliente BQ)
    with patch("src.tools.bigquery_billing.bigquery") as mock_bq_module:
        mock_cliente = MagicMock()
        mock_job = MagicMock()
        mock_job.result.return_value = [{"sku": "N1-Standard", "costo": 120.5}]
        mock_cliente.query.return_value = mock_job
        mock_bq_module.Client.return_value = mock_cliente

        resultado_select = query_billing_data("SELECT sku, costo FROM billing_table")
        datos_select = json.loads(resultado_select)
        assert datos_select["total_registros"] == 1
        assert datos_select["datos"][0]["sku"] == "N1-Standard"


def test_remediacion_flujo_hitl():
    """
    Valida que una acción destructiva quede en estado de espera y requiera token HITL para ejecutarse.
    """
    SOLICITUDES_HITL_PENDIENTES.clear()
    recurso_id = "projects/test-proj/zones/us-central1-a/disks/disco-prueba-1"

    # Paso 1: Disparo sin confirmación previa
    respuesta_inicial_raw = trigger_resource_action(
        resource_id=recurso_id,
        action="delete_disk",
        confirmation_token=None
    )
    respuesta_inicial = json.loads(respuesta_inicial_raw)

    assert respuesta_inicial["estado"] == "REQUIERE_CONFIRMACION_HUMANA"
    assert "token_confirmacion" in respuesta_inicial
    token = respuesta_inicial["token_confirmacion"]

    # Paso 2: Aprobación con el token generado
    respuesta_confirmacion_raw = trigger_resource_action(
        resource_id=recurso_id,
        action="delete_disk",
        confirmation_token=token,
        usuario_solicitante="ing_finops"
    )
    respuesta_confirmacion = json.loads(respuesta_confirmacion_raw)

    assert respuesta_confirmacion["estado"] == "EJECUCION_INICIADA"
    assert respuesta_confirmacion["recurso_afectado"] == recurso_id


def test_agente_modo_heuristico():
    """
    Comprueba que el agente responda adecuadamente en modo local/heurístico para consultas de discos huérfanos.
    """
    with patch("src.tools.asset_inventory.compute_v1") as mock_compute_module:
        mock_disks_client = mock_compute_module.DisksClient
        mock_instancia = mock_disks_client.return_value
        
        # Simular respuesta de disco sin vincular
        disco_mock = MagicMock()
        disco_mock.id = "12345"
        disco_mock.name = "disco-huerfano-staging"
        disco_mock.size_gb = 100
        disco_mock.type_ = "pd-standard"
        disco_mock.creation_timestamp = "2026-10-01T00:00:00Z"
        disco_mock.users = []  # Sin usuarios vinculados = huérfano

        zona_mock = MagicMock()
        zona_mock.disks = [disco_mock]

        mock_instancia.aggregated_list.return_value = [("zones/us-central1-a", zona_mock)]

        agente = AgenteFinOps()
        resultado = agente.procesar_mensaje("¿Qué discos huérfanos tenemos?")
        
        assert "disco-huerfano-staging" in resultado["respuesta"]
        assert len(resultado["herramientas_ejecutadas"]) >= 1
