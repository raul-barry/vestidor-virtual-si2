# Estado operativo de las características SaaS

Fecha de validación: 3 de noviembre de 2026.

Los registros de `PlanCaracteristica` describen disponibilidad configurada en
Estilo, Moda y Glamour. El registro de una característica no implica por sí
mismo que exista una funcionalidad operativa ni que una ruta esté protegida.

## Controles conectados

- `PlanAccessService.require_branch_capacity()` se invoca al crear y reactivar
  sucursales. Cuenta sucursales activas y aplica los límites del plan.
- `PlanAccessService.require_feature()` resuelve el plan y consulta la matriz
  de características. Los reportes requieren y aplican las características de plan correspondientes.
- La expiración y la política de suscripción inactiva se aplican a los
  controles anteriores. El catálogo público de productos y las funciones de
  cliente no se bloquean por estas características premium.

## Características registradas sin endpoints premium

Las siguientes claves son metadatos de disponibilidad; no deben presentarse
como operaciones disponibles hasta implementar y proteger sus endpoints:

- `operaciones_offline`
- `sincronizacion`
- `reportes_gemini`
- `comparacion_sucursales`
- `reportes_voz`
- `machine_learning`
- `prediccion_demanda`
- `segmentacion_kmeans`
- `dashboard_predictivo`

Los endpoints existentes de Fashion Assistant, recomendaciones y vestidor
virtual son funciones de experiencia de cliente. No implementan los reportes
Gemini empresariales y no están condicionados por `reportes_gemini`.

`catalogo_offline` está registrado en los tres planes, pero la aplicación
Flutter actual consulta el catálogo mediante HTTP y no implementa persistencia
offline del catálogo. Por tanto, esa característica también permanece como
declaración de plan pendiente de una implementación offline real.

`exportacion_pdf_excel` habilita la descarga tenant-scoped de los reportes empresariales en PDF y XLSX. El endpoint conserva filtros autorizados, registra la exportación y responde con `no-store`.

## Matriz inicial registrada

| Plan | Sucursales activas | Características registradas |
| --- | ---: | ---: |
| Estilo | 2 | 8 comunes |
| Moda | 10 | 8 comunes + 5 de Moda |
| Glamour | Sin límite fijo | 8 comunes + 5 de Moda + 5 de Glamour |

Los valores pueden cambiar desde la administración de planes. Consultar los
datos actuales de la base antes de usar esta tabla como configuración vigente.
