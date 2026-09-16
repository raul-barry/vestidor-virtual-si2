import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:vestidor_virtual_mobile/services/api_client.dart';

void main() {
  test('Client sends bearer token and decodes server response', () async {
    final api = ApiClient(client: MockClient((request) async {
      expect(request.url.path, '/api/cart/items');
      expect(request.headers['Authorization'], 'Bearer sample');
      expect(request.body, '{"cantidad":2}');
      return http.Response('{"total":"12.00"}', 200);
    }));
    api.token = 'sample';
    final result = await api.request('POST', '/api/cart/items', {'cantidad': 2});
    expect(result['total'], '12.00');
    api.dispose();
  });
  test('Client preserves errors needed for payment retry', () async {
    final api = ApiClient(client: MockClient((request) async => http.Response('{"detail":"Not found"}', 404)));
    await expectLater(api.request('GET', '/api/payments/order/1'), throwsA(isA<ApiException>().having((e) => e.status, 'status', 404)));
    api.dispose();
  });
}
