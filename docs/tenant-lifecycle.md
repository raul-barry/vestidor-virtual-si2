# Tenant Lifecycle SaaS

La transición de suscripciones está centralizada en `SubscriptionService`. Las fechas se comparan en UTC; solo suscripciones `ACTIVA` con `fecha_fin <= ahora` pasan a `VENCIDA`. Los estados históricos (`CANCELADA`, `FINALIZADA`, `VENCIDA`) no se reescriben. El vencimiento nunca cambia el estado de la organización. CU24.3 sigue resolviendo límites y características desde la suscripción actual.

No hay scheduler en el backend. Ejecutar a diario desde el directorio `backend`:

```powershell
python -m scripts.process_subscription_lifecycle --expiring-within-days 30
```

El comando vence suscripciones activas, y genera una sola entrada de auditoría `SUSCRIPCION_PROXIMA_VENCER` por suscripción al entrar en la ventana configurada. La clave de deduplicación está respaldada por un índice único.

Al programar en Render Cron Jobs, configurar el directorio de trabajo en `backend`, las mismas variables de entorno del servicio backend (incluidos `DATABASE_URL` y `SECRET_KEY`) y una ejecución diaria (UTC). No se crea ni se modifica el Cron Job en esta fase.

Renovación usa la asignación existente cuando no queda una suscripción activa; cambio y cancelación conservan su historial. Suspender/reactivar empresa cambia únicamente `Organizacion.estado` y registra el cambio. Repetir una solicitud con el estado actual no produce otro evento.
