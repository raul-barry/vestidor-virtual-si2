import 'package:http/http.dart' as http;

import '../core/config/api_config.dart';

class ApiClient {
  ApiClient({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;

  Uri resolve(String path) => Uri.parse('${ApiConfig.baseUrl}$path');

  void dispose() => _client.close();
}
