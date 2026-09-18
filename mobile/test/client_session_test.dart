import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:vestidor_virtual_mobile/services/api_client.dart';
import 'package:vestidor_virtual_mobile/services/client_repository.dart';
import 'package:vestidor_virtual_mobile/services/client_session.dart';
import 'support.dart';

void main() {
  late ApiClient api;
  late MemorySessionStore store;
  late ClientSession session;
  var role = 'CLIENTE';
  var profileStatus = 200;
  var logoutFails = false;
  final calls = <String>[];
  setUp(() {
    role = 'CLIENTE';
    profileStatus = 200;
    logoutFails = false;
    calls.clear();
    store = MemorySessionStore();
    api = ApiClient(client: MockClient((request) async {
      calls.add(request.url.path);
      if (request.url.path.endsWith('/login')) {
        return http.Response(
            jsonEncode({'access_token': jwt(role: role), 'rol': role}), 200);
      }
      if (request.url.path.endsWith('/profile')) {
        return http.Response('{}', profileStatus);
      }
      if (logoutFails) throw http.ClientException('offline');
      return http.Response('{}', 200);
    }));
    session = ClientSession(ClientRepository(api), store);
  });
  tearDown(() {
    session.dispose();
    api.dispose();
  });
  test('persists token and server only, without credentials', () async {
    await session.login('http://localhost:8000/', 'cliente@test.com', 'secret');
    final saved = jsonDecode(store.value!) as Map;
    expect(saved.keys.toSet(), {'token', 'server'});
    expect(saved['server'], 'http://localhost:8000');
    expect(session.signedIn, isTrue);
  });
  test('restores session and verifies it with the current backend', () async {
    store.value =
        jsonEncode({'token': jwt(), 'server': 'http://localhost:8000'});
    await session.restore();
    expect(session.ready, isTrue);
    expect(session.signedIn, isTrue);
    expect(calls, ['/api/users/profile']);
  });
  test('expired stored token is cleared without a protected request', () async {
    store.value = jsonEncode(
        {'token': jwt(expires: 1), 'server': 'http://localhost:8000'});
    await session.restore();
    expect(store.value, isNull);
    expect(session.signedIn, isFalse);
    expect(calls, isEmpty);
  });
  test('malformed stored session keeps login usable', () async {
    store.value = 'not-json';
    await session.restore();
    expect(session.ready, isTrue);
    expect(session.signedIn, isFalse);
    expect(store.value, isNull);
  });
  test('401 revokes in-memory and persisted session', () async {
    await session.login('http://localhost:8000', 'c@test.com', 'secret');
    profileStatus = 401;
    await expectLater(
        api.request('GET', '/api/users/profile'), throwsA(isA<ApiException>()));
    expect(session.signedIn, isFalse);
    expect(store.value, isNull);
  });
  test('revoked token on restore returns to login', () async {
    store.value =
        jsonEncode({'token': jwt(), 'server': 'http://localhost:8000'});
    profileStatus = 401;
    await session.restore();
    expect(session.signedIn, isFalse);
    expect(store.value, isNull);
  });
  test('non-client login is revoked and never stored', () async {
    role = 'ADMINISTRADOR';
    await expectLater(
        session.login('http://localhost:8000', 'a@test.com', 'secret'),
        throwsA(isA<ApiException>()));
    expect(calls, contains('/api/auth/logout'));
    expect(store.value, isNull);
    expect(api.token, isNull);
  });
  test('logout clears session even when offline', () async {
    await session.login('http://localhost:8000', 'c@test.com', 'secret');
    logoutFails = true;
    await expectLater(session.logout(), throwsA(isA<ApiException>()));
    expect(api.token, isNull);
    expect(store.value, isNull);
  });
  test('storage failure revokes login instead of pretending persistence',
      () async {
    store.failWrite = true;
    await expectLater(
        session.login('http://localhost:8000', 'c@test.com', 'secret'),
        throwsA(isA<ApiException>()));
    expect(api.token, isNull);
    expect(calls, contains('/api/auth/logout'));
  });
  test('rejects unsafe or malformed server values', () {
    for (final url in [
      'invalid',
      'file:///tmp',
      'http://user:secret@localhost',
      'https://host?token=a'
    ]) {
      expect(() => ClientSession.validateServer(url),
          throwsA(isA<ApiException>()));
    }
  });
}
