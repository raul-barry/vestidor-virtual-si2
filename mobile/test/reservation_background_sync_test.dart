import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:vestidor_virtual_mobile/services/api_client.dart';
import 'package:vestidor_virtual_mobile/services/catalog_offline_store.dart';
import 'package:vestidor_virtual_mobile/services/reservation_background_sync.dart';
import 'package:vestidor_virtual_mobile/services/reservation_offline_store.dart';
import 'package:vestidor_virtual_mobile/services/session_store.dart';

class _MemoryCredentials implements DeviceSyncCredentialStore {
  _MemoryCredentials(this.values);
  final Map<String, dynamic> values;
  @override
  Future<Map<String, dynamic>> readAll() async => values;
  @override
  Future<void> writeFor(
      int userId, int organizationId, Map<String, dynamic> credential) async {}
  @override
  Future<void> clear() async => values.clear();
}

Map<String, dynamic> _credential(
        int organizationId, int userId, String clientId, String token) =>
    {
      'organization_id': organizationId,
      'user_id': userId,
      'client_id': clientId,
      'sync_token': token,
      'server': 'https://fashion.example.test',
      'expires_at':
          DateTime.now().add(const Duration(days: 1)).toIso8601String(),
    };

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  sqfliteFfiInit();

  test(
      'background runner syncs after logout using only the scoped device credential',
      () async {
    final (outbox, reservations) = await _stores();
    final credentials = _MemoryCredentials({
      '4:21': _credential(4, 21, 'device-21', 'fssync_limited-21'),
    });
    final operationId = await outbox.enqueueOperation(
      tenantScope: 'org:4',
      ownerUserId: 21,
      operationType: 'reserva.crear',
      payload: {'id_usuario': 21, 'id_inventario': 9, 'cantidad': 1},
      clientId: 'device-21',
    );
    await reservations.save('reservations:org:4:21', [
      {
        'id_reserva': 0,
        'id_inventario': 9,
        'cantidad': 1,
        'local_operation_uuid': operationId,
        'estado': 'PENDIENTE'
      }
    ]);
    await reservations.save('availability:org:4:21', [
      {'id_inventario': 9, 'disponible': 0}
    ]);
    String? sentCredential;

    final runner = ReservationBackgroundSyncRunner(
      outbox: outbox,
      reservations: reservations,
      credentials: credentials,
      internetCheck: (_) async => true,
      batchSender: (_, token, operations) async {
        sentCredential = token;
        expect(operations.single['operation_uuid'], operationId);
        return {
          'results': [
            {
              'operation_uuid': operationId,
              'status': 'SINCRONIZADA',
              'result': {
                'id_reserva': 401,
                'estado': 'PENDIENTE',
                'fecha_expiracion_servidor': '2026-11-12T12:00:00Z'
              }
            }
          ]
        };
      },
    );

    expect(await runner.run(), isTrue);
    expect(sentCredential, 'fssync_limited-21');
    final saved = (await outbox.listOutbox('org:4', ownerUserId: 21)).single;
    expect(saved['status'], 'SINCRONIZADA');
    final reservation =
        (await reservations.read('reservations:org:4:21')).single;
    expect(reservation['id_reserva'], 401);
    expect(reservation['local_operation_uuid'], isNull);
  });

  test(
      'failed background send remains retryable and is recovered on the next run',
      () async {
    final (outbox, reservations) = await _stores();
    final credentials = _MemoryCredentials({
      '4:21': _credential(4, 21, 'device-21', 'fssync_limited-21'),
    });
    final operationId = await outbox.enqueueOperation(
      tenantScope: 'org:4',
      ownerUserId: 21,
      operationType: 'reserva.crear',
      payload: {'id_usuario': 21, 'id_inventario': 9, 'cantidad': 1},
      clientId: 'device-21',
    );
    await reservations.save('reservations:org:4:21', [
      {
        'id_reserva': 0,
        'id_inventario': 9,
        'cantidad': 1,
        'local_operation_uuid': operationId,
        'estado': 'PENDIENTE'
      }
    ]);
    var shouldFail = true;

    Future<ReservationBackgroundSyncRunner> makeRunner() async =>
        ReservationBackgroundSyncRunner(
          outbox: outbox,
          reservations: reservations,
          credentials: credentials,
          internetCheck: (_) async => true,
          batchSender: (_, __, operations) async {
            if (shouldFail) throw ApiException(0, 'Servidor inaccesible');
            return {
              'results': [
                {
                  'operation_uuid': operations.single['operation_uuid'],
                  'status': 'SINCRONIZADA',
                  'result': {'id_reserva': 402, 'estado': 'PENDIENTE'}
                }
              ]
            };
          },
        );

    expect(await (await makeRunner()).run(), isFalse);
    expect((await outbox.listOutbox('org:4', ownerUserId: 21)).single['status'],
        'ERROR_REINTENTABLE');
    expect(
        (await reservations.read('reservations:org:4:21'))
            .single['local_operation_uuid'],
        operationId);

    shouldFail = false;
    expect(await (await makeRunner()).run(), isTrue);
    expect((await outbox.listOutbox('org:4', ownerUserId: 21)).single['status'],
        'SINCRONIZADA');
    expect(
        (await reservations.read('reservations:org:4:21')).single['id_reserva'],
        402);
  });

  test(
      'offline payment request survives logout, retries and keeps its organization scope',
      () async {
    final (outbox, reservations) = await _stores();
    final credentials = _MemoryCredentials({
      '4:21': _credential(4, 21, 'device-21', 'fssync_limited-21'),
    });
    final operationId = await outbox.enqueueOperation(
      tenantScope: 'org:4',
      ownerUserId: 21,
      operationType: 'pago.solicitar',
      payload: {
        'id_usuario': 21,
        'id_pedido': 90,
        'metodo_pago': 'QR',
      },
      clientId: 'device-21',
    );
    await reservations.saveOrders('org:4', 21, [
      {'id_pedido': 90, 'estado_pago': 'PENDIENTE'},
    ]);
    var shouldFail = true;
    final runner = ReservationBackgroundSyncRunner(
      outbox: outbox,
      reservations: reservations,
      credentials: credentials,
      internetCheck: (_) async => true,
      batchSender: (server, token, operations) async {
        expect(server, 'https://fashion.example.test');
        expect(token, 'fssync_limited-21');
        expect(operations.single['tenant_scope'], 'org:4');
        expect(operations.single['operation_uuid'], operationId);
        if (shouldFail) throw ApiException(0, 'Servidor inaccesible');
        return {
          'results': [
            {
              'operation_uuid': operationId,
              'status': 'SINCRONIZADA',
              'result': {
                'estado': 'PENDIENTE',
                'requires_online_confirmation': true,
              },
            }
          ]
        };
      },
    );

    expect(await runner.run(), isFalse);
    expect((await outbox.listOutbox('org:4', ownerUserId: 21)).single['status'],
        'ERROR_REINTENTABLE');
    expect((await reservations.orders('org:4', 21)).single['payment_sync_status'],
        'ERROR_REINTENTABLE');

    shouldFail = false;
    expect(await runner.run(), isTrue);
    final saved = (await outbox.listOutbox('org:4', ownerUserId: 21)).single;
    expect(saved['status'], 'SINCRONIZADA');
    expect(saved['tenant_scope'], 'org:4');
    final order = (await reservations.orders('org:4', 21)).single;
    expect(order['estado_pago'], 'PENDIENTE');
    expect(order['payment_sync_status'], 'SINCRONIZADA');
    expect(order['payment_sync_message'], contains('Falta autorizar'));
  });

  test('each saved organization credential can only claim its own outbox rows',
      () async {
    final (outbox, reservations) = await _stores();
    final credentials = _MemoryCredentials({
      '4:21': _credential(4, 21, 'device-21', 'fssync-21'),
      '5:22': _credential(5, 22, 'device-22', 'fssync-22'),
    });
    for (final (org, user, device) in [
      (4, 21, 'device-21'),
      (5, 22, 'device-22')
    ]) {
      final scope = 'org:$org';
      final id = await outbox.enqueueOperation(
        tenantScope: scope,
        ownerUserId: user,
        operationType: 'reserva.crear',
        payload: {'id_usuario': user, 'id_inventario': org, 'cantidad': 1},
        clientId: device,
      );
      await reservations.save('reservations:$scope:$user', [
        {
          'id_reserva': 0,
          'id_inventario': org,
          'cantidad': 1,
          'local_operation_uuid': id,
          'estado': 'PENDIENTE'
        }
      ]);
    }
    final sends = <(String token, String scope)>[];
    final runner = ReservationBackgroundSyncRunner(
      outbox: outbox,
      reservations: reservations,
      credentials: credentials,
      internetCheck: (_) async => true,
      batchSender: (_, token, operations) async {
        final scope = operations.single['tenant_scope'] as String;
        sends.add((token, scope));
        return {
          'results': [
            {
              'operation_uuid': operations.single['operation_uuid'],
              'status': 'SINCRONIZADA',
              'result': {
                'id_reserva': scope == 'org:4' ? 404 : 405,
                'estado': 'PENDIENTE'
              }
            }
          ]
        };
      },
    );

    expect(await runner.run(), isTrue);
    expect(sends.toSet(), {('fssync-21', 'org:4'), ('fssync-22', 'org:5')});
    expect((await outbox.listOutbox('org:4', ownerUserId: 21)).single['status'],
        'SINCRONIZADA');
    expect((await outbox.listOutbox('org:5', ownerUserId: 22)).single['status'],
        'SINCRONIZADA');
  });

  test(
      'background sales reconcile a partial server result and restore rejected local stock',
      () async {
    final (outbox, reservations) = await _stores();
    final credentials = _MemoryCredentials({
      '4:21': _credential(4, 21, 'device-21', 'fssync-sales'),
    });
    final operationId = await outbox.enqueueOperation(
      tenantScope: 'org:4',
      ownerUserId: 21,
      operationType: 'venta.crear',
      clientId: 'device-21',
      payload: {
        'id_usuario': 21,
        'metodo_pago': 'EFECTIVO',
        'lineas': [
          {
            'client_line_id': 'v8',
            'id_variante': 8,
            'cantidad': 1,
            'offline_allocations': [
              {'id_inventario': 77, 'cantidad': 1}
            ]
          },
          {
            'client_line_id': 'v9',
            'id_variante': 9,
            'cantidad': 1,
            'offline_allocations': [
              {'id_inventario': 78, 'cantidad': 1}
            ]
          },
        ]
      },
    );
    await reservations.saveOrders('org:4', 21, [
      {
        'id_pedido': null,
        'local_operation_uuid': operationId,
        'numero_local': '12345678',
        'estado_sync': 'PENDIENTE',
        'total': '45.00',
        'metodo_pago': 'EFECTIVO',
        'detalles': [
          {
            'client_line_id': 'v8',
            'id_variante': 8,
            'cantidad': 1,
            'offline_allocations': [
              {'id_inventario': 77, 'cantidad': 1}
            ]
          },
          {
            'client_line_id': 'v9',
            'id_variante': 9,
            'cantidad': 1,
            'offline_allocations': [
              {'id_inventario': 78, 'cantidad': 1}
            ]
          },
        ],
      }
    ]);
    await reservations.save('availability:org:4:21', [
      {'id_inventario': 77, 'id_variante': 8, 'disponible': 0},
      {'id_inventario': 78, 'id_variante': 9, 'disponible': 0},
    ]);

    final runner = ReservationBackgroundSyncRunner(
      outbox: outbox,
      reservations: reservations,
      credentials: credentials,
      internetCheck: (_) async => true,
      batchSender: (_, token, operations) async {
        expect(token, 'fssync-sales');
        return {
          'results': [
            {
              'operation_uuid': operationId,
              'status': 'SINCRONIZADA',
              'result': {
                'pedido': {
                  'id_pedido': 902,
                  'estado': 'PENDIENTE',
                  'total': '20.00',
                  'metodo_pago': 'EFECTIVO',
                  'estado_pago': 'PENDIENTE'
                },
                'lineas_aceptadas': [
                  {'client_line_id': 'v8', 'precio_unitario': '20.00'}
                ],
                'lineas_rechazadas': [
                  {
                    'client_line_id': 'v9',
                    'id_variante': 9,
                    'cantidad': 1,
                    'motivo': 'CONFLICTO_INVENTARIO'
                  }
                ],
                'parcial': true,
              },
            }
          ]
        };
      },
    );

    expect(await runner.run(), isTrue);
    final saved = (await outbox.listOutbox('org:4', ownerUserId: 21)).single;
    expect(saved['status'], 'SINCRONIZADA');
    final orders = await reservations.orders('org:4', 21);
    expect(orders.single['id_pedido'], 902);
    expect(orders.single['estado_sync'], 'PARCIAL');
    final lines = orders.single['detalles'] as List;
    expect(lines[0]['estado_sync'], 'CONFIRMADA');
    expect(lines[1]['estado_sync'], 'RECHAZADA');
    final stock = await reservations.read('availability:org:4:21');
    expect(stock[0]['disponible'], 0);
    expect(stock[1]['disponible'], 1);
  });
}

Future<(CatalogOfflineStore, ReservationOfflineStore)> _stores() async {
  final directory =
      await Directory.systemTemp.createTemp('cu26-background-sync-');
  final outbox = CatalogOfflineStore(
    factory: databaseFactoryFfi,
    databasePath: '${directory.path}${Platform.pathSeparator}outbox.db',
  );
  final reservations = ReservationOfflineStore(
    factory: databaseFactoryFfi,
    databasePath: '${directory.path}${Platform.pathSeparator}reservations.db',
  );
  return (outbox, reservations);
}
