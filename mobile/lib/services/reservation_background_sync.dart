import 'dart:io';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/widgets.dart';
import 'package:workmanager/workmanager.dart';

import 'api_client.dart';
import 'catalog_offline_store.dart';
import 'client_session.dart';
import 'reservation_offline_store.dart';
import 'session_store.dart';
import 'offline_sync_protocol.dart';

const _reservationSyncTask = 'fashionstore.reservation_outbox_sync';
const _reservationSyncWorkName = 'fashionstore-reservation-outbox-sync';
typedef BackgroundInternetCheck = Future<bool> Function(String server);
typedef LimitedBatchSender = Future<dynamic> Function(String server,
    String limitedCredential, List<Map<String, dynamic>> operations);

class ReservationBackgroundSyncRunner {
  ReservationBackgroundSyncRunner({
    CatalogOfflineStore? outbox,
    ReservationOfflineStore? reservations,
    DeviceSyncCredentialStore? credentials,
    BackgroundInternetCheck? internetCheck,
    LimitedBatchSender? batchSender,
  })  : _outbox = outbox ?? CatalogOfflineStore(),
        _reservations = reservations ?? ReservationOfflineStore(),
        _credentials = credentials ?? SecureDeviceSyncCredentialStore(),
        _internetCheck = internetCheck ?? _checkInternet,
        _batchSender = batchSender ?? _sendBatch;

  final CatalogOfflineStore _outbox;
  final ReservationOfflineStore _reservations;
  final DeviceSyncCredentialStore _credentials;
  final BackgroundInternetCheck _internetCheck;
  final LimitedBatchSender _batchSender;

  Future<bool> run() async {
    try {
      final savedCredentials = await _credentials.readAll();
      for (final value in savedCredentials.values) {
        if (value is! Map) continue;
        final credential = Map<String, dynamic>.from(value);
        final organizationId = credential['organization_id'];
        final userId = credential['user_id'];
        final clientId = credential['client_id'];
        final token = credential['sync_token'];
        final server = credential['server'];
        final expiresAt = DateTime.tryParse('${credential['expires_at']}');
        if (organizationId is! int ||
            userId is! int ||
            clientId is! String ||
            token is! String ||
            token.isEmpty ||
            server is! String ||
            expiresAt == null ||
            !expiresAt.isAfter(DateTime.now())) {
          continue;
        }

        final normalizedServer = ClientSession.validateServer(server);
        if (!await _internetCheck(normalizedServer)) return false;
        final scope = 'org:$organizationId';
        await _outbox.recoverSending(scope, ownerUserId: userId);
        final operations = await _outbox.claimPending(
          scope,
          ownerUserId: userId,
          operationTypes: clientOutboxOperationTypes,
        );
        if (operations.isEmpty) {
          if (await _outbox.hasSending(scope, ownerUserId: userId))
            return false;
          continue;
        }

        final authorized = operations.where((operation) {
          final payload = operation['payload'];
          return operation['client_id'] == clientId &&
              operation['tenant_scope'] == scope &&
              payload is Map &&
              payload['id_usuario'] == userId;
        }).toList();
        for (final operation
            in operations.where((item) => !authorized.contains(item))) {
          await _outbox.updateOutbox(
            operation['operation_uuid'] as String,
            'RECHAZADA',
            category: 'NO_AUTORIZADA',
            message:
                'La operación no corresponde a la credencial de este usuario, organización o dispositivo.',
          );
        }
        if (authorized.isEmpty) continue;

        dynamic response;
        try {
          response = await _batchSender(normalizedServer, token, authorized);
        } on ApiException catch (error) {
          final data = error.data;
          if (data is Map && data['results'] is List) {
            response = data;
          } else {
            final retryable = error.status == 0 || error.status >= 500;
            await _markBatch(
                authorized,
                retryable ? 'ERROR_REINTENTABLE' : 'RECHAZADA',
                retryable ? 'TEMPORAL' : 'NO_AUTORIZADA',
                error.message);
            if (retryable) return false;
            continue;
          }
        } catch (error) {
          await _markBatch(
              authorized, 'ERROR_REINTENTABLE', 'TEMPORAL', '$error');
          return false;
        }

        if (response is! Map || response['results'] is! List) {
          await _markBatch(authorized, 'ERROR_REINTENTABLE', 'TEMPORAL',
              'El servidor devolvió una respuesta de sincronización inválida.');
          return false;
        }
        final retry =
            await _applyResults(authorized, response['results'] as List);
        await _outbox.setLastSync(scope);
        if (retry) return false;
      }
      return true;
    } finally {
      await _outbox.close();
      await _reservations.close();
    }
  }

  Future<bool> _applyResults(
      List<Map<String, dynamic>> operations, List results) async {
    final byId = {
      for (final result in results.whereType<Map>())
        '${result['operation_uuid']}': Map<String, dynamic>.from(result),
    };
    var retry = false;
    for (final operation in operations) {
      final id = operation['operation_uuid'] as String;
      final result = byId[id];
      final status = result?['status'];
      final validStatus =
          {'SINCRONIZADA', 'RECHAZADA', 'ERROR_REINTENTABLE'}.contains(status);
      final savedStatus = validStatus ? status as String : 'ERROR_REINTENTABLE';
      await _outbox.updateOutbox(
        id,
        savedStatus,
        category: result?['category'] as String? ??
            (result == null ? 'TEMPORAL' : null),
        message: result?['message'] as String? ??
            (result == null
                ? 'El servidor omitió el resultado de la operación.'
                : null),
      );
      if (operation['operation_type'] == 'reserva.crear' ||
          operation['operation_type'] == 'reserva.cancelar') {
        await _reservations.reconcile(
          operation,
          result?['result'] is Map
              ? Map<String, dynamic>.from(result!['result'] as Map)
              : null,
          savedStatus,
          result?['message'] as String?,
        );
      } else if (operation['operation_type'] == 'venta.crear') {
        await _reservations.reconcileSale(
          operation,
          result?['result'] is Map
              ? Map<String, dynamic>.from(result!['result'] as Map)
              : null,
          savedStatus,
          result?['message'] as String?,
        );
      } else if (operation['operation_type'] == 'cambio.solicitar' ||
          operation['operation_type'] == 'cambio.registrar_offline') {
        await _reservations.reconcileExchange(
          operation,
          result?['result'] is Map
              ? Map<String, dynamic>.from(result!['result'] as Map)
              : null,
          savedStatus,
          result?['message'] as String?,
        );
      } else if (operation['operation_type'] == 'pago.solicitar') {
        // A queued request creates a pending payment record. Card/QR provider
        // authorization still requires the foreground client and provider UI.
        await _reservations.reconcilePayment(
          operation,
          result?['result'] is Map
              ? Map<String, dynamic>.from(result!['result'] as Map)
              : null,
          savedStatus,
          result?['message'] as String?,
        );
      }
      retry = retry || savedStatus == 'ERROR_REINTENTABLE';
    }
    return retry;
  }

  Future<void> _markBatch(List<Map<String, dynamic>> operations, String status,
      String category, String message) async {
    for (final operation in operations) {
      final id = operation['operation_uuid'] as String;
      await _outbox.updateOutbox(id, status,
          category: category, message: message);
      if (operation['operation_type'] == 'venta.crear') {
        await _reservations.reconcileSale(operation, null, status, message);
      } else if ((operation['operation_type'] as String? ?? '')
          .startsWith('cambio.')) {
        await _reservations.reconcileExchange(operation, null, status, message);
      } else if ((operation['operation_type'] as String? ?? '')
          .startsWith('reserva.')) {
        await _reservations.reconcile(operation, null, status, message);
      } else if (operation['operation_type'] == 'pago.solicitar') {
        await _reservations.reconcilePayment(operation, null, status, message);
      }
    }
  }

  static Future<bool> _checkInternet(String server) async {
    final connectivity = await Connectivity().checkConnectivity();
    if (!connectivity.any((result) => result != ConnectivityResult.none))
      return false;
    final api = ApiClient(timeout: const Duration(seconds: 5))
      ..baseUrl = server;
    try {
      final response = await api.request('GET', '/health');
      return response is Map && response['status'] == 'ok';
    } catch (_) {
      return false;
    } finally {
      api.dispose();
    }
  }

  static Future<dynamic> _sendBatch(String server, String credential,
      List<Map<String, dynamic>> operations) async {
    final api = ApiClient()
      ..baseUrl = server
      ..token = credential;
    try {
      return await api.request('POST', '/api/sync/batch',
          {'operations': OfflineSyncProtocol.toWireOperations(operations)});
    } finally {
      api.dispose();
    }
  }
}

class ReservationBackgroundSync {
  static bool _initialized = false;

  static Future<void> initialize() async {
    if (_initialized || !Platform.isAndroid) return;
    try {
      await Workmanager().initialize(reservationSyncCallbackDispatcher);
      _initialized = true;
    } catch (_) {
      // Widget tests and unsupported hosts do not register the Android plugin.
    }
  }

  static Future<void> schedule() async {
    if (!Platform.isAndroid) return;
    try {
      if (!_initialized) await initialize();
      if (!_initialized) return;
      await Workmanager().registerOneOffTask(
        _reservationSyncWorkName,
        _reservationSyncTask,
        constraints: Constraints(networkType: NetworkType.connected),
        existingWorkPolicy: ExistingWorkPolicy.keep,
        backoffPolicy: BackoffPolicy.exponential,
        backoffPolicyDelay: const Duration(seconds: 30),
      );
    } catch (_) {
      // The persistent Outbox remains authoritative if scheduling is unavailable.
    }
  }
}

@pragma('vm:entry-point')
void reservationSyncCallbackDispatcher() {
  Workmanager().executeTask((task, inputData) async {
    if (task != _reservationSyncTask) return true;
    WidgetsFlutterBinding.ensureInitialized();
    try {
      return await ReservationBackgroundSyncRunner().run();
    } catch (_) {
      return false;
    }
  });
}
