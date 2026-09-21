# Validación de la refactorización

Fecha: 17 de septiembre de 2026.

## Resultados finales

| Comprobación | Resultado |
| --- | --- |
| Build de producción Angular | Correcto |
| Suite completa en Chrome Headless | 97/97 pruebas correctas |
| Comprobación visual por rol y viewport | 24/24 correctas |
| Desbordamiento horizontal del documento en esos casos | Ninguno |
| Excepciones JavaScript en comprobación visual | Ninguna |
| git diff --check | Correcto |
| Servicios, modelos y guards | Sin modificaciones |
| Implementaciones de negocio de 19 componentes editados | Idénticas a HEAD; solo cambió su presentación |

Build final: paquete inicial de 567,11 kB. Permanece el aviso del presupuesto recomendado de 500 kB; no supera el límite de error de 1 MB. No se aumentaron los presupuestos para ocultarlo.

## Pruebas de navegación
AppComponent se verifica con visitante, CLIENTE, ADMINISTRADOR, ENCARGADO, ENCARGADO_SUCURSAL y CAJERO. Se comprueba la presencia de una sola navbar, ausencia de sidebar para clientes, módulos del cajero, apertura/cierre del menú y destinos por rol. Cada enlace del mapa de navegación se contrasta con las rutas existentes. Los tests previos de guards y login continúan pasando.

## Comprobación visual
scripts/visual-smoke.cjs sirve el build de producción en localhost y abre un perfil aislado de Chrome. Intercepta la API con fixtures y bloquea solicitudes externas: NO prueba permisos del servidor ni operaciones reales de compra, stock o pago.

Casos: visitante y cliente en catálogo; administrador en productos; ambos nombres de encargado en inventario; cajero en venta presencial. Cada uno se evalúa a 1440, 768, 390 y 320 px. Se comprueban el rol visible, apertura del menú móvil, anchura del documento y errores de ejecución. Se guardan 24 capturas y report.json en artifacts/visual/ (archivos generados ignorados por Git).

Se inspeccionaron además las capturas de cliente en escritorio/móvil y administrador en escritorio/móvil. Se corrigieron bordes de campos Material producidos por Tailwind, el placeholder externo del producto y el contraste de la acción principal.

## Incidencias corregidas
- Build previo imposible por texto accidental antepuesto al JSON de tsconfig.json. Se retiró solo el prefijo.
- Chrome Headless fallaba al iniciar GPU; test:ci usa un launcher de software para este entorno.
- Dos tests existentes de ProductDetailComponent no proporcionaban ApiService/AuthService/router. Se completaron los doubles del montaje, sin modificar el comportamiento del componente.

## Reproducir en PowerShell

```powershell
cd frontend-web
npm.cmd run build
$env:CHROME_BIN = 'C:/Program Files/Google/Chrome/Application/chrome.exe'
npm.cmd run test:ci
npm.cmd run test:visual
```

La suite visual necesita un build previo. CHROME_BIN puede apuntar a otra instalación de Chrome. Los logs locales se encuentran en build-final.log, test-final.log y visual-smoke.log.

## Alcance pendiente por restricciones del encargo
No se cambió autorización ni backend. Los menús de personal están separados por rol, pero la visibilidad no restringe rutas que los guards ya permitían. La gestión de pedidos de sucursal para encargados no existe en la API actual: /api/admin/orders es exclusiva de administradores y /api/orders es del cliente. Su resolución requeriría un cambio funcional fuera de este alcance. Véase frontend-audit.md.
