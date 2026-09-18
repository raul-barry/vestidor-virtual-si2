import 'dart:convert';
import 'package:vestidor_virtual_mobile/services/session_store.dart';

class MemorySessionStore implements SessionStore {
  String? value;
  bool failWrite = false;
  @override
  Future<String?> read() async => value;
  @override
  Future<void> write(String value) async {
    if (failWrite) throw StateError('Storage unavailable');
    this.value = value;
  }

  @override
  Future<void> clear() async {
    value = null;
  }
}

String jwt({String role = 'CLIENTE', int? expires}) =>
    'header.${base64Url.encode(utf8.encode(jsonEncode({
              'rol': role,
              'exp': expires ??
                  DateTime.now().millisecondsSinceEpoch ~/ 1000 + 3600,
            }))).replaceAll('=', '')}.signature';
