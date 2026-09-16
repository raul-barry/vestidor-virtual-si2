import 'package:http/http.dart' as http;
import 'dart:convert';

import '../core/config/api_config.dart';

class ApiClient {
  ApiClient({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;
  String baseUrl = ApiConfig.baseUrl;
  String? token;

  Uri resolve(String path) => Uri.parse('${baseUrl.replaceFirst(RegExp(r'/+$'), '')}$path');

  Future<dynamic> request(String method, String path, [Object? body]) async {
    final request = http.Request(method, resolve(path));
    request.headers['Content-Type'] = 'application/json';
    if (token != null) request.headers['Authorization'] = 'Bearer $token';
    if (body != null) request.body = jsonEncode(body);
    final response = await http.Response.fromStream(await _client.send(request).timeout(const Duration(seconds: 20)));
    final data = response.body.isEmpty ? null : jsonDecode(response.body);
    if (response.statusCode >= 400) {
      final detail = data is Map ? data['message'] ?? data['detail'] : null;
      throw ApiException(response.statusCode, detail is String ? detail : 'No se pudo completar la operación (${response.statusCode})');
    }
    return data;
  }

  void dispose() => _client.close();
}

class ApiException implements Exception {
  ApiException(this.status, this.message);
  final int status;
  final String message;
  @override
  String toString() => message;
}
