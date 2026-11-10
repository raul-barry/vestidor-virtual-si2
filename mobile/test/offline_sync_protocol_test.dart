import 'package:flutter_test/flutter_test.dart';
import 'package:vestidor_virtual_mobile/services/offline_sync_protocol.dart';

void main() {
  test('serializes only the backend envelope and clean sync payload', () {
    final wire = OfflineSyncProtocol.toWireOperation({
      'operation_uuid': 'op-1',
      'operation_type': 'venta.crear',
      'payload': {
        'id_usuario': 9,
        'lineas': [
          {
            'client_line_id': 'line-1',
            'id_variante': 7,
            'cantidad': 1,
            'offline_allocations': [
              {'id_inventario': 50, 'cantidad': 1}
            ],
          }
        ],
      },
      'sync_payload': {
        'id_usuario': 9,
        'lineas': [
          {'client_line_id': 'line-1', 'id_variante': 7, 'cantidad': 1}
        ],
      },
      'created_at': '2026-11-08T10:00:00Z',
      'schema_version': 1,
      'client_id': 'device-1',
      'tenant_scope': 'org:9',
      'status': 'ENVIANDO',
      'attempts': 3,
      'last_error': 'local only',
    });

    expect(wire.keys.toSet(), {
      'operation_uuid',
      'operation_type',
      'payload',
      'created_at',
      'schema_version',
      'client_id',
      'tenant_scope',
    });
    expect(wire['payload'], {
      'id_usuario': 9,
      'lineas': [
        {'client_line_id': 'line-1', 'id_variante': 7, 'cantidad': 1}
      ],
    });
  });

  test('rejects malformed local operations before an HTTP request', () {
    expect(
      () => OfflineSyncProtocol.toWireOperation({'operation_uuid': 'broken'}),
      throwsFormatException,
    );
  });
}
