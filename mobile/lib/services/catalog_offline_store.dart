import 'dart:convert';
import 'dart:math';
import 'package:path/path.dart' as p;
import 'package:sqflite/sqflite.dart';

class CatalogOfflineStore {
  CatalogOfflineStore({DatabaseFactory? factory, String? databasePath})
      : _factory = factory,
        _databasePath = databasePath;
  final DatabaseFactory? _factory;
  final String? _databasePath;
  Database? _database;

  Future<Database> get database async => _database ??= await (_factory == null
      ? openDatabase(p.join(await getDatabasesPath(), 'fashion_catalog.db'),
          version: 3, onCreate: _create, onUpgrade: _upgrade)
      : _factory.openDatabase(_databasePath ?? ':memory:',
          options: OpenDatabaseOptions(
              version: 3, onCreate: _create, onUpgrade: _upgrade)));

  Future<void> _create(Database db, int _) async {
    await db.execute(
        'CREATE TABLE catalog_snapshots (scope TEXT PRIMARY KEY, products TEXT NOT NULL, synced_at INTEGER NOT NULL)');
    await db.execute(
        'CREATE TABLE catalog_categories (scope TEXT NOT NULL, category_id INTEGER NOT NULL, name TEXT NOT NULL, PRIMARY KEY(scope, category_id))');
    await _createOutbox(db);
  }

  Future<void> _upgrade(Database db, int oldVersion, int newVersion) async {
    if (oldVersion < 2) await _createOutbox(db);
    if (oldVersion >= 2 && oldVersion < 3)
      await db.execute('ALTER TABLE outbox ADD COLUMN owner_user_id INTEGER');
  }

  Future<void> _createOutbox(Database db) async {
    await db.execute(
        'CREATE TABLE outbox (operation_uuid TEXT PRIMARY KEY, tenant_scope TEXT NOT NULL, operation_json TEXT NOT NULL, status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, error_category TEXT, error_message TEXT, created_at TEXT NOT NULL, updated_at INTEGER NOT NULL, owner_user_id INTEGER)');
    await db.execute(
        'CREATE INDEX ix_outbox_scope_status ON outbox(tenant_scope, status)');
    await db.execute(
        'CREATE TABLE sync_metadata (tenant_scope TEXT PRIMARY KEY, last_sync INTEGER NOT NULL)');
  }

  Future<String> enqueueOperation(
      {required String tenantScope,
      required String operationType,
      required Map<String, dynamic> payload,
      Map<String, dynamic>? syncPayload,
      required String clientId,
      int? ownerUserId,
      int schemaVersion = 1}) async {
    if (_containsCredential(payload) ||
        (syncPayload != null && _containsCredential(syncPayload))) {
      throw ArgumentError('Outbox no puede almacenar tokens ni credenciales.');
    }
    final id = _uuid();
    final createdAt = DateTime.now().toUtc().toIso8601String();
    final operation = <String, dynamic>{
      'operation_uuid': id,
      'operation_type': operationType,
      'payload': payload,
      'created_at': createdAt,
      'schema_version': schemaVersion,
      'client_id': clientId,
      'tenant_scope': tenantScope,
      if (syncPayload != null) 'sync_payload': syncPayload,
    };
    await (await database).insert('outbox', {
      'operation_uuid': id,
      'tenant_scope': tenantScope,
      'operation_json': jsonEncode(operation),
      'status': 'PENDIENTE',
      'attempts': 0,
      'created_at': createdAt,
      'updated_at': DateTime.now().millisecondsSinceEpoch,
      'owner_user_id': ownerUserId,
    });
    return id;
  }

  static bool _containsCredential(dynamic value) {
    const forbidden = {
      'authorization',
      'access_token',
      'refresh_token',
      'token',
      'password',
      'password_hash',
      'secret',
      'cvv',
      'card_number',
      'numero_tarjeta'
    };
    if (value is Map)
      return value.entries.any((entry) =>
          forbidden.contains(entry.key.toString().toLowerCase()) ||
          _containsCredential(entry.value));
    if (value is List) return value.any(_containsCredential);
    return false;
  }

  static String _uuid() {
    final bytes = List<int>.generate(16, (_) => Random.secure().nextInt(256));
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    final hex =
        bytes.map((byte) => byte.toRadixString(16).padLeft(2, '0')).join();
    return '${hex.substring(0, 8)}-${hex.substring(8, 12)}-${hex.substring(12, 16)}-${hex.substring(16, 20)}-${hex.substring(20)}';
  }

  Future<List<Map<String, dynamic>>> listOutbox(String scope,
      {int? ownerUserId}) async {
    final rows = await (await database).query('outbox',
        where: ownerUserId == null
            ? 'tenant_scope = ?'
            : 'tenant_scope = ? AND owner_user_id = ?',
        whereArgs: ownerUserId == null ? [scope] : [scope, ownerUserId],
        orderBy: 'created_at');
    return rows
        .map((row) => <String, dynamic>{
              ...Map<String, dynamic>.from(
                  jsonDecode(row['operation_json'] as String) as Map),
              'status': row['status'],
              'attempts': row['attempts'],
              'error_category': row['error_category'],
              'error_message': row['error_message'],
              'updated_at': row['updated_at'],
            })
        .toList();
  }

  Future<List<Map<String, dynamic>>> claimPending(
    String scope, {
    int limit = 50,
    int? ownerUserId,
    Set<String>? operationTypes,
  }) async {
    final db = await database;
    return db.transaction((txn) async {
      final where = <String>['tenant_scope = ?', 'status IN (?, ?)'];
      final args = <Object?>[scope, 'PENDIENTE', 'ERROR_REINTENTABLE'];
      if (ownerUserId != null) {
        where.add('owner_user_id = ?');
        args.add(ownerUserId);
      }
      if (operationTypes != null && operationTypes.isNotEmpty) {
        where.add(
            "json_extract(operation_json, '\$.operation_type') IN (${List.filled(operationTypes.length, '?').join(',')})");
        args.addAll(operationTypes);
      }
      final rows = await txn.query('outbox',
          where: where.join(' AND '),
          whereArgs: args,
          orderBy: 'created_at',
          limit: limit);
      final claimed = <Map<String, dynamic>>[];
      for (final row in rows) {
        await txn.update(
            'outbox',
            {
              'status': 'ENVIANDO',
              'attempts': (row['attempts'] as int) + 1,
              'updated_at': DateTime.now().millisecondsSinceEpoch
            },
            where: 'operation_uuid = ? AND status IN (?, ?)',
            whereArgs: [
              row['operation_uuid'],
              'PENDIENTE',
              'ERROR_REINTENTABLE'
            ]);
        claimed.add(Map<String, dynamic>.from(
            jsonDecode(row['operation_json'] as String) as Map));
      }
      return claimed;
    });
  }

  Future<void> updateOutbox(String id, String status,
      {String? category, String? message}) async {
    await (await database).update(
        'outbox',
        {
          'status': status,
          'error_category': category,
          'error_message': message,
          'updated_at': DateTime.now().millisecondsSinceEpoch
        },
        where: 'operation_uuid = ?',
        whereArgs: [id]);
  }

  Future<bool> deleteOutbox(String id) async {
    final deleted = await (await database).delete('outbox',
        where: 'operation_uuid = ? AND status IN (?, ?)',
        whereArgs: [id, 'PENDIENTE', 'ERROR_REINTENTABLE']);
    return deleted == 1;
  }

  Future<void> recoverSending(
    String scope, {
    int? ownerUserId,
    Duration staleAfter = const Duration(minutes: 5),
  }) async {
    final where = <String>['tenant_scope = ?', 'status = ?', 'updated_at <= ?'];
    final args = <Object?>[
      scope,
      'ENVIANDO',
      DateTime.now().subtract(staleAfter).millisecondsSinceEpoch,
    ];
    if (ownerUserId != null) {
      where.add('owner_user_id = ?');
      args.add(ownerUserId);
    }
    await (await database).update(
        'outbox',
        {
          'status': 'ERROR_REINTENTABLE',
          'error_category': 'TEMPORAL',
          'error_message': 'Se reanuda una operaci??n interrumpida.',
          'updated_at': DateTime.now().millisecondsSinceEpoch,
        },
        where: where.join(' AND '),
        whereArgs: args);
  }

  Future<bool> hasSending(String scope, {int? ownerUserId}) async {
    final rows = await (await database).query('outbox',
        columns: ['operation_uuid'],
        where: ownerUserId == null
            ? 'tenant_scope = ? AND status = ?'
            : 'tenant_scope = ? AND owner_user_id = ? AND status = ?',
        whereArgs: ownerUserId == null
            ? [scope, 'ENVIANDO']
            : [scope, ownerUserId, 'ENVIANDO'],
        limit: 1);
    return rows.isNotEmpty;
  }

  Future<void> setLastSync(String scope) async {
    await (await database).insert(
        'sync_metadata',
        {
          'tenant_scope': scope,
          'last_sync': DateTime.now().millisecondsSinceEpoch
        },
        conflictAlgorithm: ConflictAlgorithm.replace);
  }

  Future<int?> getLastSync(String scope) async {
    final rows = await (await database).query('sync_metadata',
        where: 'tenant_scope = ?', whereArgs: [scope], limit: 1);
    return rows.isEmpty ? null : rows.first['last_sync'] as int;
  }

  Future<void> save(String scope, List<Map<String, dynamic>> products) async {
    final db = await database;
    final batch = db.batch();
    batch.insert(
        'catalog_snapshots',
        {
          'scope': scope,
          'products': jsonEncode(products),
          'synced_at': DateTime.now().millisecondsSinceEpoch
        },
        conflictAlgorithm: ConflictAlgorithm.replace);
    batch.delete('catalog_categories', where: 'scope = ?', whereArgs: [scope]);
    for (final product in products) {
      final category = product['categoria'];
      if (category is Map && category['id_categoria'] is int) {
        batch.insert(
            'catalog_categories',
            {
              'scope': scope,
              'category_id': category['id_categoria'],
              'name': category['nombre'] ?? ''
            },
            conflictAlgorithm: ConflictAlgorithm.replace);
      }
    }
    await batch.commit(noResult: true);
  }

  Future<({List<Map<String, dynamic>> products, DateTime? syncedAt})> read(
      String scope) async {
    final db = await database;
    final rows = await db.query('catalog_snapshots',
        where: 'scope = ?', whereArgs: [scope], limit: 1);
    if (rows.isEmpty)
      return (products: <Map<String, dynamic>>[], syncedAt: null);
    final snapshot = rows.first;
    final products = (jsonDecode(snapshot['products'] as String) as List)
        .map((item) => Map<String, dynamic>.from(item as Map))
        .toList();
    return (
      products: products,
      syncedAt:
          DateTime.fromMillisecondsSinceEpoch(snapshot['synced_at'] as int)
    );
  }

  Future<void> close() async {
    await _database?.close();
    _database = null;
  }
}
