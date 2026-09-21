import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';
import '../core/config/api_config.dart';

class ApiClient {
  ApiClient({http.Client? client, this.timeout = const Duration(seconds: 20)})
      : _client = client ?? http.Client();
  final http.Client _client;
  final Duration timeout;
  String baseUrl = ApiConfig.baseUrl;
  String? token;
  Future<void> Function()? onUnauthorized;

  Uri resolve(String path) =>
      Uri.parse('${baseUrl.replaceFirst(RegExp(r'/+$'), '')}$path');

  Future<dynamic> request(String method, String path, [Object? body]) async {
    final sentToken = token;
    try {
      final request = http.Request(method, resolve(path));
      request.headers['Content-Type'] = 'application/json';
      if (sentToken != null) {
        request.headers['Authorization'] = 'Bearer $sentToken';
      }
      if (body != null) request.body = jsonEncode(body);
      final response = await _client
          .send(request)
          .then(http.Response.fromStream)
          .timeout(timeout);
      dynamic data;
      try {
        data = response.bodyBytes.isEmpty
            ? null
            : jsonDecode(utf8.decode(response.bodyBytes));
      } on FormatException {/* Gateways can return HTML instead of JSON. */}
      if (response.statusCode == 401 &&
          sentToken != null &&
          sentToken == token) {
        await onUnauthorized?.call();
      }
      if (response.statusCode >= 400) {
        final detail = data is Map ? data['message'] ?? data['detail'] : null;
        final message = detail is String
            ? detail
            : detail is List
                ? detail
                    .map((e) => e is Map ? e['msg'] ?? 'Dato inválido' : '$e')
                    .join('\n')
                : 'No se pudo completar la operación (${response.statusCode}).';
        throw ApiException(response.statusCode, message);
      }
      if (data == null && response.bodyBytes.isNotEmpty) {
        throw ApiException(0, 'El servidor no devolvió una respuesta válida.');
      }
      return data;
    } on TimeoutException {
      throw ApiException(0,
          'El servidor tardó demasiado. Comprueba la conexión. Si confirmabas una compra, revisa tus pedidos antes de repetirla.');
    } on http.ClientException {
      throw ApiException(0,
          'No se pudo conectar con el servidor. Comprueba la red y la dirección de la API.');
    }
  }

  Future<dynamic> multipart(String path, Map<String, String> fields,
      List<int> bytes, String filename, String mimeType) async {
    final sentToken = token;
    final request = http.MultipartRequest('POST', resolve(path));
    if (sentToken != null) request.headers['Authorization'] = 'Bearer $sentToken';
    request.fields.addAll(fields);
    request.files.add(http.MultipartFile.fromBytes('photo', bytes,
        filename: filename, contentType: MediaType.parse(mimeType)));
    final response = await http.Response.fromStream(
        await _client.send(request).timeout(timeout));
    dynamic data;
    try { data = jsonDecode(utf8.decode(response.bodyBytes)); } on FormatException {}
    if (response.statusCode == 401 &&
        sentToken != null &&
        sentToken == token) {
      await onUnauthorized?.call();
    }
    if (response.statusCode >= 400) {
      final detail = data is Map ? data['detail'] ?? data['message'] : null;
      throw ApiException(response.statusCode, detail is String ? detail : 'No se pudo generar la prueba virtual.');
    }
    if (data is! Map) throw ApiException(0, 'El servidor no devolvió una prueba válida.');
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
