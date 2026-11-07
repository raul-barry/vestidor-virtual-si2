import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:vestidor_virtual_mobile/features/client_app.dart';
import 'package:vestidor_virtual_mobile/services/api_client.dart';
import 'package:vestidor_virtual_mobile/services/catalog_offline_store.dart';
import 'package:vestidor_virtual_mobile/services/client_repository.dart';
import 'package:vestidor_virtual_mobile/services/session_store.dart';

class _MemorySessionStore implements SessionStore {
  _MemorySessionStore(this.value);

  final String value;

  @override
  Future<void> clear() async {}

  @override
  Future<String?> read() async => value;

  @override
  Future<void> write(String value) async {}
}

class _TracingCatalogStore extends CatalogOfflineStore {
  _TracingCatalogStore()
      : super(factory: databaseFactoryFfi, databasePath: ':memory:');

  final outboxReadScopes = <String>[];
  final syncReadScopes = <String>[];
  final savedCatalogScopes = <String>[];
  final catalogSaved = Completer<void>();

  @override
  Future<List<Map<String, dynamic>>> listOutbox(String scope,
      {int? ownerUserId}) {
    outboxReadScopes.add('$scope:$ownerUserId');
    return super.listOutbox(scope, ownerUserId: ownerUserId);
  }

  @override
  Future<int?> getLastSync(String scope) {
    syncReadScopes.add(scope);
    return super.getLastSync(scope);
  }

  @override
  Future<void> save(String scope, List<Map<String, dynamic>> products) async {
    await super.save(scope, products);
    savedCatalogScopes.add(scope);
    if (!catalogSaved.isCompleted) catalogSaved.complete();
  }
}

String _clientJwt() {
  final payload = base64Url.encode(utf8.encode(jsonEncode({
        'rol': 'CLIENTE',
        'id_organizacion': 1,
        'id_usuario': 7,
        'exp': DateTime.now().millisecondsSinceEpoch ~/ 1000 + 3600,
      }))).replaceAll('=', '');
  return 'header.$payload.signature';
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(() {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
    final messenger =
        TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;
    messenger.setMockMethodCallHandler(
      const MethodChannel('dev.fluttercommunity.plus/connectivity'),
      (call) async => ['wifi'],
    );
    messenger.setMockStreamHandler(
      const EventChannel('dev.fluttercommunity.plus/connectivity_status'),
      MockStreamHandler.inline(
        onListen: (arguments, events) => events.success(['wifi']),
      ),
    );
    messenger.setMockMethodCallHandler(
      const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),
      (call) async => null,
    );
  });

  testWidgets('restored tenant reads its outbox then loads and caches catalog',
      (tester) async {
    SharedPreferences.setMockInitialValues({});
    final catalogStore = _TracingCatalogStore();
    final requests = <http.Request>[];
    final api = ApiClient(client: MockClient((request) async {
      requests.add(request);
      if (request.url.path == '/api/users/profile') {
        return http.Response('{}', 200);
      }
      if (request.url.path == '/api/catalog/products') {
        return http.Response(
          jsonEncode([
            {
              'id_producto': 1,
              'nombre': 'Camisa de prueba',
              'precio_base': '100.00',
              'categoria': {'id_categoria': 2, 'nombre': 'Camisas'},
              'variantes': [],
            }
          ]),
          200,
        );
      }
      return http.Response('{}', 200);
    }));
    final sessionStore = _MemorySessionStore(jsonEncode({
      'token': _clientJwt(),
      'server': 'http://localhost:8000',
    }));

    await tester.pumpWidget(MaterialApp(
      home: ClientHome(
        repository: ClientRepository(api),
        sessionStore: sessionStore,
        catalogStore: catalogStore,
      ),
    ));
    await tester.pumpAndSettle();
    await tester.runAsync(() => catalogStore.catalogSaved.future.timeout(
          const Duration(seconds: 10),
          onTimeout: () => throw TimeoutException(
              'restore() stopped before the catalog request. '
              'Outbox reads: ${catalogStore.outboxReadScopes}; '
              'sync metadata reads: ${catalogStore.syncReadScopes}; '
              'catalog saves: ${catalogStore.savedCatalogScopes}'),
        ));
    await tester.pumpAndSettle();

    expect(api.token, isNotNull);
    expect(ClientJwtOrganization.read(api.token!), 1);
    expect(requests.map((request) => request.url.path),
        containsAll(['/api/users/profile', '/api/catalog/products']));
    expect(
      requests.singleWhere(
          (request) => request.url.path == '/api/catalog/products').url.query,
      isEmpty,
      reason: 'Authenticated catalog requests are scoped by the JWT tenant.',
    );
    expect(catalogStore.outboxReadScopes, contains('org:1:7'));
    expect(catalogStore.syncReadScopes, contains('org:1'));
    expect(catalogStore.savedCatalogScopes, contains('org:1'));
    expect(catalogStore.savedCatalogScopes, isNot(contains('org:2')));
    expect(find.text('Camisa de prueba'), findsOneWidget);

    await tester.pumpWidget(const SizedBox.shrink());
    api.dispose();
  });
}

class ClientJwtOrganization {
  static int? read(String token) {
    final claims = jsonDecode(utf8.decode(
        base64Url.decode(base64Url.normalize(token.split('.')[1])))) as Map;
    return (claims['id_organizacion'] as num?)?.toInt();
  }
}
