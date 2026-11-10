import 'dart:convert';
import 'package:vestidor_virtual_mobile/services/session_store.dart';
import 'package:vestidor_virtual_mobile/services/catalog_offline_store.dart';
import 'package:vestidor_virtual_mobile/services/reservation_offline_store.dart';

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

String jwt(
        {String role = 'CLIENTE',
        int? expires,
        int? organizationId = 1,
        int? userId = 7}) =>
    'header.${base64Url.encode(utf8.encode(jsonEncode({
              'rol': role,
              if (userId != null) 'id_usuario': userId,
              if (organizationId != null) 'id_organizacion': organizationId,
              'exp': expires ??
                  DateTime.now().millisecondsSinceEpoch ~/ 1000 + 3600,
            }))).replaceAll('=', '')}.signature';

class MemoryCatalogStore extends CatalogOfflineStore {
  final Map<String, List<Map<String, dynamic>>> catalogs = {};
  final Map<String, int> syncTimes = {};

  @override
  Future<void> save(String scope, List<Map<String, dynamic>> products) async {
    catalogs[scope] = products.map(Map<String, dynamic>.from).toList();
    syncTimes[scope] = DateTime.now().millisecondsSinceEpoch;
  }

  @override
  Future<({List<Map<String, dynamic>> products, DateTime? syncedAt})> read(
          String scope) async =>
      (
        products:
            catalogs[scope]?.map(Map<String, dynamic>.from).toList() ?? [],
        syncedAt: syncTimes[scope] == null
            ? null
            : DateTime.fromMillisecondsSinceEpoch(syncTimes[scope]!),
      );

  int _operationNumber = 0;
  final List<Map<String, dynamic>> operations = [];

  @override
  Future<String> enqueueOperation({
    required String tenantScope,
    required String operationType,
    required Map<String, dynamic> payload,
    Map<String, dynamic>? syncPayload,
    required String clientId,
    int? ownerUserId,
    int schemaVersion = 1,
  }) async {
    final id = 'memory-operation-${++_operationNumber}';
    operations.add({
      'operation_uuid': id,
      'operation_type': operationType,
      'payload': Map<String, dynamic>.from(payload),
      if (syncPayload != null)
        'sync_payload': Map<String, dynamic>.from(syncPayload),
      'created_at': DateTime.now().toUtc().toIso8601String(),
      'schema_version': schemaVersion,
      'client_id': clientId,
      'tenant_scope': tenantScope,
      'owner_user_id': ownerUserId,
      'status': 'PENDIENTE',
      'attempts': 0,
    });
    return id;
  }

  @override
  Future<List<Map<String, dynamic>>> claimPending(String scope,
      {int limit = 50, int? ownerUserId, Set<String>? operationTypes}) async {
    final claimed = operations
        .where((operation) =>
            operation['tenant_scope'] == scope &&
            operation['owner_user_id'] == ownerUserId &&
            {'PENDIENTE', 'ERROR_REINTENTABLE'}.contains(operation['status']) &&
            (operationTypes == null ||
                operationTypes.contains(operation['operation_type'])))
        .take(limit)
        .toList();
    for (final operation in claimed) {
      operation['status'] = 'ENVIANDO';
      operation['attempts'] = (operation['attempts'] as int) + 1;
    }
    return claimed.map(Map<String, dynamic>.from).toList();
  }

  @override
  Future<void> updateOutbox(String id, String status,
      {String? category, String? message}) async {
    final operation =
        operations.where((row) => row['operation_uuid'] == id).firstOrNull;
    if (operation == null) return;
    operation['status'] = status;
    operation['error_category'] = category;
    operation['error_message'] = message;
  }

  @override
  Future<List<Map<String, dynamic>>> listOutbox(String scope,
          {int? ownerUserId}) async =>
      operations
          .where((row) =>
              row['tenant_scope'] == scope &&
              row['owner_user_id'] == ownerUserId)
          .map(Map<String, dynamic>.from)
          .toList();

  @override
  Future<void> recoverSending(String scope,
      {int? ownerUserId,
      Duration staleAfter = const Duration(minutes: 5)}) async {}

  @override
  Future<void> setLastSync(String scope) async {
    syncTimes[scope] = DateTime.now().millisecondsSinceEpoch;
  }

  @override
  Future<int?> getLastSync(String scope) async => syncTimes[scope];
}

class MemoryReservationStore extends ReservationOfflineStore {
  final Map<String, List<Map<String, dynamic>>> values = {};

  @override
  Future<void> save(String key, List<Map<String, dynamic>> rows) async {
    values[key] = rows.map(Map<String, dynamic>.from).toList();
  }

  @override
  Future<List<Map<String, dynamic>>> read(String key) async =>
      values[key]?.map(Map<String, dynamic>.from).toList() ?? [];

  @override
  Future<List<Map<String, dynamic>>> orders(String scope, int userId) =>
      read('sales:orders:$scope:$userId');

  @override
  Future<void> saveOrders(
          String scope, int userId, List<Map<String, dynamic>> rows) =>
      save('sales:orders:$scope:$userId', rows);

  @override
  Future<List<Map<String, dynamic>>> exchanges(String scope, int userId) =>
      read('exchanges:$scope:$userId');

  @override
  Future<void> saveExchanges(
          String scope, int userId, List<Map<String, dynamic>> rows) =>
      save('exchanges:$scope:$userId', rows);
}
