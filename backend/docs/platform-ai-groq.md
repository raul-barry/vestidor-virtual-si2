# Configuración central de IA con Groq

## Alcance e inventario

- **Reportes empresariales:** `AiReportService` calcula métricas con `ReportRepository` dentro de la organización autenticada y usa Groq solo para redactar observaciones y recomendaciones. La llamada sale del backend.
- **Probador virtual:** `GeminiVirtualTryOnProvider` sigue usando Gemini cuando está configurado, porque Groq no reemplaza la edición/generación de imágenes de prendas. Sin Gemini se conserva el proveedor local existente.
- **Recomendaciones de catálogo y asistente de moda:** `RecommendationService` y `FashionAssistantService` usan reglas y datos reales; no consumen un LLM.
- **Reportes por voz:** Angular usa `SpeechRecognition`/`webkitSpeechRecognition` y `speechSynthesis` del navegador. No se envían grabaciones al proveedor. El selector de transcripción queda preparado, pero no está conectado a un flujo existente.
- **Móvil:** Flutter consume los endpoints de experiencia existentes; no se encontró un cliente LLM independiente.
- **UML:** no se encontró asistente ni flujo de modelado UML en FastAPI, Angular o Flutter. La capacidad `uml_assistant` queda asignada en la configuración, pero no hay consumidor hasta que exista ese módulo.
- **Interpretación de imágenes:** Groq tiene una capacidad central invocable, utilizable para imágenes compatibles; no se conecta al probador virtual porque ese flujo edita/genera una imagen y conserva Gemini.
- **Transcripción de voz:** la integración central llama al endpoint Groq Whisper y envía idioma `es`. El flujo actual de reportes continúa usando el reconocimiento del navegador y no envía audio al backend.
- **Otros proveedores:** `GROK_API_KEY` y `GrokClient` son la integración previa de xAI Grok, distinta de Groq. Los reportes dejan de usar ese cliente. `FASHN_API_KEY` no está conectado al servicio actual del probador.

## Configuración y seguridad

La pantalla global está en `/platform/ai`, protegida por `platformAdminGuard`; el backend exige `get_current_platform_admin`. La API Key se cifra con Fernet en `platform_ai_config.encrypted_api_key`. Configure `AI_CONFIG_ENCRYPTION_KEY` en el entorno secreto del backend usando una clave Fernet generada por `cryptography.fernet.Fernet.generate_key()`. Mantenga copia de seguridad protegida de esa clave: perderla impide descifrar la API Key almacenada. No use una clave de ejemplo ni la guarde en el repositorio.

La clave Groq solo se transmite al backend, se guarda cifrada y las respuestas exponen únicamente estado y máscara. Los registros de auditoría guardan actor, acción y modelos, nunca la API Key. La configuración es global, no pertenece a un tenant. Los datos de cada reporte siguen limitados por el tenant de la sesión.

## Modelos y capacidades

Valores iniciales solicitados: `openai/gpt-oss-120b` (texto principal), `openai/gpt-oss-20b` (texto rápido), `qwen/qwen3.8-27b` (visión experimental) y `whisper-large-v3-turbo` (transcripción). Los IDs se validan contra Groq `/models` antes de guardarlos. Los modelos de visión/transcripción aparecen solo en el selector de su capacidad. El modelo de visión no se selecciona automáticamente para producción; reportes usan exclusivamente el principal.

Las asignaciones para las ocho capacidades se persisten en el JSON de `platform_ai_config.models`, cuya tabla ya provee la migración 0038. La pantalla `/platform/ai` permite consultar los modelos, reasignar cada capacidad, probar texto, imagen o transcripción y reponer valores predeterminados. El catálogo consultado clasifica capacidades; no sustituye la prueba real del proveedor.

La clave cifrada en PostgreSQL tiene prioridad. Si no existe, el servicio usa `GROQ_API_KEY` desde el entorno. `AI_CONFIG_ENCRYPTION_KEY` no se genera ni rota automáticamente. El servicio reintenta una sola vez fallos transitorios de red/HTTP 502-504, con timeout limitado. Los reportes pasan `business_reports` explícitamente.

## Migración

La revisión `20261106_0038` agrega tablas para configuración global y auditoría. Es reversible, no altera registros de negocio. Debe aplicarse por el proceso habitual de despliegue; esta implementación no ejecutó migraciones ni se conectó a PostgreSQL.

## Limitaciones

- Requiere API Key activa de Groq y `AI_CONFIG_ENCRYPTION_KEY` configurada si la clave se guarda cifrada en PostgreSQL. `GROQ_API_KEY` sirve de fallback para desarrollo.
- Los modelos, capacidades y cuotas dependen de la cuenta de Groq al momento de consultar.
- Gemini permanece como proveedor de edición de imágenes; el reconocimiento/síntesis de voz sigue dependiendo del navegador.
