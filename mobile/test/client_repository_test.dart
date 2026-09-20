import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:vestidor_virtual_mobile/services/api_client.dart';
import 'package:vestidor_virtual_mobile/services/client_repository.dart';

void main() {
  test(
      'catalog uses list endpoint without filters and encodes nonempty filters',
      () async {
    final requests = <Uri>[];
    final api = ApiClient(client: MockClient((r) async {
      requests.add(r.url);
      return http.Response('[]', 200);
    }));
    final repo = ClientRepository(api);
    await repo.catalog();
    await repo
        .catalog({'nombre': 'Camisa azul', 'color': '', 'precio_max': '200'});
    expect(requests[0].path, '/api/catalog/products');
    expect(requests[1].queryParameters,
        {'nombre': 'Camisa azul', 'precio_max': '200'});
    api.dispose();
  });
  for (final state in ['PENDIENTE', 'PAGADO']) {
    test('reuses existing $state payment without duplicate creation', () async {
      final methods = <String>[];
      final api = ApiClient(client: MockClient((r) async {
        methods.add(r.method);
        return http.Response(
            jsonEncode({'id_pago': 4, 'estado': state, 'metodo_pago': 'QR'}),
            200);
      }));
      final payment = await ClientRepository(api).preparePayment(1, 'TARJETA');
      expect(payment['id_pago'], 4);
      expect(methods, ['GET']);
      api.dispose();
    });
  }
  test('creates payment after 404 with exact backend payload', () async {
    final api = ApiClient(client: MockClient((r) async {
      if (r.method == 'GET') return http.Response('{}', 404);
      expect(r.url.path, '/api/payments');
      expect(jsonDecode(r.body), {'id_pedido': 7, 'metodo_pago': 'EFECTIVO'});
      return http.Response('{"id_pago":5}', 200);
    }));
    expect(
        (await ClientRepository(api).preparePayment(7, 'EFECTIVO'))['id_pago'],
        5);
    api.dispose();
  });
  test('does not create payment after network/server failure', () async {
    final methods = <String>[];
    final api = ApiClient(client: MockClient((r) async {
      methods.add(r.method);
      return http.Response('{}', 500);
    }));
    await expectLater(ClientRepository(api).preparePayment(1, 'QR'),
        throwsA(isA<ApiException>()));
    expect(methods, ['GET']);
    api.dispose();
  });
  test('order history does not assume details in summary response', () async {
    final requests = <String>[];
    final api = ApiClient(client: MockClient((r) async {
      requests.add(r.url.path);
      return http.Response(
          r.url.path == '/api/orders'
              ? '[{"id_pedido":1,"estado":"PENDIENTE"}]'
              : '{"id_pedido":1,"detalles":[]}',
          200);
    }));
    final repo = ClientRepository(api);
    final orders = await repo.orders();
    await repo.order(orders.first['id_pedido']);
    expect(requests, ['/api/orders', '/api/orders/1']);
    api.dispose();
  });
}
