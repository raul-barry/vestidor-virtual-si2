import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:vestidor_virtual_mobile/services/api_client.dart';
import 'package:vestidor_virtual_mobile/services/client_repository.dart';

void main() {
  test('loads loyalty snapshot from authenticated tenant endpoint', () async {
    http.Request? captured;
    final api = ApiClient(client: MockClient((request) async {
      captured = request;
      return http.Response(jsonEncode({
        'balance': 145,
        'tier': {'name': 'Bronce'},
        'movements': [],
      }), 200, headers: {'content-type': 'application/json'});
    }));
    api.baseUrl = 'https://fashion.test';
    api.token = 'test-session-token';
    final result = await ClientRepository(api).loyalty();

    expect(captured?.url.path, '/api/loyalty/me');
    expect(captured?.headers['Authorization'], 'Bearer test-session-token');
    expect(captured?.body, isEmpty);
    expect(result['balance'], 145);
    expect(result['tier']['name'], 'Bronce');
    api.dispose();
  });
}
