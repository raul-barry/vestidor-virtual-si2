import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'dart:convert';

abstract class SessionStore {
  Future<String?> read();
  Future<void> write(String value);
  Future<void> clear();
}

class SecureSessionStore implements SessionStore {
  const SecureSessionStore();
  static const _storage = FlutterSecureStorage();
  static const _key = 'vestidor_client_session';
  @override
  Future<String?> read() => _storage.read(key: _key);
  @override
  Future<void> write(String value) => _storage.write(key: _key, value: value);
  @override
  Future<void> clear() => _storage.delete(key: _key);
}

abstract class DeviceSyncCredentialStore {
  Future<Map<String, dynamic>> readAll();
  Future<void> writeFor(int userId, int organizationId, Map<String, dynamic> credential);
  Future<void> clear();
}

class SecureDeviceSyncCredentialStore implements DeviceSyncCredentialStore {
  static const _storage = FlutterSecureStorage();
  static const _key = 'fashion_store_device_sync_credential';
  @override
  Future<Map<String, dynamic>> readAll() async {
    try {
      final value = await _storage.read(key: _key);
      if (value == null) return {};
      return Map<String, dynamic>.from(jsonDecode(value) as Map);
    } catch (_) { return {}; }
  }
  @override
  Future<void> writeFor(int userId, int organizationId, Map<String, dynamic> credential) async {
    final values = await readAll();
    values['$organizationId:$userId'] = credential;
    await _storage.write(key: _key, value: jsonEncode(values));
  }
  @override
  Future<void> clear() => _storage.delete(key: _key);
}
