import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:vestidor_virtual_mobile/services/catalog_offline_store.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  test('default outbox read used during session restore works with SQLite FFI', () async {
    final store = CatalogOfflineStore();
    addTearDown(store.close);

    expect(await store.getLastSync('org:1'), isNull);
  });

  test('stores catalog updates and categories separately for each tenant', () async {
    final store = CatalogOfflineStore(factory: databaseFactoryFfi);
    addTearDown(store.close);
    final first = <Map<String, dynamic>>[
      {'id_producto': 1, 'nombre': 'Camisa', 'categoria': {'id_categoria': 4, 'nombre': 'Camisas'}, 'variantes': []}
    ];
    await store.save('slug:tienda-a', first);
    await store.save('org:20', [
      {'id_producto': 2, 'nombre': 'Vestido', 'categoria': {'id_categoria': 8, 'nombre': 'Vestidos'}, 'variantes': []}
    ]);

    expect((await store.read('slug:tienda-a')).products.single['nombre'], 'Camisa');
    expect((await store.read('org:20')).products.single['nombre'], 'Vestido');
    expect((await store.read('slug:tienda-b')).products, isEmpty);
    final db = await store.database;
    final categoriesA = await db.query('catalog_categories', where: 'scope = ?', whereArgs: ['slug:tienda-a']);
    final categoriesB = await db.query('catalog_categories', where: 'scope = ?', whereArgs: ['org:20']);
    expect(categoriesA.single['name'], 'Camisas');
    expect(categoriesB.single['name'], 'Vestidos');

    await store.save('slug:tienda-a', [
      {'id_producto': 3, 'nombre': 'Camisa actualizada', 'categoria': {'id_categoria': 4, 'nombre': 'Camisas'}, 'variantes': []}
    ]);
    final updated = await store.read('slug:tienda-a');
    expect(updated.products.single['nombre'], 'Camisa actualizada');
    expect(updated.syncedAt, isNotNull);
  });

  test('persists outbox work per tenant, claims once, and rejects credentials', () async {
    final store = CatalogOfflineStore(factory: databaseFactoryFfi);
    addTearDown(store.close);
    final id = await store.enqueueOperation(
      tenantScope: 'org:11', operationType: 'demo.noop',
      payload: {'reference': 42}, clientId: 'device-test',
    );
    await store.enqueueOperation(
      tenantScope: 'org:12', operationType: 'demo.noop',
      payload: {'reference': 84}, clientId: 'device-test',
    );

    final parallelClaims = await Future.wait([
      store.claimPending('org:11'),
      store.claimPending('org:11'),
    ]);
    expect(parallelClaims.expand((claim) => claim).map((row) => row['operation_uuid']), [id]);
    expect((await store.listOutbox('org:12')).single['tenant_scope'], 'org:12');
    expect((await store.listOutbox('org:11')).single['status'], 'ENVIANDO');

    await store.updateOutbox(id, 'RECHAZADA', category: 'DATOS_INVALIDOS');
    expect((await store.listOutbox('org:11')).single['status'], 'RECHAZADA');
    await store.setLastSync('org:11');
    expect(await store.getLastSync('org:11'), isNotNull);
    expect(await store.getLastSync('org:12'), isNull);

    await expectLater(
      store.enqueueOperation(tenantScope: 'org:11', operationType: 'demo.noop',
          payload: {'nested': {'password': 'secret'}}, clientId: 'device-test'),
      throwsArgumentError,
    );
  });

  test('recovers interrupted work and retries it in bounded batches', () async {
    final store = CatalogOfflineStore(factory: databaseFactoryFfi);
    addTearDown(store.close);
    final ids = <String>[];
    for (var index = 0; index < 3; index++) {
      ids.add(await store.enqueueOperation(
        tenantScope: 'org:batch', operationType: 'demo.noop',
        payload: {'reference': index}, clientId: 'device-test',
      ));
    }

    final interrupted = await store.claimPending('org:batch');
    expect(interrupted, hasLength(3));
    await (await store.database).update('outbox', {
      'updated_at': DateTime.now().subtract(const Duration(minutes: 6)).millisecondsSinceEpoch,
    }, where: 'tenant_scope = ?', whereArgs: ['org:batch']);
    await store.recoverSending('org:batch');
    expect((await store.listOutbox('org:batch')).every(
      (row) => row['status'] == 'ERROR_REINTENTABLE',
    ), isTrue);

    final retryBatch = await store.claimPending('org:batch', limit: 2);
    expect(retryBatch, hasLength(2));
    expect(retryBatch.map((row) => row['operation_uuid']).toSet(),
        ids.take(2).toSet());
    final remainder = await store.claimPending('org:batch', limit: 2);
    expect(remainder, hasLength(1));
    expect(remainder.single['operation_uuid'], ids.last);
    expect(await store.claimPending('org:batch'), isEmpty);
  });

  test('does not recover a recent send while a worker may still own it', () async {
    final store = CatalogOfflineStore(factory: databaseFactoryFfi);
    addTearDown(store.close);
    await store.enqueueOperation(
      tenantScope: 'org:lease', operationType: 'reserva.crear',
      payload: {'id_usuario': 31}, clientId: 'device-test', ownerUserId: 31,
    );
    await store.claimPending('org:lease', ownerUserId: 31);

    await store.recoverSending('org:lease', ownerUserId: 31);

    expect(await store.hasSending('org:lease', ownerUserId: 31), isTrue);
    expect((await store.listOutbox('org:lease', ownerUserId: 31)).single['status'], 'ENVIANDO');
  });

  test('claims only operations supported by the limited reservation worker', () async {
    final store = CatalogOfflineStore(factory: databaseFactoryFfi);
    addTearDown(store.close);
    final reservation = await store.enqueueOperation(
      tenantScope: 'org:worker', operationType: 'reserva.crear',
      payload: {'id_usuario': 31}, clientId: 'device-test', ownerUserId: 31,
    );
    await store.enqueueOperation(
      tenantScope: 'org:worker', operationType: 'another.operation',
      payload: {'id_usuario': 31}, clientId: 'device-test', ownerUserId: 31,
    );

    final claimed = await store.claimPending('org:worker', ownerUserId: 31,
        operationTypes: {'reserva.crear', 'reserva.cancelar'});

    expect(claimed.single['operation_uuid'], reservation);
    expect((await store.listOutbox('org:worker', ownerUserId: 31))
        .singleWhere((row) => row['operation_type'] == 'another.operation')['status'], 'PENDIENTE');
  });
}
