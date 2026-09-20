import 'dart:convert';

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
    final result =
        await api.request('POST', '/api/cart/items', {'cantidad': 2});
    expect(result['total'], '12.00');
    api.dispose();
  });
  test('Client preserves errors needed for payment retry', () async {
    final api = ApiClient(
        client: MockClient(
            (request) async => http.Response('{"detail":"Not found"}', 404)));
    await expectLater(api.request('GET', '/api/payments/order/1'),
        throwsA(isA<ApiException>().having((e) => e.status, 'status', 404)));
    api.dispose();
  });

  test('non-JSON gateway error preserves HTTP status', () async {
    final api = ApiClient(
        client: MockClient(
            (r) async => http.Response('<html>Unavailable</html>', 503)));
    await expectLater(api.request('GET', '/api/cart'),
        throwsA(isA<ApiException>().having((e) => e.status, 'status', 503)));
    api.dispose();
  });
  test('timeout covers response completion and returns a usable message',
      () async {
    final api = ApiClient(
        timeout: const Duration(milliseconds: 1),
        client: MockClient((r) async {
          await Future<void>.delayed(const Duration(milliseconds: 10));
          return http.Response('{}', 200);
        }));
    await expectLater(api.request('GET', '/api/cart'),
        throwsA(isA<ApiException>().having((e) => e.status, 'status', 0)));
    api.dispose();
  });
  test('invalid JSON success is reported as protocol error', () async {
    final api = ApiClient(
        client: MockClient((r) async => http.Response('not-json', 200)));
    await expectLater(
        api.request('GET', '/api/cart'), throwsA(isA<ApiException>()));
    api.dispose();
  });

  test('multipart try-on request sends the private photo and bearer token',
      () async {
    final api = ApiClient(client: MockClient((request) async {
      expect(request.url.path, '/api/experience/virtual-try-on');
      expect(request.headers['Authorization'], 'Bearer sample');
      expect(request.headers['content-type'], contains('multipart/form-data'));
      expect(utf8.decode(request.bodyBytes), contains('name="product_id"'));
      expect(utf8.decode(request.bodyBytes), contains('name="photo"'));
      expect(utf8.decode(request.bodyBytes), contains('image/png'));
      return http.Response('{"image_base64":"result"}', 200);
    }));
    api.token = 'sample';
    final result = await api.multipart(
        '/api/experience/virtual-try-on',
        {'product_id': '9', 'variant_id': '3'},
        [1, 2, 3],
        'selfie.png',
        'image/png');
    expect(result, {'image_base64': 'result'});
    api.dispose();
  });

  test('multipart 401 expires the current session', () async {
    final api = ApiClient(client: MockClient(
        (request) async => http.Response('{"detail":"Unauthorized"}', 401)));
    api.token = 'sample';
    var expired = false;
    api.onUnauthorized = () async => expired = true;
    await expectLater(
        api.multipart('/api/experience/virtual-try-on', const {}, [1],
            'selfie.jpg', 'image/jpeg'),
        throwsA(isA<ApiException>().having((e) => e.status, 'status', 401)));
    expect(expired, isTrue);
    api.dispose();
  });
}
