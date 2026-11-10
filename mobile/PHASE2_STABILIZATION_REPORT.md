# FashionStore Mobile — estabilización fase 2

## Diagnóstico inicial: seis fallos

Capturados al ejecutar la suite completa antes de aplicar las correcciones.

### 1. `restored tenant reads its outbox then loads and caches catalog`

**Error completo:**

```text
The following TimeoutException was thrown while running async test code:
restore() stopped before the catalog request. Outbox reads: [org:1:7]; sync metadata reads: [org:1];
catalog saves: []
```

**Stack trace:**

```text
#0      main.<anonymous closure>.<anonymous closure>.<anonymous closure> (file:///D:/apuntes/Vestidor%20Virtual%20SI2/mobile/test/client_home_restore_catalog_test.dart:137:28)
<asynchronous suspension>
<asynchronous suspension>
(elided 7 frames from dart:async and package:stack_trace)
```

El mismo caso registró además esta aserción:

```text
Expected: contains all of ['/api/users/profile', '/api/catalog/products']
  Actual: MappedListIterable<Request, String>:['/api/users/profile', '/api/health']
   Which: has no match for '/api/catalog/products' at index 1
```

```text
#4      main.<anonymous closure> (file:///D:/apuntes/Vestidor%20Virtual%20SI2/mobile/test/client_home_restore_catalog_test.dart:147:5)
<asynchronous suspension>
#5      testWidgets.<anonymous closure>.<anonymous closure> (package:flutter_test/src/widget_tester.dart:192:15)
<asynchronous suspension>
#6      TestWidgetsFlutterBinding._runTestBody (package:flutter_test/src/binding.dart:1953:5)
<asynchronous suspension>
<asynchronous suspension>
(elided one frame from package:stack_trace)
```

**Causa raíz:** restauración, sincronización de conectividad y fake async del widget test competían; el test también ejercitaba almacenamiento SQLite dentro del fake async.

**Archivos/corrección:** `mobile/lib/features/client_app.dart`, `mobile/test/client_home_restore_catalog_test.dart`, `mobile/test/support.dart`. Se ordenó la restauración/outbox antes de cargar catálogo, se evitó la sonda de red con sesión de invitado y se inyectaron stores de memoria en el test. SQLite queda cubierto por prueba de servicio real.

### 2. `public catalog requires and changes an explicit store slug`

**Error completo:**

```text
The following assertion was thrown running a test:
pumpAndSettle timed out
```

**Stack trace:**

```text
#0      WidgetTester.pumpAndSettle.<anonymous closure> (package:flutter_test/src/widget_tester.dart:717:11)
<asynchronous suspension>
#1      TestAsyncUtils.guard.<anonymous closure> (package:flutter_test/src/test_async_utils.dart:130:27)
<asynchronous suspension>
#2      tapText (file:///D:/apuntes/Vestidor%20Virtual%20SI2/mobile/test/widget_test.dart:70:65)
<asynchronous suspension>
#3      main.<anonymous closure> (file:///D:/apuntes/Vestidor%20SI2/mobile/test/widget_test.dart:120:5)
<asynchronous suspension>
#4      testWidgets.<anonymous closure>.<anonymous closure> (package:flutter_test/src/widget_tester.dart:192:15)
<asynchronous suspension>
#5      TestWidgetsFlutterBinding._runTestBody (package:flutter_test/src/binding.dart:1953:5)
<asynchronous suspension>
<asynchronous suspension>
(elided one frame from package:stack_trace)
```

**Causa raíz:** `pumpAndSettle` esperaba que terminara el indicador de carga indeterminado durante una operación async.

**Archivos/corrección:** `mobile/test/widget_test.dart`; el helper ahora bombea y cede al event loop real para operaciones async, y reserva `pumpAndSettle` para transiciones finitas.

### 3. `login persists session and shows API catalog`

**Error completo:**

```text
The following assertion was thrown running a test:
pumpAndSettle timed out
```

**Stack trace:**

```text
#0      WidgetTester.pumpAndSettle.<anonymous closure> (package:flutter_test/src/widget_tester.dart:717:11)
<asynchronous suspension>
#1      TestAsyncUtils.guard.<anonymous closure> (package:flutter_test/src/test_async_utils.dart:130:27)
<asynchronous suspension>
#2      tapText (file:///D:/apuntes/Vestidor%20Virtual%20SI2/mobile/test/widget_test.dart:70:65)
<asynchronous suspension>
#3      main.<anonymous closure> (file:///D:/apuntes/Vestidor%20Virtual%20SI2/mobile/test/widget_test.dart:134:5)
<asynchronous suspension>
#4      testWidgets.<anonymous closure>.<anonymous closure> (package:flutter_test/src/widget_tester.dart:192:15)
<asynchronous suspension>
#5      TestWidgetsFlutterBinding._runTestBody (package:flutter_test/src/binding.dart:1953:5)
<asynchronous suspension>
<asynchronous suspension>
(elided one frame from dart:async and package:stack_trace)
```

**Causa raíz:** el mismo helper bloqueaba el avance del login/carga; además faltaba simular secure storage y el id de usuario esperado por la sesión.

**Archivos/corrección:** `mobile/test/widget_test.dart`, `mobile/test/support.dart`; plugin seguro simulado, JWT de fixture con `id_usuario`, stores en memoria y helper async corregido.

### 4. `catalog, variant, cart, checkout and demo payment complete`

**Error completo:**

```text
The following StateError was thrown running a test:
Bad state: No element
```

**Stack trace:**

```text
#0      Iterable.last (dart:core/iterable.dart:679:7)
#1      _LastFinderMixin.filter (package:flutter_test/src/finders.dart:1410:28)
#3      Iterable.isEmpty (dart:core/iterable.dart:560:33)
#4      tapText (file:///D:/apuntes/Vestidor%20Virtual%20SI2/mobile/test/widget_test.dart:69:25)
#5      main.<anonymous closure> (file:///D:/apuntes/Vestidor%20Virtual%20SI2/mobile/test/widget_test.dart:140:11)
<asynchronous suspension>
#6      testWidgets.<anonymous closure>.<anonymous closure> (package:flutter_test/src/widget_tester.dart:192:15)
<asynchronous suspension>
#7      TestWidgetsFlutterBinding._runTestBody (package:flutter_test/src/binding.dart:1953:5)
<asynchronous suspension>
<asynchronous suspension>
(elided 2 frames from dart:async-patch and package:stack_trace)
```

**Causa raíz:** el finder solicitado no estaba en el árbol porque la pantalla no había terminado su carga async; el helper usaba `last` sin tolerar el estado de carga.

**Archivos/corrección:** `mobile/test/widget_test.dart` ahora espera carga async correctamente. Se ejecuta con `--dart-define=PAYMENT_DEMO=true` y FixtureApi, sin compra real.

### 5. `profile reads and saves data then logs out`

**Error completo:**

```text
The following assertion was thrown running a test:
pumpAndSettle timed out
```

**Stack trace:**

```text
#0      WidgetTester.pumpAndSettle.<anonymous closure> (package:flutter_test/src/widget_tester.dart:717:11)
<asynchronous suspension>
#1      TestAsyncUtils.guard.<anonymous closure> (package:flutter_test/src/test_async_utils.dart:130:27)
<asynchronous suspension>
#2      main.<anonymous closure> (file:///D:/apuntes/Vestidor%20Virtual%20SI2/mobile/test/widget_test.dart:161:58)
<asynchronous suspension>
#3      testWidgets.<anonymous closure>.<anonymous closure> (package:flutter_test/src/widget_tester.dart:192:15)
<asynchronous suspension>
#4      TestWidgetsFlutterBinding._runTestBody (package:flutter_test/src/binding.dart:1953:5)
<asynchronous suspension>
<asynchronous suspension>
(elided one frame from package:stack_trace)
```

**Causa raíz:** `pumpAndSettle` se usaba durante carga indeterminada del perfil.

**Archivos/corrección:** `mobile/test/widget_test.dart`; se reemplazó por bombeo async determinista. La cobertura de sesión existente se conservó.

### 6. `opens the photographic fitting flow for the selected variant`

**Error completo:**

```text
The following assertion was thrown running a test:
pumpAndSettle timed out
```

**Stack trace:**

```text
#0      WidgetTester.pumpAndSettle.<anonymous closure> (package:flutter_test/src/widget_tester.dart:717:11)
<asynchronous suspension>
#1      TestAsyncUtils.guard.<anonymous closure> (package:flutter_test/src/test_async_utils.dart:130:27)
<asynchronous suspension>
#2      destination (file:///D:/apuntes/Vestidor%20Virtual%20SI2/mobile/test/widget_test.dart:74:63)
<asynchronous suspension>
#3      main.<anonymous closure> (file:///D:/apuntes/Vestidor%20Virtual%20SI2/mobile/test/widget_test.dart:170:5)
<asynchronous suspension>
#4      testWidgets.<anonymous closure>.<anonymous closure> (package:flutter_test/src/widget_tester.dart:192:15)
<asynchronous suspension>
#5      TestWidgetsFlutterBinding._runTestBody (package:flutter_test/src/binding.dart:1953:5)
<asynchronous suspension>
<asynchronous suspension>
(elided one frame from dart:async and package:stack_trace)
```

**Causa raíz:** helper de navegación esperaba settle mientras el destino iniciaba una operación async con progreso indeterminado.

**Archivos/corrección:** `mobile/test/widget_test.dart`; navegación bombea la ruta finita y deja que la carga async complete mediante el helper corregido.

## Resultado de validación

- Suite completa Flutter: **73 tests pasan**, cero fallos, ejecutada con `--dart-define=PAYMENT_DEMO=true`.
- Los seis tests iniciales se ejecutaron individualmente y pasaron.
- Carrito: pruebas de añadir offline y reconectar conservando línea local, reconciliación tras POST aceptado/GET perdido sin duplicar, modificación y eliminación de unidades.
- Persistencia: prueba SQLite verifica línea y estado `pending_offline` tras cerrar y reabrir el store.
- `dart analyze`: exit code 0; cero errores/advertencias, 34 sugerencias informativas de llaves en `if`.
- Render: `GET https://vestidor-virtual-backend.onrender.com/api/health` devolvió HTTP 404. La comprobación remota no está aprobada; no se enviaron mutaciones ni compras.
- APK Release: generado y sobrescrito solamente `mobile/build/app/outputs/flutter-apk/app-release.apk` (65,347,124 bytes).

Las pruebas de backend con inventario/precios reales requieren un ambiente de prueba Render y credenciales de test. No se usó producción para comprar.
