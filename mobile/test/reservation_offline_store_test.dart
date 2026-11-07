import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:vestidor_virtual_mobile/services/reservation_offline_store.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  sqfliteFfiInit();

  test('scopes cached reservations and availability by organization and user',
      () async {
    final store = ReservationOfflineStore(factory: databaseFactoryFfi);
    addTearDown(store.close);
    await store.save('reservations:org:4:21', [
      {'id_reserva': 7}
    ]);
    await store.save('reservations:org:4:22', [
      {'id_reserva': 8}
    ]);
    await store.save('availability:org:4:21', [
      {'id_inventario': 1, 'disponible': 2}
    ]);

    expect((await store.read('reservations:org:4:21')).single['id_reserva'], 7);
    expect((await store.read('reservations:org:4:22')).single['id_reserva'], 8);
    expect(await store.read('availability:org:4:22'), isEmpty);
  });

  test('reconciles pending payment only inside its organization and user scope',
      () async {
    final store = ReservationOfflineStore(factory: databaseFactoryFfi);
    addTearDown(store.close);
    await store.saveOrders('org:4', 21, [
      {'id_pedido': 90, 'estado_pago': 'PENDIENTE'}
    ]);
    await store.saveOrders('org:5', 21, [
      {'id_pedido': 90, 'estado_pago': 'PENDIENTE'}
    ]);
    final operation = {
      'operation_uuid': 'payment-op',
      'tenant_scope': 'org:4',
      'payload': {'id_usuario': 21, 'id_pedido': 90}
    };

    await store.reconcilePayment(
      operation,
      {'estado': 'PENDIENTE', 'requires_online_confirmation': true},
      'SINCRONIZADA',
      null,
    );

    final saved = (await store.orders('org:4', 21)).single;
    expect(saved['payment_sync_status'], 'SINCRONIZADA');
    expect(saved['payment_sync_message'], contains('Falta autorizar'));
    expect((await store.orders('org:5', 21)).single['payment_sync_status'], isNull);
  });

  test(
      'keeps offline exchange requests and reconciliation scoped to tenant and owner',
      () async {
    final store = ReservationOfflineStore(factory: databaseFactoryFfi);
    addTearDown(store.close);
    await store.saveExchanges('org:4', 21, [
      {
        'local_operation_uuid': 'exchange-op',
        'state': 'SOLICITUD_LOCAL_PENDIENTE'
      }
    ]);
    await store.saveExchanges('org:5', 21, [
      {
        'local_operation_uuid': 'other-tenant',
        'state': 'SOLICITUD_LOCAL_PENDIENTE'
      }
    ]);
    final operation = {
      'operation_uuid': 'exchange-op',
      'operation_type': 'cambio.solicitar',
      'tenant_scope': 'org:4',
      'payload': {'id_usuario': 21, 'id_detalle': 44}
    };
    await store.reconcileExchange(
        operation,
        {'id': 8, 'state': 'SOLICITADO', 'original_order_id': 12},
        'SINCRONIZADA',
        null);

    final saved = (await store.exchanges('org:4', 21)).single;
    expect(saved['id'], 8);
    expect(saved['state'], 'SOLICITADO');
    expect(saved['sync_status'], 'SINCRONIZADA');
    expect((await store.exchanges('org:5', 21)).single['local_operation_uuid'],
        'other-tenant');
    expect(await store.exchanges('org:4', 22), isEmpty);
  });

  test('rejection restores provisional stock and preserves its reason',
      () async {
    final store = ReservationOfflineStore(factory: databaseFactoryFfi);
    addTearDown(store.close);
    await store.save('availability:org:4:21', [
      {'id_inventario': 1, 'disponible': 0}
    ]);
    await store.save('reservations:org:4:21', [
      {
        'id_reserva': 0,
        'id_inventario': 1,
        'cantidad': 1,
        'local_operation_uuid': 'op-1',
        'estado': 'PENDIENTE'
      }
    ]);
    await store.reconcile({
      'operation_uuid': 'op-1',
      'operation_type': 'reserva.crear',
      'tenant_scope': 'org:4',
      'payload': {'id_usuario': 21, 'id_inventario': 1, 'cantidad': 1}
    }, null, 'RECHAZADA', 'Disponibilidad insuficiente.');

    expect((await store.read('availability:org:4:21')).single['disponible'], 1);
    expect((await store.read('reservations:org:4:21')).single,
        containsPair('sync_message', 'Disponibilidad insuficiente.'));
  });

  test('server confirmation reconciles a provisional offline creation',
      () async {
    final store = ReservationOfflineStore(factory: databaseFactoryFfi);
    addTearDown(store.close);
    await store.save('availability:org:4:21', [
      {'id_inventario': 1, 'disponible': 2}
    ]);
    await store.save('reservations:org:4:21', [
      {
        'id_reserva': 0,
        'id_inventario': 1,
        'cantidad': 1,
        'local_operation_uuid': 'create-1',
        'estado': 'PENDIENTE'
      }
    ]);

    await store.reconcile({
      'operation_uuid': 'create-1',
      'operation_type': 'reserva.crear',
      'tenant_scope': 'org:4',
      'payload': {'id_usuario': 21, 'id_inventario': 1, 'cantidad': 1}
    }, {
      'id_reserva': 501,
      'estado': 'PENDIENTE',
      'fecha_expiracion_servidor': '2026-11-12T12:00:00Z'
    }, 'SINCRONIZADA', null);

    final confirmed = (await store.read('reservations:org:4:21')).single;
    expect(confirmed['id_reserva'], 501);
    expect(confirmed['local_operation_uuid'], isNull);
    expect(confirmed['sync_status'], 'SINCRONIZADA');
    expect(confirmed['fecha_expiracion_servidor'], '2026-11-12T12:00:00Z');
  });

  test('cancel confirmation changes local state without reapplying stock',
      () async {
    final store = ReservationOfflineStore(factory: databaseFactoryFfi);
    addTearDown(store.close);
    await store.save('availability:org:4:21', [
      {'id_inventario': 1, 'disponible': 2}
    ]);
    await store.save('reservations:org:4:21', [
      {
        'id_reserva': 7,
        'id_inventario': 1,
        'cantidad': 1,
        'local_cancel_operation_uuid': 'cancel-7',
        'estado': 'CANCELACION_PENDIENTE'
      }
    ]);

    await store.reconcile({
      'operation_uuid': 'cancel-7',
      'operation_type': 'reserva.cancelar',
      'tenant_scope': 'org:4',
      'payload': {
        'id_usuario': 21,
        'id_reserva': 7,
        'id_inventario': 1,
        'cantidad': 1
      }
    }, {
      'id_reserva': 7,
      'estado': 'CANCELADA'
    }, 'SINCRONIZADA', null);

    expect((await store.read('reservations:org:4:21')).single['estado'],
        'CANCELADA');
    expect((await store.read('availability:org:4:21')).single['disponible'], 2);
  });

  test('snapshots survive closing and reopening the SQLite database', () async {
    final directory =
        await Directory.systemTemp.createTemp('cu26-reservation-store-');
    addTearDown(() => directory.delete(recursive: true));
    final path = '${directory.path}${Platform.pathSeparator}reservations.db';
    final first = ReservationOfflineStore(
        factory: databaseFactoryFfi, databasePath: path);
    await first.save('reservations:org:4:21', [
      {'id_reserva': 44, 'estado': 'PENDIENTE'}
    ]);
    await first.close();
    final reopened = ReservationOfflineStore(
        factory: databaseFactoryFfi, databasePath: path);
    addTearDown(reopened.close);

    expect((await reopened.read('reservations:org:4:21')).single['id_reserva'],
        44);
  });
}
