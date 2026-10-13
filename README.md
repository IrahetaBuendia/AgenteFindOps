# AgenteFindOps - Monitoreo de Infraestructura y FinOps en GCP

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Google Cloud Platform](https://img.shields.io/badge/GCP-Cloud%20Run%20%7C%20BigQuery-4285F4.svg)](https://cloud.google.com/)
[![Gemini 1.5](https://img.shields.io/badge/Vertex%20AI-Gemini%201.5%20Pro%20%26%20Flash-8E24AA.svg)](https://cloud.google.com/vertex-ai)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)

**AgenteFindOps** es una solución autónoma e interactiva basada en **Gemini 1.5** sobre **Google Cloud Platform (GCP)**. Su propósito es monitorear continuamente el consumo de infraestructura, optimizar costos operativos (FinOps), detectar anomalías en la facturación y ofrecer capacidades de remediación rápida en lenguaje natural mediante integración ChatOps (Slack / Teams) con gobernanza **Human-in-the-Loop (HITL)**.

---

## 1. Arquitectura de Referencia

```text
[ Cloud Billing Export ] ────► [ BigQuery ] ──────┐
                                                  │
[ Cloud Monitoring ]    ────► [ Pub/Sub ]  ──────┼──► [ Cloud Run: AgenteFindOps ] ◄──► [ Gemini 1.5 Pro/Flash ]
                                                  │       (LangChain / FastAPI)
[ GCP Recommender API ] ────► [ Cloud Assets ] ───┘             │
                                                                 ▼
                                                  [ Cloud Workflows / Cloud Functions ]
                                                                 │
                                                                 ▼
                                                    [ ChatOps / Remedación HITL ]
                                                               (Slack / Teams)
```

---

## 2. Componentes y Servicios de GCP

### 2.1 Ingesta de Datos e Infraestructura
- **Cloud Billing Data Export**: Exportación continua y detallada de facturación hacia BigQuery.
- **GCP Recommender API & Cloud Asset Inventory**: Detección de activos ociosos y recomendaciones de *right-sizing*.
- **Cloud Logging & Cloud Monitoring**: Disparadores de alertas presupuestarias e infraestructura vía Pub/Sub.

### 2.2 Motor de Razonamiento e IA
- **Google Cloud Run**: Alojamiento serverless en contenedor para la API y orquestación del agente.
- **Vertex AI (Gemini 1.5 Flash / Pro)**:
  - **Gemini 1.5 Flash**: Consultas rápidas, triaje y parsing de eventos de alerta entrantes.
  - **Gemini 1.5 Pro**: Análisis analítico de variaciones en BigQuery, agregaciones por SKU y diagnóstico *root-cause*.
- **Secret Manager**: Almacenamiento seguro de tokens de Slack/Teams y credenciales del sistema.

---

## 3. Herramientas del Agente (Function Calling)

| Herramienta | Descripción | Parámetros | Servicio GCP Destino |
| :--- | :--- | :--- | :--- |
| `query_billing_data` | Ejecuta consultas SQL analíticas sobre la tabla de exportación de costos | `query_sql` | BigQuery |
| `get_recommender_insights` | Obtiene sugerencias de optimización de costo y tamaño de máquinas | `project_id`, `category` | GCP Recommender API |
| `list_unattached_disks` | Identifica discos persistentes no vinculados y calcula el ahorro mensual proyectado | `project_id` | Compute Engine / Asset Inventory |
| `trigger_resource_action` | Ejecuta remediaciones controladas (detener VM, redimensionar, eliminar discos) tras confirmación HITL | `resource_id`, `action`, `confirmation_token` | Cloud Workflows / Cloud Functions |

---

## 4. Casos de Uso y Flujos de Trabajo

### Caso de Uso 1: Detección y Análisis de Anomalías de Costos
1. **Disparador**: Webhook de Cloud Billing emite una alerta por pico de gasto a Cloud Pub/Sub.
2. **Proceso**: `AgenteFindOps` intercepta el evento, enruta la tarea a **Gemini 1.5 Pro** y ejecuta `query_billing_data` para aislar el SKU con mayor varianza.
3. **Salida**: Genera un diagnóstico de causa raíz y envía una notificación formateada a Slack.

### Caso de Uso 2: Limpieza Interactiva de Recursos Huérfanos
1. **Consulta**: En Slack, el operador pregunta: *"¿Qué recursos sin usar tenemos en el entorno de Staging?"*
2. **Proceso**: El agente invoca `get_recommender_insights` y `list_unattached_disks`, calculando el ahorro potencial mensual.
3. **Respuesta e Interacción**: El agente responde con la lista y genera botones interactivos con tokens de seguridad temporales para autorizar la remediación.

---

## 5. Seguridad y Gobernanza (IAM)

El principio de **Mínimo Privilegio** se implementa asignando únicamente los siguientes roles a la Cuenta de Servicio de Cloud Run:
- `roles/bigquery.dataViewer`: Lectura de tablas de facturación.
- `roles/bigquery.jobUser`: Ejecución de consultas analíticas.
- `roles/recommender.viewer`: Lectura de recomendaciones de optimización.
- `roles/cloudasset.viewer`: Consulta de inventario de recursos.
- `roles/aiplatform.user`: Invocación de modelos en Vertex AI.
- `roles/workflows.invoker`: Ejecución de remediaciones autorizadas.

**Human-in-the-Loop (HITL)**: Ninguna acción destructiva o que modifique infraestructura se ejecuta sin una autorización explícita previa por parte de un usuario autorizado en el canal de chat.

---

## 6. Estructura del Código

```text
AgenteFindOps/
├── config/
│   ├── settings.py              # Variables de entorno y configuración centralizada
│   └── iam_policies.json        # Matriz de roles y permisos IAM mínimos
├── src/
│   ├── agent/
│   │   ├── core.py              # Motor central AgenteFindOps y Function Calling
│   │   ├── prompts.py           # Prompts del sistema FinOps y análisis de anomalías
│   │   └── router.py            # Enrutador inteligente Gemini Flash vs Pro
│   ├── tools/
│   │   ├── __init__.py          # Registro y esquemas para Function Calling
│   │   ├── bigquery_billing.py  # Herramienta: query_billing_data
│   │   ├── recommender.py       # Herramienta: get_recommender_insights
│   │   ├── asset_inventory.py   # Herramienta: list_unattached_disks
│   │   └── remediator.py        # Herramienta: trigger_resource_action (HITL)
│   ├── integrations/
│   │   ├── slack_bot.py         # Formateo de bloques y botones HITL para Slack
│   │   └── pubsub_consumer.py   # Ingesta de alertas presupuestarias desde Pub/Sub
│   └── main.py                  # API FastAPI para Cloud Run
├── tests/
│   └── test_agent.py            # Pruebas unitarias de herramientas y razonamiento
├── Dockerfile                   # Imagen lista para Cloud Run
├── requirements.txt             # Dependencias del proyecto
└── README.md                    # Documentación técnica
```

---

## 7. Instalación y Uso Local

### 7.1 Configuración de Entorno
```bash
# Clonar el repositorio
git clone https://github.com/IrahetaBuendia/AgenteFindOps.git
cd AgenteFindOps

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
```

### 7.2 Ejecución de Pruebas Unitarias
```bash
pytest tests/ -v
```

### 7.3 Iniciar el Servidor de Desarrollo
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8080 --reload
```

---

## 8. Despliegue en Google Cloud Run

```bash
gcloud run deploy agente-findops \
    --source . \
    --region us-central1 \
    --service-account sa-finops-agent@MI_PROYECTO.iam.gserviceaccount.com \
    --set-env-vars GCP_PROJECT_ID=MI_PROYECTO,GCP_LOCATION=us-central1 \
    --allow-unauthenticated
```
