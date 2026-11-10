const clientOutboxOperationTypes = <String>{
  'reserva.crear',
  'reserva.cancelar',
  'venta.crear',
  'cambio.solicitar',
  'pago.solicitar',
};

/// Projects a durable local outbox record onto the strict backend contract.
/// Database status, retry counters, local reconciliation data, and error details
/// must never become fields in the HTTP operation envelope.
class OfflineSyncProtocol {
  const OfflineSyncProtocol._();

  static Map<String, dynamic> toWireOperation(Map<String, dynamic> operation) {
    final payload = operation['sync_payload'] ?? operation['payload'];
    if (payload is! Map) {
      throw const FormatException('La operación local no contiene payload.');
    }
    return {
      'operation_uuid': operation['operation_uuid'],
      'operation_type': operation['operation_type'],
      'payload': Map<String, dynamic>.from(payload),
      'created_at': operation['created_at'],
      'schema_version': operation['schema_version'],
      'client_id': operation['client_id'],
      'tenant_scope': operation['tenant_scope'],
    };
  }

  static List<Map<String, dynamic>> toWireOperations(
          Iterable<Map<String, dynamic>> operations) =>
      operations.map(toWireOperation).toList(growable: false);
}
