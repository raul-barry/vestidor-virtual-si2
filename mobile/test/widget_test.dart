import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:vestidor_virtual_mobile/main.dart';
import 'package:vestidor_virtual_mobile/services/api_client.dart';
import 'package:vestidor_virtual_mobile/services/client_repository.dart';
import 'support.dart';

class FixtureApi {
  final requests = <http.Request>[];
  int quantity = 0;
  String orderState = 'PENDIENTE';
  Json? payment;
  bool ordered = false;
  bool reserved = false;
  String firstName = 'Cliente';
  final product = <String, dynamic>{'id_producto': 1, 'nombre': 'Camisa Oxford', 'descripcion': 'Algodón', 'precio_base': '100.00', 'categoria': {'nombre': 'Camisas'}, 'variantes': [{'id_variante': 2, 'talla': 'M', 'color': 'Azul'}]};
  final inventory = <String, dynamic>{'id_inventario': 3, 'producto': 'Camisa Oxford', 'talla': 'M', 'color': 'Azul', 'sucursal': 'Central', 'disponible': 10};
  Json get order => {'id_pedido': 4, 'estado': orderState, 'fecha_pedido': '2026-09-17', 'total': '100.00'};
  Future<http.Response> respond(http.Request r) async {
    requests.add(r);
    final path = r.url.path;
    final body = r.body.isEmpty ? <String, dynamic>{} : jsonDecode(r.body) as Json;
    dynamic result;
    if (path.endsWith('/login')) { result = {'access_token': jwt(), 'rol': 'CLIENTE'}; }
    else if (path.endsWith('/logout')) { result = {'message': 'ok'}; }
    else if (path == '/api/users/profile') {
      if (r.method == 'PUT') firstName = body['nombres'];
      result = {'nombres': firstName, 'apellidos': 'Prueba', 'correo': 'cliente@example.com', 'telefono': '70000000'};
    } else if (path.endsWith('/variants')) { result = {...product, 'nombre_producto': 'Camisa Oxford'}; }
    else if (path == '/api/catalog/products/1/availability') { result = {'disponibilidad': [{'nombre_sucursal': 'Central', 'direccion': 'Av. 1', 'stock_disponible': 10}]}; }
    else if (path.startsWith('/api/catalog/products')) { result = [product]; }
    else if (path.startsWith('/api/cart/items')) {
      quantity = r.method == 'DELETE' ? 0 : body['cantidad']; result = {};
    } else if (path == '/api/cart') {
      result = {'total': '${quantity * 100}.00', 'items': [if (quantity > 0) {'id_detalle': 5, 'producto': 'Camisa Oxford', 'talla': 'M', 'color': 'Azul', 'precio_unitario': '100.00', 'cantidad': quantity}]};
    } else if (path == '/api/orders') {
      if (r.method == 'POST') { ordered = true; quantity = 0; result = order; }
      else { result = ordered ? [order] : []; }
    } else if (path == '/api/orders/4') {
      result = {...order, 'detalles': [{'producto': 'Camisa Oxford', 'talla': 'M', 'color': 'Azul', 'cantidad': 1, 'precio_unitario': '100.00'}]};
    } else if (path == '/api/payments/order/4') {
      if (payment == null) return http.Response('{}', 404);
      result = payment;
    } else if (path == '/api/payments') {
      payment = {'id_pago': 6, 'estado': 'PENDIENTE', 'metodo_pago': body['metodo_pago'], 'monto': '100.00'}; result = payment;
    } else if (path.endsWith('/approve')) { payment!['estado'] = 'PAGADO'; orderState = 'CONFIRMADO'; result = payment; }
    else if (path.endsWith('/reject')) { payment!['estado'] = 'FALLIDO'; result = payment; }
    else if (path == '/api/reservations/availability') { result = [inventory]; }
    else if (path == '/api/reservations') {
      if (r.method == 'POST') reserved = true;
      result = r.method == 'POST' ? {} : [if (reserved) {...inventory, 'id_reserva': 7, 'estado': 'PENDIENTE', 'cantidad': 1}];
    } else if (path == '/api/experience/fitting') {
      final garment = {'id_variante': 2, 'id_producto': 1, 'nombre': 'Camisa Oxford', 'talla': 'M', 'color': 'Azul', 'garment': 'top'};
      result = r.method == 'POST' ? garment : [garment];
    } else if (path == '/api/experience/recommendations') { result = [{'id_variante': 2, 'id_producto': 1, 'nombre': 'Camisa Oxford', 'talla': 'M', 'color': 'Azul', 'precio': '100.00', 'motivo': 'Tu estilo'}]; }
    else { result = {}; }
    return http.Response(jsonEncode(result), 200, headers: {'content-type': 'application/json; charset=utf-8'});
  }
}

Future<void> tapText(WidgetTester tester, String text) async {
  final target = find.text(text).last;
  if (target.evaluate().isEmpty) await tester.scrollUntilVisible(target, 250, scrollable: find.byType(Scrollable).first);
  await tester.ensureVisible(target); await tester.tap(target); await tester.pumpAndSettle();
}
Future<void> destination(WidgetTester tester, String name) async {
  await tester.tap(find.byTooltip('Open navigation menu')); await tester.pumpAndSettle();
  await tester.tap(find.widgetWithText(ListTile, name).last); await tester.pumpAndSettle();
}
void main() {
  late FixtureApi backend;
  late ApiClient api;
  late MemorySessionStore store;
  Future<void> start(WidgetTester tester, {bool loggedIn = false}) async {
    tester.view.physicalSize = const Size(430, 1100); tester.view.devicePixelRatio = 1;
    addTearDown(() { tester.view.resetPhysicalSize(); tester.view.resetDevicePixelRatio(); });
    backend = FixtureApi(); store = MemorySessionStore();
    if (loggedIn) store.value = jsonEncode({'token': jwt(), 'server': 'http://localhost:8000'});
    api = ApiClient(client: MockClient(backend.respond));
    await tester.pumpWidget(VestidorVirtualApp(repository: ClientRepository(api), sessionStore: store));
    await tester.pumpAndSettle();
  }
  tearDown(() => api.dispose());
  testWidgets('login form preserves registration and validates input', (tester) async {
    await start(tester);
    expect(find.text('Iniciar sesión'), findsOneWidget);
    await tapText(tester, 'Iniciar sesión');
    expect(find.text('Ingresa un correo válido y tu contraseña.'), findsOneWidget);
    expect(backend.requests, isEmpty);
    await tapText(tester, 'Crear cuenta');
    expect(find.text('Nombres'), findsOneWidget); expect(find.text('Apellidos'), findsOneWidget);
  });
  testWidgets('login persists session and shows API catalog', (tester) async {
    await start(tester);
    await tester.enterText(find.widgetWithText(TextField, 'Correo'), 'cliente@example.com');
    await tester.enterText(find.widgetWithText(TextField, 'Contraseña'), 'secret');
    await tapText(tester, 'Iniciar sesión');
    expect(store.value, isNotNull); expect(find.text('Camisa Oxford'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
  });
  testWidgets('catalog, variant, cart, checkout and demo payment complete', (tester) async {
    await start(tester, loggedIn: true);
    await tapText(tester, 'Camisa Oxford');
    await tester.tap(find.byType(DropdownButtonFormField<int>)); await tester.pumpAndSettle();
    await tester.tap(find.text('M · Azul').last); await tester.pumpAndSettle();
    await tapText(tester, 'Agregar al carrito'); expect(backend.quantity, 1);
    await tester.tap(find.byIcon(Icons.shopping_bag_outlined)); await tester.pumpAndSettle();
    await tapText(tester, 'Aumentar'); expect(backend.quantity, 2);
    await tapText(tester, 'Reducir'); expect(backend.quantity, 1);
    await tapText(tester, 'Confirmar compra');
    expect(find.text('Confirmar pedido'), findsOneWidget);
    await tapText(tester, 'Crear pedido');
    expect(find.text('Pedido #4'), findsOneWidget);
    expect(backend.requests.where((r) => r.url.path == '/api/orders' && r.method == 'POST'), hasLength(1));
    await tapText(tester, 'Pagar (demostración)'); await tapText(tester, 'Simular aprobación');
    expect(backend.orderState, 'CONFIRMADO'); expect(find.text('Estado: CONFIRMADO'), findsOneWidget);
    await tapText(tester, 'Volver a mis pedidos');
    await tapText(tester, 'Pedido #4 · CONFIRMADO');
    expect(find.text('Camisa Oxford'), findsOneWidget);
    expect(tester.takeException(), isNull); await tester.pumpWidget(const SizedBox());
  });
  testWidgets('profile reads and saves data then logs out', (tester) async {
    await start(tester, loggedIn: true);
    await tester.tap(find.byIcon(Icons.person_outline)); await tester.pumpAndSettle();
    expect(find.text('cliente@example.com'), findsOneWidget);
    await tester.enterText(find.widgetWithText(TextField, 'Nombres'), 'Actualizado');
    await tapText(tester, 'Guardar perfil'); expect(backend.firstName, 'Actualizado');
    await tapText(tester, 'Cerrar sesión'); expect(store.value, isNull);
    expect(find.text('Iniciar sesión'), findsOneWidget);
  });
  testWidgets('opens the photographic fitting flow for the selected variant', (tester) async {
    await start(tester, loggedIn: true);
    await destination(tester, 'Reservas');
    await tester.tap(find.byType(DropdownButtonFormField<int>)); await tester.pumpAndSettle();
    await tester.tap(find.text('Camisa Oxford · M · Azul · Central (10)').last); await tester.pumpAndSettle();
    await tapText(tester, 'Reservar'); expect(backend.reserved, isTrue);
    expect(find.text('Camisa Oxford · PENDIENTE'), findsOneWidget);
    await destination(tester, 'Vestidor');
    await tester.tap(find.byType(DropdownButtonFormField<int>)); await tester.pumpAndSettle();
    await tester.tap(find.text('Camisa Oxford · M · Azul').last); await tester.pumpAndSettle();
    expect(find.textContaining('cuerpo completo o torso'), findsOneWidget);
    expect(find.textContaining('Tomar fotograf'), findsOneWidget);
    expect(find.textContaining('Elegir de galer'), findsOneWidget);
    expect(tester.takeException(), isNull); await tester.pumpWidget(const SizedBox());
  });
}
