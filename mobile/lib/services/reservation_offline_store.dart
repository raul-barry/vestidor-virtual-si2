import 'dart:convert';
import 'package:path/path.dart' as p;
import 'package:sqflite/sqflite.dart';

class ReservationOfflineStore {
  ReservationOfflineStore({DatabaseFactory? factory, String? databasePath})
      : _factory = factory,
        _databasePath = databasePath;
  final DatabaseFactory? _factory;
  final String? _databasePath;
  Database? _database;

  Future<Database> get database async {
    if (_database != null) return _database!;
    if (_factory == null) {
      final dbPath = _databasePath ??
          p.join(await getDatabasesPath(), 'fashion_reservations.db');
      _database = await openDatabase(dbPath, version: 1, onCreate: _create);
    } else {
      _database = await _factory.openDatabase(
        _databasePath ?? ':memory:',
        options: OpenDatabaseOptions(version: 1, onCreate: _create),
      );
    }
    return _database!;
  }

  Future<void> _create(Database db, int _) async {
    await db.execute(
        'CREATE TABLE reservation_cache (cache_key TEXT PRIMARY KEY, value_json TEXT NOT NULL, updated_at INTEGER NOT NULL)');
  }

  Future<void> save(String key, List<Map<String, dynamic>> values) async {
    await (await database).insert(
        'reservation_cache',
        {
          'cache_key': key,
          'value_json': jsonEncode(values),
          'updated_at': DateTime.now().millisecondsSinceEpoch,
        },
        conflictAlgorithm: ConflictAlgorithm.replace);
  }

  Future<List<Map<String, dynamic>>> read(String key) async {
    final rows = await (await database).query('reservation_cache',
        where: 'cache_key = ?', whereArgs: [key], limit: 1);
    if (rows.isEmpty) return [];
    return (jsonDecode(rows.single['value_json'] as String) as List)
        .map((item) => Map<String, dynamic>.from(item as Map))
        .toList();
  }

  Future<List<Map<String, dynamic>>> orders(String scope, int userId) =>
      read('sales:orders:$scope:$userId');

  Future<void> saveOrders(
          String scope, int userId, List<Map<String, dynamic>> values) =>
      save('sales:orders:$scope:$userId', values);

  Future<List<Map<String, dynamic>>> exchanges(String scope, int userId) =>
      read('exchanges:$scope:$userId');

  Future<void> saveExchanges(
          String scope, int userId, List<Map<String, dynamic>> values) =>
      save('exchanges:$scope:$userId', values);

  Future<void> reconcileExchange(Map<String, dynamic> operation,
      Map<String, dynamic>? response, String status, String? message) async {
    final payload =
        Map<String, dynamic>.from(operation['payload'] as Map? ?? const {});
    final userId = payload['id_usuario'];
    final scope = operation['tenant_scope'];
    if (userId is! int || scope is! String) return;
    final values = await exchanges(scope, userId);
    final index = values.indexWhere(
        (row) => row['local_operation_uuid'] == operation['operation_uuid']);
    if (index < 0) return;
    values[index] = {
      ...values[index],
      ...?response,
      'local_operation_uuid': operation['operation_uuid'],
      'sync_status': status,
      'sync_message': message,
    };
    await saveExchanges(scope, userId, values);
  }

  Future<void> reconcileSale(Map<String, dynamic> operation,
      Map<String, dynamic>? response, String status, String? message) async {
    final payload =
        Map<String, dynamic>.from(operation['payload'] as Map? ?? const {});
    final userId = payload['id_usuario'];
    final scope = operation['tenant_scope'];
    if (userId is! int || scope is! String) return;
    final values = await orders(scope, userId);
    final index = values.indexWhere(
        (row) => row['local_operation_uuid'] == operation['operation_uuid']);
    if (index < 0) return;
    final order = values[index];
    final rejected = (response?['lineas_rechazadas'] as List? ?? const [])
        .whereType<Map>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList();
    final accepted = (response?['lineas_aceptadas'] as List? ?? const [])
        .whereType<Map>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList();
    final lines = (order['detalles'] as List? ?? const [])
        .whereType<Map>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList();
    for (final line in lines) {
      final rejectedLine = rejected
          .where((item) => item['client_line_id'] == line['client_line_id'])
          .firstOrNull;
      final acceptedLine = accepted
          .where((item) => item['client_line_id'] == line['client_line_id'])
          .firstOrNull;
      if (rejectedLine != null) {
        line['estado_sync'] = 'RECHAZADA';
        line['motivo_rechazo'] = rejectedLine['motivo'];
        final key = 'availability:$scope:$userId';
        final availability = await read(key);
        final allocations =
            (line['offline_allocations'] as List? ?? const []).whereType<Map>();
        for (final allocation in allocations) {
          final inventory = availability
              .where((item) =>
                  item['id_inventario'] == allocation['id_inventario'])
              .firstOrNull;
          if (inventory != null)
            inventory['disponible'] = (inventory['disponible'] as int) +
                (allocation['cantidad'] as int);
        }
        await save(key, availability);
      } else if (acceptedLine != null) {
        line['estado_sync'] = 'CONFIRMADA';
        line['precio_unitario_confirmado'] = acceptedLine['precio_unitario'];
      }
    }
    if (status == 'SINCRONIZADA') {
      final sale = response?['pedido'] as Map?;
      if (sale != null) {
        order.addAll(Map<String, dynamic>.from(sale));
        order['id_pedido'] = sale['id_pedido'];
        order['estado_sync'] = rejected.isEmpty ? 'CONFIRMADA' : 'PARCIAL';
        order['total'] = sale['total'];
        order['metodo_pago'] = sale['metodo_pago'];
        order['estado_pago'] = sale['estado_pago'];
        order['mensaje_sync'] = rejected.isEmpty
            ? 'Tu compra ha sido confirmada'
            : 'Algunos productos no tenían disponibilidad';
      } else {
        order['estado_sync'] = 'RECHAZADA';
        order['mensaje_sync'] =
            message ?? 'La venta fue rechazada por el servidor.';
      }
    } else if (status == 'RECHAZADA') {
      order['estado_sync'] = 'RECHAZADA';
      order['mensaje_sync'] =
          message ?? 'La venta fue rechazada por el servidor.';
    } else {
      order['estado_sync'] = 'ERROR_REINTENTABLE';
      order['mensaje_sync'] =
          message ?? 'Venta registrada. Esperando confirmación';
    }
    order['detalles'] = lines;
    values[index] = order;
    await saveOrders(scope, userId, values);
  }

  Future<void> reconcilePayment(Map<String, dynamic> operation,
      Map<String, dynamic>? response, String status, String? message) async {
    final payload = Map<String, dynamic>.from(operation['payload'] as Map? ?? const {});
    final userId = payload['id_usuario'];
    final orderId = payload['id_pedido'];
    final scope = operation['tenant_scope'];
    if (userId is! int || orderId is! int || scope is! String) return;
    final values = await orders(scope, userId);
    final index = values.indexWhere((row) => row['id_pedido'] == orderId);
    if (index < 0) return;
    values[index] = {
      ...values[index],
      if (response?['estado'] is String) 'estado_pago': response!['estado'],
      'payment_sync_status': status,
      'payment_sync_message': message ??
          (response?['requires_online_confirmation'] == true
              ? 'Solicitud registrada. Falta autorizar el pago con el proveedor.'
              : null),
    };
    await saveOrders(scope, userId, values);
  }

  Future<void> reconcile(Map<String, dynamic> operation,
      Map<String, dynamic>? response, String status, String? message) async {
    final payload =
        Map<String, dynamic>.from(operation['payload'] as Map? ?? const {});
    final userId = payload['id_usuario'];
    if (userId is! int) return;
    final scope = operation['tenant_scope'] as String;
    final reservationsKey = 'reservations:$scope:$userId';
    final reservations = await read(reservationsKey);
    final availabilityKey = 'availability:$scope:$userId';
    final availability = await read(availabilityKey);
    final creating = operation['operation_type'] == 'reserva.crear';
    final index = reservations.indexWhere((row) => creating
        ? row['local_operation_uuid'] == operation['operation_uuid']
        : row['id_reserva'] == payload['id_reserva']);
    final row = index >= 0 ? reservations[index] : null;
    final inventoryId = payload['id_inventario'] ?? row?['id_inventario'];
    final quantity = payload['cantidad'] ?? row?['cantidad'] ?? 0;
    final inv = availability
        .where((item) => item['id_inventario'] == inventoryId)
        .firstOrNull;
    if (creating) {
      if (status == 'SINCRONIZADA' && row != null) {
        reservations[index] = {
          ...row,
          ...?response,
          'local_operation_uuid': null,
          'estado': response?['estado'] ?? 'PENDIENTE',
          'sync_status': status
        };
      } else if (status == 'RECHAZADA') {
        if (row != null) {
          row['estado'] = 'RECHAZADA';
          row['sync_status'] = status;
          row['sync_message'] = message;
        }
        if (inv != null)
          inv['disponible'] = (inv['disponible'] as int) + (quantity as int);
      } else if (row != null) {
        row['sync_status'] = status;
        row['sync_message'] = message;
      }
    } else if (operation['operation_type'] == 'reserva.cancelar' &&
        row != null) {
      if (status == 'SINCRONIZADA') {
        row['estado'] = 'CANCELADA';
        row['sync_status'] = status;
        row.remove('local_cancel_operation_uuid');
      } else if (status == 'RECHAZADA') {
        row['estado'] = payload['estado_anterior'] ?? 'PENDIENTE';
        row['sync_status'] = status;
        row['sync_message'] = message;
        row.remove('local_cancel_operation_uuid');
        if (inv != null)
          inv['disponible'] = ((inv['disponible'] as int) - (quantity as int))
              .clamp(0, 1 << 31);
      } else {
        row['sync_status'] = status;
        row['sync_message'] = message;
      }
    }
    await save(reservationsKey, reservations);
    await save(availabilityKey, availability);
  }

  Future<void> close() async {
    await _database?.close();
    _database = null;
  }
}
