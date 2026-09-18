import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'api_client.dart';
import 'client_repository.dart';
import 'session_store.dart';

class ClientSession extends ChangeNotifier {
  ClientSession(this.repository, this.store) {
    repository.api.onUnauthorized = expire;
  }
  final ClientRepository repository;
  final SessionStore store;
  Timer? _expiry;
  bool ready = false;
  String? notice;
  bool get signedIn => repository.api.token != null;

  static Map<String, dynamic>? claims(String token) {
    try {
      final parts = token.split('.');
      if (parts.length != 3) return null;
      return Map<String, dynamic>.from(jsonDecode(
          utf8.decode(base64Url.decode(base64Url.normalize(parts[1])))) as Map);
    } catch (_) {
      return null;
    }
  }

  static bool validClientToken(String token) {
    final data = claims(token);
    final expiry = data?['exp'];
    return data?['rol'] == 'CLIENTE' &&
        expiry is num &&
        expiry * 1000 > DateTime.now().millisecondsSinceEpoch;
  }

  static String validateServer(String value) {
    final uri = Uri.tryParse(value.trim());
    if (uri == null ||
        !['http', 'https'].contains(uri.scheme) ||
        uri.host.isEmpty ||
        uri.userInfo.isNotEmpty ||
        uri.hasQuery ||
        uri.hasFragment) {
      throw ApiException(0,
          'Dirección de API inválida. Usa http:// o https:// y un servidor.');
    }
    return value.trim().replaceFirst(RegExp(r'/+$'), '');
  }

  Future<void> restore() async {
    try {
      final saved = await store.read();
      if (saved != null) {
        final data = jsonDecode(saved) as Map;
        final token = data['token'] as String;
        if (!validClientToken(token)) {
          await store.clear();
          notice = 'La sesión venció. Inicia sesión nuevamente.';
        } else {
          repository.api.baseUrl = validateServer(data['server'] as String);
          repository.api.token = token;
          _schedule();
          try {
            await repository.profile();
          } on ApiException catch (e) {
            if (e.status != 401) notice = e.message;
          }
        }
      }
    } catch (_) {
      repository.api.token = null;
      notice =
          'No se pudo recuperar la sesión guardada. Inicia sesión nuevamente.';
      try {
        await store.clear();
      } catch (_) {/* Keep login available. */}
    } finally {
      ready = true;
      notifyListeners();
    }
  }

  Future<void> login(String server, String email, String password) async {
    repository.api.baseUrl = validateServer(server);
    final response = await repository.login(email, password);
    final token = response['access_token'] as String? ?? '';
    repository.api.token = token;
    if (response['rol'] != 'CLIENTE' || !validClientToken(token)) {
      try {
        await repository.logout();
      } catch (_) {/* Clear locally regardless. */}
      repository.api.token = null;
      throw ApiException(403,
          'Esta aplicación es para clientes. Usa la web para otros roles.');
    }
    try {
      await store.write(
          jsonEncode({'token': token, 'server': repository.api.baseUrl}));
    } catch (_) {
      try {
        await repository.logout();
      } catch (_) {/* Revoke when reachable. */}
      repository.api.token = null;
      throw ApiException(0,
          'No se pudo guardar la sesión de forma segura. Intenta nuevamente.');
    }
    notice = null;
    _schedule();
    notifyListeners();
  }

  void _schedule() {
    _expiry?.cancel();
    final exp = claims(repository.api.token!)!['exp'] as num;
    _expiry = Timer(
        Duration(
            milliseconds: (exp * 1000).toInt() -
                DateTime.now().millisecondsSinceEpoch), () {
      unawaited(expire());
    });
  }

  Future<void> expire() async {
    notice = 'La sesión venció o fue revocada. Inicia sesión nuevamente.';
    await _clear();
  }

  Future<void> logout() async {
    try {
      await repository.logout();
    } finally {
      await _clear();
    }
  }

  Future<void> _clear() async {
    _expiry?.cancel();
    repository.api.token = null;
    try {
      await store.clear();
    } catch (_) {
      notice =
          'Sesión cerrada. No se pudo limpiar el almacenamiento del dispositivo.';
    }
    notifyListeners();
  }

  @override
  void dispose() {
    _expiry?.cancel();
    repository.api.onUnauthorized = null;
    super.dispose();
  }
}
