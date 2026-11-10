import 'dart:convert';
import 'dart:async';
import 'dart:io';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter_stripe/flutter_stripe.dart'
    show FailureCode, StripeException;
import 'package:image_picker/image_picker.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../core/config/api_config.dart';
import '../services/api_client.dart';
import '../services/client_repository.dart';
import '../services/client_session.dart';
import '../services/session_store.dart';
import '../services/tenant_preference_keys.dart';
import '../services/catalog_offline_store.dart';
import '../services/reservation_offline_store.dart';
import '../services/reservation_background_sync.dart';
import '../services/stripe_payment_sheet_service.dart';
import '../services/offline_sync_protocol.dart';

class ClientHome extends StatefulWidget {
  const ClientHome(
      {super.key,
      this.repository,
      this.sessionStore,
      this.catalogStore,
      this.privateCacheStore,
      this.reservationStore,
      this.stripePaymentSheet});
  final ClientRepository? repository;
  final SessionStore? sessionStore;
  final CatalogOfflineStore? catalogStore;
  final ClientPrivateCacheStore? privateCacheStore;
  final ReservationOfflineStore? reservationStore;
  final StripePaymentSheetService? stripePaymentSheet;
  @override
  State<ClientHome> createState() => _ClientHomeState();
}

/// QR visual de demostración. No representa un cobro ni contiene credenciales.
class _FakeQrPainter extends CustomPainter {
  _FakeQrPainter(this.value);
  final String value;

  @override
  void paint(Canvas canvas, Size size) {
    final modules = 29;
    final cell = size.width / modules;
    final random = Random(value.hashCode);
    final paint = Paint()..color = Colors.black;
    canvas.drawRect(Offset.zero & size, Paint()..color = Colors.white);
    bool finder(int x, int y) =>
        (x < 7 && y < 7) ||
        (x >= modules - 7 && y < 7) ||
        (x < 7 && y >= modules - 7);
    for (var y = 0; y < modules; y++) {
      for (var x = 0; x < modules; x++) {
        var dark = random.nextBool();
        if (finder(x, y)) {
          final ox = x < 7
              ? 0
              : x >= modules - 7
                  ? modules - 7
                  : 0;
          final oy = y < 7
              ? 0
              : y >= modules - 7
                  ? modules - 7
                  : 0;
          final dx = x - ox;
          final dy = y - oy;
          dark = dx == 0 ||
              dx == 6 ||
              dy == 0 ||
              dy == 6 ||
              (dx >= 2 && dx <= 4 && dy >= 2 && dy <= 4);
        }
        if (dark) {
          canvas.drawRect(
              Rect.fromLTWH(x * cell, y * cell, cell + .3, cell + .3), paint);
        }
      }
    }
  }

  @override
  bool shouldRepaint(covariant _FakeQrPainter oldDelegate) =>
      oldDelegate.value != value;
}

class _ClientHomeState extends State<ClientHome> {
  late final ClientRepository repository;
  late final ClientSession session;
  final email = TextEditingController();
  final password = TextEditingController();
  final firstName = TextEditingController();
  final lastName = TextEditingController();
  final phone = TextEditingController();
  final search = TextEditingController();
  final size = TextEditingController();
  final color = TextEditingController();
  final category = TextEditingController();
  final maxPrice = TextEditingController();
  final resetToken = TextEditingController();
  final fashionAssistant = TextEditingController();
  final cardNumber = TextEditingController();
  final cardHolder = TextEditingController();
  final cardExpiry = TextEditingController();
  final cardCvv = TextEditingController();
  final cashReceived = TextEditingController();
  late final TextEditingController server;
  final organizationSlug = TextEditingController();
  String publicOrganizationSlug = '';
  bool browsingPublicCatalog = false;
  bool busy = false;
  bool register = false;
  bool failed = false;
  String page = 'Catálogo';
  String message = '';
  String assistantStatus = 'Esperando consulta';
  String assistantReply = '';
  String preferredSize = '';
  final Set<String> preferredColors = <String>{};
  final Set<String> preferredGarments = <String>{};
  String preferredStyle = '';
  final Map<String, dynamic> localStylePreferences = <String, dynamic>{};
  final priceMinimum = TextEditingController();
  final priceMaximum = TextEditingController();
  List<Json> personalizedRows = [];
  List<Json> exchangeEligible = [];
  List<Json> exchangeRows = [];
  final Map<int, Json> exchangeOptions = {};
  final Map<int, int?> exchangeVariantChoice = {};
  final Map<int, int?> exchangeBranchChoice = {};
  final Map<int, String> exchangeOptionsUpdated = {};
  final exchangeReason = TextEditingController();
  List<Json> rows = [];
  List<Json> availability = [];
  List<Json> fittingAvailability = [];
  Json cart = {};
  Json? product;
  Json? fitting;
  Json? selectedOrder;
  Json? paymentInfo;
  int? variantId;
  int? inventoryId;
  int quantity = 1;
  String paymentMethod = 'QR';
  final Map<int, String> orderQrTokens = {};
  String profileEmail = '';
  Json? loyaltySnapshot;
  double garmentScale = 1;
  double garmentOffset = 0;
  final imagePicker = ImagePicker();
  XFile? tryOnPhoto;
  Json? tryOnResult;
  int? tryOnProductId;
  String? tryOnProductName;
  bool _wasSignedIn = false;
  SharedPreferences? _localStore;
  late final CatalogOfflineStore _catalogStore;
  late final ClientPrivateCacheStore _privateCacheStore;
  late final ReservationOfflineStore _reservationStore =
      widget.reservationStore ?? ReservationOfflineStore();
  late final StripePaymentSheetService _stripePaymentSheet =
      widget.stripePaymentSheet ?? StripePaymentSheetService();
  final SecureDeviceSyncCredentialStore _deviceCredentialStore =
      SecureDeviceSyncCredentialStore();
  Map<String, dynamic> _deviceCredentials = {};
  bool reservationsOfflineMode = false;
  bool offlineMode = false;
  DateTime? catalogSyncedAt;
  StreamSubscription<List<ConnectivityResult>>? _connectivitySubscription;
  bool _catalogRefreshInProgress = false;
  bool _outboxSyncInProgress = false;
  bool _restoring = true;
  bool _salesOffline = false;
  bool _networkAvailable = true;
  DateTime? _lastInternetProbeAt;
  bool? _lastInternetProbeResult;
  DateTime? _lastConnectivitySyncAt;
  Future<bool>? _internetProbe;
  String outboxClientId = '';
  List<Map<String, dynamic>> outboxRows = [];
  int? outboxLastSync;

  @override
  void initState() {
    super.initState();
    repository = widget.repository ?? ClientRepository(ApiClient());
    _catalogStore = widget.catalogStore ?? CatalogOfflineStore();
    _privateCacheStore =
        widget.privateCacheStore ?? SecureClientPrivateCacheStore();
    server = TextEditingController(text: repository.api.baseUrl);
    _resetDemoCard();
    session = ClientSession(
        repository, widget.sessionStore ?? const SecureSessionStore());
    session.addListener(sessionChanged);
    _connectivitySubscription =
        Connectivity().onConnectivityChanged.listen((results) {
      _networkAvailable =
          results.any((result) => result != ConnectivityResult.none);
      if (!_networkAvailable) {
        _lastInternetProbeAt = null;
        _lastInternetProbeResult = null;
        _lastConnectivitySyncAt = null;
      }
      if (mounted) setState(() {});
      if (_networkAvailable && !_restoring) {
        unawaited(_handleConnectivityAvailable());
      }
    });
    restore();
  }

  Future<void> restore() async {
    await session.restore();
    _deviceCredentials = await _deviceCredentialStore.readAll();
    await _restoreLocalPreferences();
    if (!mounted) return;
    await _refreshOutboxState();
    server.text = repository.api.baseUrl;
    if (session.signedIn) {
      await run(load);
      await _refreshOutboxState();
    }
    unawaited(_scheduleBackgroundSyncIfPending());
    if (session.signedIn) {
      await _catalogStore.recoverSending('org:${session.organizationId}');
    }
    await _syncOutbox();
    _restoring = false;
  }

  Future<void> _restoreLocalPreferences() async {
    try {
      _localStore = await SharedPreferences.getInstance();
      outboxClientId =
          _localStore!.getString('fashion_store_outbox_client_id') ?? '';
      if (outboxClientId.isEmpty) {
        final random = Random.secure();
        outboxClientId = List<int>.generate(16, (_) => random.nextInt(256))
            .map((value) => value.toRadixString(16).padLeft(2, '0'))
            .join();
        await _localStore!
            .setString('fashion_store_outbox_client_id', outboxClientId);
      }
      publicOrganizationSlug =
          _localStore!.getString('public_organization_slug') ?? '';
      organizationSlug.text = publicOrganizationSlug;
      preferredSize = _localStore!.getString(_styleKey('size')) ?? '';
      preferredColors
        ..clear()
        ..addAll(_localStore!.getStringList(_styleKey('colors')) ??
            const <String>[]);
      preferredGarments
        ..clear()
        ..addAll(_localStore!.getStringList(_styleKey('garments')) ??
            const <String>[]);
      preferredStyle = _localStore!.getString(_styleKey('preferred')) ?? '';
      priceMinimum.text = _localStore!.getString(_styleKey('price_min')) ?? '';
      priceMaximum.text = _localStore!.getString(_styleKey('price_max')) ?? '';
      localStylePreferences
        ..['talla'] = preferredSize
        ..['colores'] = List<String>.from(preferredColors)
        ..['prendas'] = List<String>.from(preferredGarments)
        ..['estilo'] = preferredStyle
        ..['precio_minimo'] = priceMinimum.text
        ..['precio_maximo'] = priceMaximum.text;
    } catch (_) {
      // La app sigue funcionando aunque el almacenamiento local no esté disponible.
    }
  }

  String _styleKey(String name) {
    return TenantPreferenceKeys.forContext(
      name: name,
      organizationId: session.organizationId,
      publicSlug: publicOrganizationSlug,
    );
  }

  Future<void> selectPublicOrganization() async {
    final slug = organizationSlug.text.trim().toLowerCase();
    if (!RegExp(r'^[a-z0-9]+(?:-[a-z0-9]+)*$').hasMatch(slug)) {
      throw ApiException(0, 'Ingresa el slug de una tienda válido.');
    }
    _localStore ??= await SharedPreferences.getInstance();
    await _localStore!.setString('public_organization_slug', slug);
    publicOrganizationSlug = slug;
    browsingPublicCatalog = true;
    page = 'Catálogo';
    rows = [];
    await _restoreLocalPreferences();
    await load();
  }

  Future<List<Json>> _catalogRequest(Map<String, String> filters) => repository
      .catalog(filters, session.signedIn ? null : publicOrganizationSlug);

  String? get _catalogScope {
    if (session.signedIn)
      return session.organizationId == null
          ? null
          : 'org:${session.organizationId}';
    return publicOrganizationSlug.isEmpty
        ? null
        : 'slug:$publicOrganizationSlug';
  }

  String? get _outboxScope => session.signedIn && session.organizationId != null
      ? 'org:${session.organizationId}'
      : null;

  Future<void> _refreshOutboxState() async {
    final scope = _outboxScope;
    final owner = session.userId;
    if (scope == null) {
      outboxRows = [];
      outboxLastSync = null;
    } else {
      outboxRows = owner == null
          ? []
          : await _catalogStore.listOutbox(scope, ownerUserId: owner);
      outboxLastSync = await _catalogStore.getLastSync(scope);
    }
    if (mounted) setState(() {});
  }

  Future<void> _scheduleBackgroundSyncIfPending() async {
    final scopes = <({String scope, int userId})>{};
    if (session.organizationId != null && session.userId != null) {
      scopes.add(
          (scope: 'org:${session.organizationId}', userId: session.userId!));
    }
    for (final value in _deviceCredentials.values) {
      if (value is! Map) continue;
      final credential = Map<String, dynamic>.from(value);
      final orgId = credential['organization_id'];
      final userId = credential['user_id'];
      if (orgId is int && userId is int) {
        scopes.add((scope: 'org:$orgId', userId: userId));
      }
    }
    for (final owner in scopes) {
      final operations = await _catalogStore.listOutbox(owner.scope,
          ownerUserId: owner.userId);
      if (operations.any((item) => {
            'PENDIENTE',
            'ERROR_REINTENTABLE',
            'ENVIANDO'
          }.contains(item['status']))) {
        unawaited(ReservationBackgroundSync.schedule());
        return;
      }
    }
  }

  Future<bool> _hasInternetAccess() async {
    if (!_networkAvailable) return false;
    final now = DateTime.now();
    if (_internetProbe != null) return _internetProbe!;
    if (_lastInternetProbeAt != null &&
        now.difference(_lastInternetProbeAt!) < const Duration(seconds: 20)) {
      return _lastInternetProbeResult ?? false;
    }
    _lastInternetProbeAt = now;
    final probe = () async {
      try {
        final response = await repository.api
            .request('GET', '/health')
            .timeout(const Duration(seconds: 5));
        // A successful HTTP response is enough to prove reachability; health
        // endpoints may return different JSON shapes across backend versions.
        return response is Map;
      } catch (_) {
        return false;
      }
    }();
    _internetProbe = probe;
    try {
      _lastInternetProbeResult = await probe;
      return _lastInternetProbeResult!;
    } finally {
      _internetProbe = null;
    }
  }

  Future<void> _handleConnectivityAvailable() async {
    if (!session.signedIn && _deviceCredentials.isEmpty) return;
    final now = DateTime.now();
    if (_lastConnectivitySyncAt != null &&
        now.difference(_lastConnectivitySyncAt!) <
            const Duration(seconds: 20)) {
      return;
    }
    _lastConnectivitySyncAt = now;
    if (!await _hasInternetAccess()) return;
    if (offlineMode) await _refreshCatalogOnReconnect();
    await _syncOutbox();
    if (page == 'Cambios' && mounted) await _loadExchanges();
  }

  Future<void> _syncOutbox() async {
    if (!session.signedIn && _deviceCredentials.isEmpty) return;
    if (_outboxSyncInProgress) return;
    _outboxSyncInProgress = true;
    final originalToken = repository.api.token;
    final originalServer = repository.api.baseUrl;
    try {
      final network = await Connectivity().checkConnectivity();
      _networkAvailable =
          network.any((result) => result != ConnectivityResult.none);
      if (!_networkAvailable || !await _hasInternetAccess()) return;
      if (session.signedIn &&
          session.organizationId != null &&
          session.userId != null) {
        await _syncOutboxFor(
          scope: 'org:${session.organizationId}',
          userId: session.userId!,
          clientId: outboxClientId,
          token: originalToken!,
          server: originalServer,
        );
      } else {
        _deviceCredentials = await _deviceCredentialStore.readAll();
        for (final value in _deviceCredentials.values) {
          if (value is! Map) continue;
          final credential = Map<String, dynamic>.from(value);
          final expires = DateTime.tryParse('${credential['expires_at']}');
          if (expires == null ||
              !expires.isAfter(DateTime.now()) ||
              credential['sync_token'] is! String) continue;
          final organizationId = credential['organization_id'];
          final userId = credential['user_id'];
          if (organizationId is! int ||
              userId is! int ||
              credential['server'] is! String) continue;
          await _syncOutboxFor(
            scope: 'org:$organizationId',
            userId: userId,
            clientId: credential['client_id'] as String? ?? '',
            token: credential['sync_token'] as String,
            server: credential['server'] as String,
          );
        }
      }
    } finally {
      repository.api.token = session.signedIn ? originalToken : null;
      repository.api.baseUrl = originalServer;
      _outboxSyncInProgress = false;
      await _refreshOutboxState();
      if (mounted &&
          page == 'Pedido' &&
          selectedOrder?['local_operation_uuid'] != null &&
          session.userId != null &&
          _salesScope != null) {
        final savedOrders =
            await _reservationStore.orders(_salesScope!, session.userId!);
        final operationId = selectedOrder!['local_operation_uuid'];
        selectedOrder = savedOrders
                .where((order) => order['local_operation_uuid'] == operationId)
                .firstOrNull ??
            selectedOrder;
        if (mounted) setState(() {});
      }
      if (mounted &&
          page == 'Reservas' &&
          session.signedIn &&
          session.userId != null &&
          session.organizationId != null) {
        final scope = 'org:${session.organizationId}';
        rows = await _reservationStore
            .read(_reservationCacheKey(scope, session.userId!));
        availability = await _reservationStore
            .read(_reservationAvailabilityKey(scope, session.userId!));
        setState(() {});
      }
    }
  }

  Future<void> _syncOutboxFor(
      {required String scope,
      required int userId,
      required String clientId,
      required String token,
      required String server}) async {
    repository.api.baseUrl = ClientSession.validateServer(server);
    repository.api.token = token;
    await _catalogStore.recoverSending(scope, ownerUserId: userId);
    final operations = await _catalogStore.claimPending(
      scope,
      ownerUserId: userId,
      operationTypes: clientOutboxOperationTypes,
    );
    if (operations.isEmpty) return;
    final allowed = operations.where((operation) {
      final payload = operation['payload'] as Map?;
      return operation['client_id'] == clientId &&
          operation['tenant_scope'] == scope &&
          payload?['id_usuario'] == userId;
    }).toList();
    for (final operation
        in operations.where((operation) => !allowed.contains(operation))) {
      await _catalogStore.updateOutbox(
          operation['operation_uuid'] as String, 'RECHAZADA',
          category: 'NO_AUTORIZADA',
          message:
              'La operación no corresponde a este usuario, organización o dispositivo.');
    }
    if (allowed.isEmpty) return;
    try {
      final response = Map<String, dynamic>.from(await repository.api.request(
          'POST',
          '/api/sync/batch',
          {'operations': OfflineSyncProtocol.toWireOperations(allowed)}));
      await _applyOutboxResults(
          allowed, response['results'] as List? ?? const []);
      await _catalogStore.setLastSync(scope);
    } on ApiException catch (error) {
      final data = error.data;
      if (data is Map && data['results'] is List) {
        await _applyOutboxResults(allowed, data['results'] as List);
        await _catalogStore.setLastSync(scope);
      } else {
        final retryable = error.status == 0 || error.status >= 500;
        final status = retryable ? 'ERROR_REINTENTABLE' : 'RECHAZADA';
        for (final operation in allowed) {
          await _catalogStore.updateOutbox(
              operation['operation_uuid'] as String, status,
              category: retryable
                  ? 'TEMPORAL'
                  : error.status == 401 || error.status == 403
                      ? 'NO_AUTORIZADA'
                      : 'DATOS_INVALIDOS',
              message: error.message);
          await _reconcileOutboxOperation(operation, status, error.message);
        }
      }
    } catch (error) {
      for (final operation in allowed) {
        await _catalogStore.updateOutbox(
            operation['operation_uuid'] as String, 'ERROR_REINTENTABLE',
            category: 'TEMPORAL', message: '$error');
        await _reconcileOutboxOperation(
            operation, 'ERROR_REINTENTABLE', '$error');
      }
    }
  }

  Future<void> _reconcileOutboxOperation(
      Json operation, String status, String? message,
      {Json? result}) async {
    final type = operation['operation_type'] as String? ?? '';
    if (type.startsWith('reserva.')) {
      await _reservationStore.reconcile(operation, result, status, message);
    } else if (type == 'venta.crear') {
      await _reservationStore.reconcileSale(operation, result, status, message);
    } else if (type.startsWith('cambio.')) {
      await _reservationStore.reconcileExchange(
          operation, result, status, message);
    } else if (type == 'pago.solicitar') {
      await _reservationStore.reconcilePayment(
          operation, result, status, message);
    }
  }

  Future<void> _applyOutboxResults(List<Json> operations, List results) async {
    final byId = {
      for (final item in results.whereType<Map>())
        '${item['operation_uuid']}': Map<String, dynamic>.from(item)
    };
    for (final operation in operations) {
      final id = operation['operation_uuid'] as String;
      final result = byId[id];
      final status = result?['status'];
      final validStatus =
          {'SINCRONIZADA', 'RECHAZADA', 'ERROR_REINTENTABLE'}.contains(status);
      final savedStatus = validStatus ? status as String : 'ERROR_REINTENTABLE';
      await _catalogStore.updateOutbox(id, savedStatus,
          category: result?['category'] as String? ??
              (result == null ? 'TEMPORAL' : null),
          message: result?['message'] as String? ??
              (result == null
                  ? 'El servidor omitió el resultado de la operación.'
                  : null));
      await _reconcileOutboxOperation(
        operation,
        savedStatus,
        result?['message'] as String? ??
            (result == null ? 'El servidor omitió el resultado.' : null),
        result: result?['result'] is Map
            ? Map<String, dynamic>.from(result!['result'] as Map)
            : null,
      );
    }
  }

  Future<void> _refreshCatalogOnReconnect() async {
    final scope = _catalogScope;
    if (_catalogRefreshInProgress ||
        !mounted ||
        !offlineMode ||
        page != 'Catálogo' ||
        scope == null) return;
    _catalogRefreshInProgress = true;
    try {
      final fresh = await _catalogRequest(const {});
      await _catalogStore.save(scope, fresh);
      if (mounted && page == 'Catálogo' && _catalogScope == scope) {
        setState(() {
          rows = fresh;
          offlineMode = false;
          catalogSyncedAt = DateTime.now();
          message = 'Catálogo actualizado al recuperar la conexión.';
        });
      }
    } catch (_) {
      // Se conserva el catálogo local hasta el siguiente evento de conectividad.
    } finally {
      _catalogRefreshInProgress = false;
    }
  }

  Future<List<Json>> _offlineCatalog(Map<String, String> filters) async {
    final scope = _catalogScope;
    if (scope == null) return [];
    final snapshot = await _catalogStore.read(scope);
    catalogSyncedAt = snapshot.syncedAt;
    final needle = (filters['nombre'] ?? '').trim().toLowerCase();
    final max = double.tryParse(filters['precio_max'] ?? '');
    return snapshot.products.where((item) {
      final variants = (item['variantes'] as List? ?? const [])
          .map((e) => Map<String, dynamic>.from(e as Map));
      final categoryMap =
          Map<String, dynamic>.from(item['categoria'] as Map? ?? const {});
      return (needle.isEmpty ||
              (item['nombre'] as String? ?? '')
                  .toLowerCase()
                  .contains(needle)) &&
          ((filters['categoria'] ?? '').isEmpty ||
              categoryMap['nombre'] == filters['categoria']) &&
          ((filters['talla'] ?? '').isEmpty ||
              variants.any((v) => v['talla'] == filters['talla'])) &&
          ((filters['color'] ?? '').isEmpty ||
              variants.any((v) => v['color'] == filters['color'])) &&
          (max == null ||
              (double.tryParse(item['precio_base']?.toString() ?? '') ?? 0) <=
                  max);
    }).toList();
  }

  void clearClientData() {
    rows = [];
    availability = [];
    fittingAvailability = [];
    cart = {};
    product = null;
    fitting = null;
    tryOnPhoto = null;
    tryOnResult = null;
    tryOnProductId = null;
    tryOnProductName = null;
    selectedOrder = null;
    paymentInfo = null;
    exchangeEligible = [];
    exchangeRows = [];
    exchangeOptions.clear();
    exchangeVariantChoice.clear();
    exchangeBranchChoice.clear();
    exchangeOptionsUpdated.clear();
    exchangeReason.clear();
    for (final c in [cardNumber, cardHolder, cardExpiry, cardCvv]) {
      c.clear();
    }
    fashionAssistant.clear();
    assistantStatus = 'Esperando consulta';
    assistantReply = '';
    preferredSize = '';
    preferredColors.clear();
    preferredGarments.clear();
    preferredStyle = '';
    localStylePreferences.clear();
    priceMinimum.clear();
    priceMaximum.clear();
    personalizedRows = [];
    _resetDemoCard();
    variantId = null;
    inventoryId = null;
    quantity = 1;
    profileEmail = '';
    for (final c in [
      firstName,
      lastName,
      phone,
      search,
      size,
      color,
      category,
      maxPrice,
      password,
      resetToken
    ]) {
      c.clear();
    }
    page = 'Catálogo';
    message = '';
    failed = false;
  }

  void _resetDemoCard() {
    cardNumber.text = '4242 4242 4242 4242';
    cardHolder.text = 'Cliente Demo';
    cardExpiry.text = '12/34';
    cardCvv.text = '123';
  }

  void sessionChanged() {
    if (!mounted) return;
    setState(() {
      if (_wasSignedIn && !session.signedIn) {
        Navigator.of(context).popUntil((route) => route.isFirst);
        clearClientData();
        browsingPublicCatalog = false;
        unawaited(_restoreLocalPreferences());
      }
      _wasSignedIn = session.signedIn;
      if (session.notice != null) message = session.notice!;
    });
  }

  Future<void> run(Future<void> Function() action) async {
    if (busy || !mounted) return;
    setState(() {
      busy = true;
      failed = false;
      message = '';
    });
    try {
      await action();
    } catch (e) {
      if (mounted) {
        setState(() {
          failed = true;
          if (page == 'Recomendaciones') assistantStatus = 'Error de conexión';
          message = e is ApiException
              ? e.message
              : 'No se pudo completar la operación. Intenta nuevamente.';
        });
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Map<String, String> get filterValues => {
        'nombre': search.text,
        'talla': size.text,
        'color': color.text,
        'categoria': category.text,
        'precio_max': maxPrice.text
      };
  Future<void> load() async {
    switch (page) {
      case 'Catálogo':
        if (maxPrice.text.isNotEmpty &&
            (double.tryParse(maxPrice.text) == null ||
                double.parse(maxPrice.text) <= 0)) {
          throw ApiException(
              0, 'El precio máximo debe ser un número mayor a cero.');
        }
        try {
          rows = await _catalogRequest(filterValues);
          offlineMode = false;
          final scope = _catalogScope;
          if (scope != null) {
            await _catalogStore.save(scope, rows);
            catalogSyncedAt = DateTime.now();
          }
        } catch (_) {
          final cached = await _offlineCatalog(filterValues);
          if (cached.isEmpty) rethrow;
          rows = cached;
          offlineMode = true;
        }
      case 'Carrito':
        try {
          final remoteCart = await repository.cart();
          final scope = _salesScope;
          final owner = session.userId;
          final localItems = scope == null || owner == null
              ? <Json>[]
              : await _reservationStore.read(_salesCartKey(scope, owner));
          final remoteItems =
              List<Json>.from(remoteCart['items'] as List? ?? const []);
          final remoteVariants =
              remoteItems.map((item) => item['id_variante']).toSet();
          final pendingOffline = localItems
              .where((item) => item['pending_offline'] == true)
              .toList();
          final uncertainLocal = localItems
              .where((item) => item['server_status_unknown'] == true)
              .where((item) => !remoteVariants.contains(item['id_variante']))
              .map((item) => {
                    ...item,
                    'server_status_unknown': false,
                    'pending_offline': true,
                  });
          final retainedByVariant = <dynamic, Json>{
            for (final item in pendingOffline) item['id_variante']: item,
            for (final item in uncertainLocal) item['id_variante']: item,
          };
          final retainedLocal = retainedByVariant.values.toList();
          if (retainedLocal.isEmpty) {
            cart = remoteCart;
            _salesOffline = false;
          } else {
            final retainedVariants =
                retainedLocal.map((item) => item['id_variante']).toSet();
            cart = _cartFromItems([
              ...remoteItems.where(
                  (item) => !retainedVariants.contains(item['id_variante'])),
              ...retainedLocal,
            ]);
            _salesOffline = true;
          }
          if (scope != null && owner != null)
            await _reservationStore.save(_salesCartKey(scope, owner),
                List<Json>.from(cart['items'] as List? ?? const []));
        } catch (_) {
          final scope = _salesScope;
          final owner = session.userId;
          if (scope == null || owner == null) rethrow;
          final items =
              await _reservationStore.read(_salesCartKey(scope, owner));
          if (items.isEmpty) {
            _salesOffline = true;
            cart = _cartFromItems(const []);
            break;
          }
          _salesOffline = true;
          cart = _cartFromItems(items);
        }
      case 'Pedidos':
        final scope = _salesScope;
        final owner = session.userId;
        if (owner == null) {
          throw ApiException(
              401, 'Inicia sesión nuevamente para consultar tu perfil.');
        }
        final localOrders = scope == null
            ? <Json>[]
            : await _reservationStore.orders(scope, owner);
        try {
          final remote = await repository.orders();
          final remoteIds = remote.map((order) => order['id_pedido']).toSet();
          rows = [
            ...localOrders.where((order) =>
                order['id_pedido'] == null ||
                !remoteIds.contains(order['id_pedido'])),
            ...remote
          ];
        } catch (_) {
          rows = localOrders;
          _salesOffline = true;
        }
      case 'Pedido':
        final localId = selectedOrder!['id_pedido'];
        if (localId is int) {
          selectedOrder = await repository.order(localId);
          paymentInfo = await repository.payment(localId);
        } else {
          paymentInfo = null;
        }
        if (paymentInfo != null) {
          paymentMethod =
              paymentInfo!['metodo_pago'] as String? ?? paymentMethod;
        }
      case 'Reservas':
        await _loadReservations();
      case 'Cambios':
        await _loadExchanges();
      case 'Recomendaciones':
        try {
          personalizedRows = await _loadPersonalizedRecommendations();
        } catch (_) {
          personalizedRows = [];
          message = 'Las recomendaciones personalizadas requieren conexión.';
        }
      case 'Vestidor':
        try {
          rows = await repository.fittingVariants();
          fittingAvailability = await repository.reservationAvailability();
        } catch (_) {
          final cached = await _offlineCatalog(const {});
          rows = cached
              .expand((item) => (item['variantes'] as List? ?? const []))
              .whereType<Map>()
              .map((item) => Map<String, dynamic>.from(item))
              .toList();
          final scope = _salesScope;
          final owner = session.userId;
          fittingAvailability = scope == null || owner == null
              ? []
              : await _reservationStore
                  .read(_reservationAvailabilityKey(scope, owner));
          message =
              'Vista previa disponible sin conexión; la prueba virtual requiere Internet.';
        }
        _filterFittingAvailability();
        if (tryOnProductId == null &&
            !rows.any((r) => r['id_variante'] == variantId)) {
          variantId = null;
          fitting = null;
        }
      case 'Perfil':
        final owner = session.userId;
        if (owner == null) {
          throw ApiException(401, 'Inicia sesión para consultar tu perfil.');
        }
        final profileKey = _privateCacheKey('profile', owner);
        final loyaltyKey = _privateCacheKey('loyalty', owner);
        Map<String, dynamic>? profile;
        if (await _hasInternetAccess()) {
          try {
            profile = await repository.profile();
            await _privateCacheStore.write(profileKey, profile);
            try {
              loyaltySnapshot = await repository.loyalty();
              await _privateCacheStore.write(loyaltyKey, loyaltySnapshot!);
            } catch (_) {
              loyaltySnapshot = await _privateCacheStore.read(loyaltyKey);
            }
          } catch (_) {
            profile = await _privateCacheStore.read(profileKey);
            loyaltySnapshot = await _privateCacheStore.read(loyaltyKey);
          }
        } else {
          profile = await _privateCacheStore.read(profileKey);
          loyaltySnapshot = await _privateCacheStore.read(loyaltyKey);
        }
        if (!mounted) return;
        firstName.text = profile?['nombres']?.toString() ?? '';
        lastName.text = profile?['apellidos']?.toString() ?? '';
        phone.text = profile?['telefono']?.toString() ?? '';
        profileEmail = profile?['correo']?.toString() ?? '';
        if (profile == null) {
          message = 'Perfil sin conexión: se mostrará cuando vuelva Internet.';
        } else if (!await _hasInternetAccess()) {
          message = 'Mostrando el perfil guardado en este dispositivo.';
        }
      case 'Detalle':
        if (product != null) await detail(product!);
    }
  }

  String _reservationCacheKey(String scope, int userId) =>
      'reservations:$scope:$userId';
  String _reservationAvailabilityKey(String scope, int userId) =>
      'availability:$scope:$userId';
  String _privateCacheKey(String section, int userId) =>
      '$section:org:${session.organizationId}:user:$userId';
  String? get _salesScope =>
      session.organizationId == null ? null : 'org:${session.organizationId}';
  String _salesCartKey(String scope, int userId) => 'sales:cart:$scope:$userId';

  Json _cartFromItems(List<Json> items) => {
        'id_carrito': 0,
        'estado': 'ACTIVO',
        'items': items,
        'total': items
            .fold<double>(
                0,
                (sum, item) =>
                    sum +
                    (double.tryParse('${item['precio_unitario']}') ?? 0) *
                        (item['cantidad'] as int? ?? 0))
            .toStringAsFixed(2),
      };

  Future<void> _loadReservations() async {
    final organizationId = session.organizationId;
    final userId = session.userId;
    if (organizationId == null || userId == null)
      throw ApiException(401, 'Inicia sesión para consultar tus reservas.');
    final scope = 'org:$organizationId';
    final reservationKey = _reservationCacheKey(scope, userId);
    final availabilityKey = _reservationAvailabilityKey(scope, userId);
    final network = await Connectivity().checkConnectivity();
    if (network.any((result) => result != ConnectivityResult.none)) {
      try {
        final freshReservations = await repository.reservations();
        final freshAvailability = await repository.reservationAvailability();
        rows = freshReservations;
        availability = freshAvailability;
        await _reservationStore.save(reservationKey, rows);
        await _reservationStore.save(availabilityKey, availability);
        reservationsOfflineMode = false;
      } catch (error) {
        rows = await _reservationStore.read(reservationKey);
        availability = await _reservationStore.read(availabilityKey);
        reservationsOfflineMode = true;
        if (rows.isEmpty && availability.isEmpty) rethrow;
        message =
            'Mostrando reservas y disponibilidad descargadas; el servidor confirma los cambios al sincronizar.';
      }
    } else {
      rows = await _reservationStore.read(reservationKey);
      availability = await _reservationStore.read(availabilityKey);
      reservationsOfflineMode = true;
      if (rows.isEmpty && availability.isEmpty)
        message =
            'No hay reservas ni disponibilidad descargadas para consultar sin conexión.';
    }
    if (!availability.any((item) => item['id_inventario'] == inventoryId))
      inventoryId = null;
  }

  String _exchangeOptionsCacheKey(String scope, int userId, int detailId) =>
      'exchange-options:$scope:$userId:$detailId';

  Future<void> _loadExchanges() async {
    final scope = _salesScope;
    final owner = session.userId;
    if (scope == null || owner == null) {
      exchangeEligible = [];
      exchangeRows = [];
      return;
    }
    final cachedEligible =
        await _reservationStore.read('exchange-eligible:$scope:$owner');
    var optionsAvailable = false;
    try {
      if (!await _hasInternetAccess()) throw ApiException(0, 'Sin conexión');
      exchangeEligible = await repository.eligibleExchangePurchases();
      final remote = await repository.exchanges();
      final local = await _reservationStore.exchanges(scope, owner);
      final remoteIds = remote.map((row) => row['id']).toSet();
      exchangeRows = [
        ...local.where(
            (row) => row['id'] == null || !remoteIds.contains(row['id'])),
        ...remote,
      ];
      await _reservationStore.save(
          'exchange-eligible:$scope:$owner', exchangeEligible);
      await _reservationStore.saveExchanges(scope, owner, exchangeRows);
      for (final purchase in exchangeEligible) {
        final detailId = purchase['id_detalle'] as int;
        try {
          final response = await repository.exchangeOptions(detailId);
          exchangeOptions[detailId] = response;
          await _reservationStore.save(
            _exchangeOptionsCacheKey(scope, owner, detailId),
            [response],
          );
          final variants = (response['variantes'] as List? ?? const [])
              .map((item) => Map<String, dynamic>.from(item as Map))
              .toList();
          final originalId = purchase['id_variante'] as int;
          final chosen = variants
                  .where((item) => item['id_variante'] == originalId)
                  .firstOrNull ??
              (variants.isEmpty ? null : variants.first);
          exchangeVariantChoice[detailId] = chosen?['id_variante'] as int?;
          final stocks =
              (chosen?['stock'] as List? ?? const []).whereType<Map>();
          final stockedBranch = stocks
              .where((item) => (item['disponible'] as num? ?? 0) > 0)
              .firstOrNull;
          final branches = response['sucursales'] as List? ?? const [];
          exchangeBranchChoice[detailId] =
              stockedBranch?['id_sucursal'] as int? ??
                  (branches.isEmpty
                      ? null
                      : (branches.first as Map)['id_sucursal'] as int);
          exchangeOptionsUpdated[detailId] = DateTime.now().toIso8601String();
          optionsAvailable = true;
        } catch (_) {
          final saved = await _reservationStore.read(
            _exchangeOptionsCacheKey(scope, owner, detailId),
          );
          if (saved.isNotEmpty) {
            exchangeOptions[detailId] = saved.first;
            optionsAvailable = true;
          }
        }
      }
      reservationsOfflineMode = false;
    } catch (_) {
      exchangeEligible = cachedEligible;
      exchangeRows = await _reservationStore.exchanges(scope, owner);
      reservationsOfflineMode = true;
      for (final purchase in exchangeEligible) {
        final detailId = purchase['id_detalle'] as int;
        final saved = await _reservationStore.read(
          _exchangeOptionsCacheKey(scope, owner, detailId),
        );
        if (saved.isNotEmpty) {
          exchangeOptions[detailId] = saved.first;
          optionsAvailable = true;
        }
      }
      if (exchangeEligible.isEmpty) {
        message =
            'No hay compras elegibles descargadas para solicitar cambios offline.';
      }
    }
    if (reservationsOfflineMode &&
        exchangeEligible.isNotEmpty &&
        !optionsAvailable) {
      message =
          'Las compras están guardadas; descarga las variantes y sucursales con conexión para elegir una alternativa offline.';
    }
  }

  Future<void> _requestExchange(int detailId) async {
    final owner = session.userId;
    final organizationId = session.organizationId;
    if (owner == null || organizationId == null || outboxClientId.isEmpty) {
      throw ApiException(401, 'Inicia sesión para solicitar un cambio.');
    }
    final replacement = exchangeVariantChoice[detailId];
    final branch = exchangeBranchChoice[detailId];
    if (replacement == null || branch == null) {
      throw ApiException(0, 'Selecciona una variante y sucursal descargadas.');
    }
    final reason = exchangeReason.text.trim().isEmpty
        ? 'Cambio de talla, modelo o color solicitado por el cliente'
        : exchangeReason.text.trim();
    final payload = {
      'id_usuario': owner,
      'id_detalle': detailId,
      'id_sucursal': branch,
      'id_variante_sustituta': replacement,
      'motivo': reason,
    };
    if (await _hasInternetAccess()) {
      final created = await repository.requestExchange(payload);
      exchangeRows = [
        created,
        ...exchangeRows.where((row) => row['id'] != created['id'])
      ];
      await _reservationStore.saveExchanges(
          'org:$organizationId', owner, exchangeRows);
      message =
          'Solicitud de cambio registrada. La sucursal debe inspeccionar la prenda.';
    } else {
      final operationId = await _catalogStore.enqueueOperation(
        tenantScope: 'org:$organizationId',
        ownerUserId: owner,
        operationType: 'cambio.solicitar',
        payload: payload,
        clientId: outboxClientId,
      );
      final option = exchangeOptions[detailId];
      final variant = (option?['variantes'] as List? ?? const [])
          .whereType<Map>()
          .where((item) => item['id_variante'] == replacement)
          .firstOrNull;
      final local = {
        ...payload,
        'id': null,
        'original_detail_id': detailId,
        'original_order_id': exchangeEligible
            .where((row) => row['id_detalle'] == detailId)
            .firstOrNull?['id_pedido'],
        'original_product': exchangeEligible
            .where((row) => row['id_detalle'] == detailId)
            .firstOrNull?['producto'],
        'replacement_product': variant?['producto'],
        'replacement_size': variant?['talla'],
        'replacement_color': variant?['color'],
        'branch_id': branch,
        'state': 'SOLICITUD_LOCAL_PENDIENTE',
        'sync_status': 'PENDIENTE',
        'local_operation_uuid': operationId,
      };
      exchangeRows = [local, ...exchangeRows];
      await _reservationStore.saveExchanges(
          'org:$organizationId', owner, exchangeRows);
      await ReservationBackgroundSync.schedule();
      message = 'Solicitud guardada offline. Se enviará al recuperar conexión.';
      if (await _hasInternetAccess()) await _syncOutbox();
    }
    await _refreshOutboxState();
  }

  Future<void> _queueReservation(int inventory, int count) async {
    final organizationId = session.organizationId;
    final userId = session.userId;
    if (organizationId == null || userId == null || outboxClientId.isEmpty)
      throw ApiException(401, 'Inicia sesión para reservar.');
    final scope = 'org:$organizationId';
    final inventoryRow = availability
        .where((item) => item['id_inventario'] == inventory)
        .firstOrNull;
    if (inventoryRow == null)
      throw ApiException(
          0, 'Selecciona una sucursal guardada en este dispositivo.');
    final operationId = await _catalogStore.enqueueOperation(
      tenantScope: scope,
      ownerUserId: userId,
      operationType: 'reserva.crear',
      payload: {
        'id_inventario': inventory,
        'cantidad': count,
        'id_usuario': userId
      },
      clientId: outboxClientId,
    );
    rows.insert(0, {
      ...inventoryRow,
      'id_reserva': 0,
      'cantidad': count,
      'estado': 'PENDIENTE',
      'local_operation_uuid': operationId,
      'sync_status': 'PENDIENTE',
    });
    inventoryRow['disponible'] =
        ((inventoryRow['disponible'] as int) - count).clamp(0, 1 << 31);
    await _reservationStore.save(_reservationCacheKey(scope, userId), rows);
    await _reservationStore.save(
        _reservationAvailabilityKey(scope, userId), availability);
    await ReservationBackgroundSync.schedule();
    await _syncOutbox();
    rows = await _reservationStore.read(_reservationCacheKey(scope, userId));
    final local = rows
        .where((item) => item['local_operation_uuid'] == operationId)
        .firstOrNull;
    message = local?['sync_status'] == 'SINCRONIZADA'
        ? 'Tu reserva ha sido confirmada'
        : local?['sync_status'] == 'RECHAZADA'
            ? '${local?['sync_message'] ?? 'Reserva rechazada por el servidor.'}. Se recuperó la disponibilidad provisional.'
            : 'Reserva registrada. Esperando confirmación del servidor';
  }

  Future<void> _cancelReservation(Json reservation) async {
    final organizationId = session.organizationId;
    final userId = session.userId;
    if (organizationId == null || userId == null)
      throw ApiException(401, 'Inicia sesión para cancelar.');
    final scope = 'org:$organizationId';
    final reservationKey = _reservationCacheKey(scope, userId);
    final availabilityKey = _reservationAvailabilityKey(scope, userId);
    final localOperation = reservation['local_operation_uuid'] as String?;
    if (localOperation != null && reservation['id_reserva'] == 0) {
      final pending = (await _catalogStore.listOutbox(scope,
              ownerUserId: userId))
          .where((operation) => operation['operation_uuid'] == localOperation)
          .firstOrNull;
      if (pending == null ||
          !{'PENDIENTE', 'ERROR_REINTENTABLE'}.contains(pending['status'])) {
        throw ApiException(
            409, 'Espera la respuesta del servidor antes de cancelar.');
      }
      if (!await _catalogStore.deleteOutbox(localOperation)) {
        throw ApiException(
            409, 'La reserva ya se está enviando; espera su confirmación.');
      }
      rows.removeWhere(
          (item) => item['local_operation_uuid'] == localOperation);
      final cached = await _reservationStore.read(availabilityKey);
      final inv = cached
          .where(
              (item) => item['id_inventario'] == reservation['id_inventario'])
          .firstOrNull;
      if (inv != null)
        inv['disponible'] =
            (inv['disponible'] as int) + (reservation['cantidad'] as int);
      availability = cached;
      await _reservationStore.save(reservationKey, rows);
      await _reservationStore.save(availabilityKey, availability);
      message = 'Reserva local cancelada antes del envío.';
      return;
    }
    final operationId = await _catalogStore.enqueueOperation(
      tenantScope: scope,
      ownerUserId: userId,
      operationType: 'reserva.cancelar',
      payload: {
        'id_reserva': reservation['id_reserva'],
        'id_usuario': userId,
        'id_inventario': reservation['id_inventario'],
        'cantidad': reservation['cantidad'],
        'estado_anterior': reservation['estado'],
      },
      clientId: outboxClientId,
    );
    reservation['estado'] = 'CANCELACION_PENDIENTE';
    reservation['sync_status'] = 'PENDIENTE';
    reservation['local_cancel_operation_uuid'] = operationId;
    final cached = await _reservationStore.read(availabilityKey);
    final inv = cached
        .where((item) => item['id_inventario'] == reservation['id_inventario'])
        .firstOrNull;
    if (inv != null)
      inv['disponible'] =
          (inv['disponible'] as int) + (reservation['cantidad'] as int);
    availability = cached;
    await _reservationStore.save(reservationKey, rows);
    await _reservationStore.save(availabilityKey, availability);
    await ReservationBackgroundSync.schedule();
    await _syncOutbox();
    rows = await _reservationStore.read(reservationKey);
    final saved = rows
        .where((item) => item['id_reserva'] == reservation['id_reserva'])
        .firstOrNull;
    message = saved?['estado'] == 'CANCELADA'
        ? 'Tu reserva ha sido cancelada'
        : saved?['sync_status'] == 'RECHAZADA'
            ? '${saved?['sync_message'] ?? 'No se pudo cancelar la reserva.'} Se restauró el inventario provisional.'
            : 'Cancelación registrada. Esperando confirmación del servidor';
  }

  Future<void> go(String destination) async {
    if (busy) return;
    if (!session.signedIn &&
        destination != 'Catálogo' &&
        destination != 'Detalle') {
      setState(() => message = 'Inicia sesión en esta tienda para continuar.');
      return;
    }
    setState(() {
      page = destination;
      rows = [];
      availability = [];
      product = null;
      fitting = null;
      tryOnPhoto = null;
      tryOnResult = null;
      tryOnProductId = null;
      tryOnProductName = null;
      selectedOrder = null;
      paymentInfo = null;
      variantId = null;
      inventoryId = null;
      quantity = 1;
      if (destination == 'Recomendaciones') {
        assistantStatus = 'Esperando consulta';
        assistantReply = '';
        rows = [];
      }
    });
    await run(load);
  }

  Future<void> authenticate() async {
    if (!email.text.trim().contains('@') || password.text.isEmpty) {
      throw ApiException(0, 'Ingresa un correo válido y tu contraseña.');
    }
    repository.api.baseUrl = ClientSession.validateServer(server.text);
    if (register) {
      final selectedSlug = organizationSlug.text.trim().toLowerCase();
      if (!RegExp(r'^[a-z0-9]+(?:-[a-z0-9]+)*$').hasMatch(selectedSlug)) {
        throw ApiException(
            0, 'Selecciona la tienda antes de crear una cuenta.');
      }
      _localStore ??= await SharedPreferences.getInstance();
      await _localStore!.setString('public_organization_slug', selectedSlug);
      publicOrganizationSlug = selectedSlug;
      if (firstName.text.trim().isEmpty ||
          lastName.text.trim().isEmpty ||
          password.text.length < 8) {
        throw ApiException(0,
            'Completa nombres, apellidos y una contraseña de al menos 8 caracteres.');
      }
      await repository.register({
        'nombres': firstName.text.trim(),
        'apellidos': lastName.text.trim(),
        'correo': email.text.trim(),
        'password': password.text
      }, organizationSlug: selectedSlug);
      register = false;
    }
    await session.login(server.text, email.text, password.text);
    if (!mounted) return;
    await _restoreLocalPreferences();
    await _issueDeviceSyncCredential();
    browsingPublicCatalog = false;
    password.clear();
    page = 'Catálogo';
    rows = [];
    await load();
    await _refreshOutboxState();
    await _syncOutbox();
  }

  Future<void> logout() async {
    try {
      await session.logout();
    } on ApiException {
      message =
          'Sesión cerrada en este dispositivo. No fue posible contactar al servidor.';
    }
    await _syncOutbox();
    await _restoreLocalPreferences();
  }

  Future<void> _issueDeviceSyncCredential() async {
    final userId = session.userId;
    final organizationId = session.organizationId;
    if (userId == null ||
        organizationId == null ||
        repository.api.token == null ||
        outboxClientId.isEmpty) return;
    try {
      final response =
          await repository.issueDeviceSyncCredential(outboxClientId);
      final credential = <String, dynamic>{
        ...response,
        'server': repository.api.baseUrl,
        'organization_id': organizationId,
        'user_id': userId,
        'client_id': outboxClientId,
      };
      await _deviceCredentialStore.writeFor(userId, organizationId, credential);
      _deviceCredentials = await _deviceCredentialStore.readAll();
      await _scheduleBackgroundSyncIfPending();
    } catch (_) {
      // El login y las reservas online no dependen de que la credencial limitada esté disponible.
    }
  }

  Future<void> detail(Json row) async {
    if (offlineMode || !await _hasInternetAccess()) {
      offlineMode = true;
      product = {...row, 'nombre_producto': row['nombre']};
      final scope = _salesScope;
      final owner = session.userId;
      availability = scope == null || owner == null
          ? []
          : await _reservationStore
              .read(_reservationAvailabilityKey(scope, owner));
      variantId = null;
      quantity = 1;
      page = 'Detalle';
      return;
    }
    final slug = session.signedIn ? null : publicOrganizationSlug;
    final result = await repository.variants(row['id_producto'] as int,
        organizationSlug: slug);
    final stock = await repository.availability(row['id_producto'] as int,
        organizationSlug: slug);
    if (session.signedIn && session.userId != null) {
      try {
        availability = await repository.reservationAvailability();
        final scope = _salesScope;
        if (scope != null)
          await _reservationStore.save(
              _reservationAvailabilityKey(scope, session.userId!),
              availability);
      } catch (_) {
        availability = [];
      }
    } else {
      availability = (stock['disponibilidad'] as List)
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList();
    }
    product = {...row, ...result};
    variantId = null;
    quantity = 1;
    page = 'Detalle';
  }

  Future<void> add(int id, [int? count]) async {
    if (!session.signedIn) {
      throw ApiException(
          401, 'Inicia sesi\u00f3n en esta tienda para usar el carrito.');
    }
    final scope = _salesScope;
    final owner = session.userId;
    final connected = await _hasInternetAccess();
    final cartKey =
        scope == null || owner == null ? null : _salesCartKey(scope, owner);
    final stockKey = scope == null || owner == null
        ? null
        : _reservationAvailabilityKey(scope, owner);
    final previousCart =
        cartKey == null ? <Json>[] : await _reservationStore.read(cartKey);
    final previousStock =
        stockKey == null ? <Json>[] : await _reservationStore.read(stockKey);
    await _addToLocalCart(id, count ?? quantity, offline: !connected);
    if (!connected) return;

    var serverAcceptedAdd = false;
    try {
      await repository.addItem(id, count ?? quantity);
      serverAcceptedAdd = true;
      cart = await repository.cart();
      _salesOffline = false;
      if (cartKey != null) {
        await _reservationStore.save(
            cartKey, List<Json>.from(cart['items'] as List? ?? const []));
      }
      message = 'Prenda agregada al carrito';
    } on ApiException catch (error) {
      if (error.status != 0) {
        if (cartKey != null)
          await _reservationStore.save(cartKey, previousCart);
        if (stockKey != null)
          await _reservationStore.save(stockKey, previousStock);
        cart = _cartFromItems(previousCart);
        rethrow;
      }
      if (cartKey != null && !serverAcceptedAdd) {
        final localItems = await _reservationStore.read(cartKey);
        for (final item
            in localItems.where((line) => line['id_variante'] == id)) {
          item['server_status_unknown'] = true;
        }
        await _reservationStore.save(cartKey, localItems);
      }
      _salesOffline = true;
      message =
          'Prenda agregada al carrito local. Se validar\u00e1 al recuperar conexi\u00f3n.';
    } catch (_) {
      if (cartKey != null && !serverAcceptedAdd) {
        final localItems = await _reservationStore.read(cartKey);
        for (final item
            in localItems.where((line) => line['id_variante'] == id)) {
          item['server_status_unknown'] = true;
        }
        await _reservationStore.save(cartKey, localItems);
      }
      _salesOffline = true;
      message =
          'Prenda agregada al carrito local. Se validar\u00e1 al recuperar conexi\u00f3n.';
    }
  }

  Future<void> _addToLocalCart(int id, int count,
      {required bool offline}) async {
    final scope = _salesScope;
    final owner = session.userId;
    if (scope == null || owner == null) {
      throw ApiException(
          401, 'La venta offline requiere una sesión de cliente.');
    }
    final selected = (product?['variantes'] as List? ?? const [])
        .where((value) => value['id_variante'] == id)
        .firstOrNull;
    final source = selected == null
        ? rows.where((row) => row['id_variante'] == id).firstOrNull
        : null;
    if (selected == null && source == null) {
      throw ApiException(
          0, 'La variante no está disponible en el catálogo guardado.');
    }
    final cacheKey = _reservationAvailabilityKey(scope, owner);
    final cachedStock = await _reservationStore.read(cacheKey);
    final allocations = <Json>[];
    var remaining = count;
    final stockRows = cachedStock
        .where((item) => item['id_variante'] == id)
        .toList()
      ..sort((a, b) =>
          (a['id_inventario'] as int).compareTo(b['id_inventario'] as int));
    for (final stock in stockRows) {
      if (remaining <= 0) break;
      final available = stock['disponible'] as int? ?? 0;
      final take = available < remaining ? available : remaining;
      if (take > 0) {
        stock['disponible'] = available - take;
        allocations
            .add({'id_inventario': stock['id_inventario'], 'cantidad': take});
        remaining -= take;
      }
    }
    final items = await _reservationStore.read(_salesCartKey(scope, owner));
    final existing =
        items.where((item) => item['id_variante'] == id).firstOrNull;
    final price = product?['precio_base'] ??
        source?['precio_base'] ??
        source?['precio'] ??
        '0.00';
    if (existing == null) {
      items.add({
        'id_detalle': -DateTime.now().microsecondsSinceEpoch,
        'id_variante': id,
        'client_line_id': 'variant-$id',
        'producto': product?['nombre_producto'] ??
            product?['nombre'] ??
            source?['nombre'] ??
            'Prenda',
        'talla': selected?['talla'] ?? source?['talla'],
        'color': selected?['color'] ?? source?['color'],
        'imagen_url': product?['imagen_url'] ?? source?['imagen_url'],
        'cantidad': count,
        'precio_unitario': '$price',
        'offline_allocations': allocations,
        'pending_offline': offline,
      });
    } else {
      existing['cantidad'] = (existing['cantidad'] as int) + count;
      if (offline) existing['pending_offline'] = true;
      existing['offline_allocations'] = [
        ...(existing['offline_allocations'] as List? ?? const []),
        ...allocations
      ];
    }
    await _reservationStore.save(cacheKey, cachedStock);
    await _reservationStore.save(_salesCartKey(scope, owner), items);
    cart = _cartFromItems(items);
    _salesOffline = offline;
    message = remaining == 0
        ? 'Producto agregado al carrito local.'
        : 'Producto agregado con disponibilidad provisional; el servidor confirmará las existencias.';
  }

  Future<void> _changeLocalCartLine(Json item, int newQuantity) async {
    final scope = _salesScope;
    final owner = session.userId;
    if (scope == null || owner == null) return;
    final items = await _reservationStore.read(_salesCartKey(scope, owner));
    final line = items
        .where((value) => value['id_detalle'] == item['id_detalle'])
        .firstOrNull;
    if (line == null) return;
    final oldQuantity = line['cantidad'] as int;
    final delta = newQuantity - oldQuantity;
    final cacheKey = _reservationAvailabilityKey(scope, owner);
    final stock = await _reservationStore.read(cacheKey);
    final variantStock = stock
        .where((value) => value['id_variante'] == line['id_variante'])
        .toList()
      ..sort((a, b) =>
          (a['id_inventario'] as int).compareTo(b['id_inventario'] as int));
    final allocations = List<Json>.from(
        (line['offline_allocations'] as List? ?? const [])
            .map((value) => Map<String, dynamic>.from(value as Map)));
    if (delta > 0) {
      var remaining = delta;
      for (final row in variantStock) {
        if (remaining <= 0) break;
        final available = row['disponible'] as int? ?? 0;
        final take = available < remaining ? available : remaining;
        if (take > 0) {
          row['disponible'] = available - take;
          final allocation = allocations
              .where((value) => value['id_inventario'] == row['id_inventario'])
              .firstOrNull;
          if (allocation == null)
            allocations
                .add({'id_inventario': row['id_inventario'], 'cantidad': take});
          else
            allocation['cantidad'] = (allocation['cantidad'] as int) + take;
          remaining -= take;
        }
      }
    } else if (delta < 0) {
      var remaining = -delta;
      for (final allocation in allocations.reversed.toList()) {
        if (remaining <= 0) break;
        final allocated = allocation['cantidad'] as int;
        final restore = allocated < remaining ? allocated : remaining;
        final inventory = stock
            .where((value) =>
                value['id_inventario'] == allocation['id_inventario'])
            .firstOrNull;
        if (inventory != null)
          inventory['disponible'] = (inventory['disponible'] as int) + restore;
        allocation['cantidad'] = allocated - restore;
        remaining -= restore;
      }
      allocations.removeWhere((value) => value['cantidad'] == 0);
    }
    line['cantidad'] = newQuantity;
    line['offline_allocations'] = allocations;
    await _reservationStore.save(cacheKey, stock);
    await _reservationStore.save(_salesCartKey(scope, owner), items);
    cart = _cartFromItems(items);
  }

  Future<void> _updateCartLine(Json item, int newQuantity) async {
    if (_salesOffline || !await _hasInternetAccess()) {
      _salesOffline = true;
      await _changeLocalCartLine(item, newQuantity);
      return;
    }
    await repository.changeQuantity(item['id_detalle'] as int, newQuantity);
    cart = await repository.cart();
    final scope = _salesScope;
    if (scope != null && session.userId != null) {
      await _reservationStore.save(_salesCartKey(scope, session.userId!),
          List<Json>.from(cart['items'] as List));
    }
  }

  Future<void> _removeCartLine(Json item) async {
    if (!_salesOffline && await _hasInternetAccess()) {
      await repository.removeItem(item['id_detalle'] as int);
      cart = await repository.cart();
      final scope = _salesScope;
      if (scope != null && session.userId != null) {
        await _reservationStore.save(_salesCartKey(scope, session.userId!),
            List<Json>.from(cart['items'] as List));
      }
      return;
    }
    await _changeLocalCartLine(item, 0);
    final scope = _salesScope;
    final owner = session.userId;
    if (scope == null || owner == null) return;
    final items = await _reservationStore.read(_salesCartKey(scope, owner));
    items.removeWhere((value) => value['id_detalle'] == item['id_detalle']);
    await _reservationStore.save(_salesCartKey(scope, owner), items);
    cart = _cartFromItems(items);
  }

  void _filterFittingAvailability() {
    availability = fittingAvailability.where((item) {
      final matches = variantId == null || item['id_variante'] == variantId;
      final stock = (item['disponible'] as num?)?.toInt() ?? 0;
      return matches && stock > 0;
    }).toList();
  }

  Future<void> openPhotoTryOn() async {
    final selectedProduct = product;
    if (selectedProduct == null || variantId == null) return;
    setState(() {
      // Preserve the detail so the result can return to the same product.
      page = 'Vestidor';
      rows = [];
      availability = [];
      fitting = null;
      fittingAvailability = [];
      tryOnPhoto = null;
      tryOnResult = null;
      tryOnProductId = selectedProduct['id_producto'] as int;
      tryOnProductName = selectedProduct['nombre_producto'] as String? ??
          selectedProduct['nombre'] as String?;
    });
    await run(load);
  }

  Future<void> pickTryOnPhoto(ImageSource source) async {
    try {
      final photo =
          await imagePicker.pickImage(source: source, imageQuality: 92);
      if (photo == null || !mounted) return;
      final extension = photo.name.split('.').last.toLowerCase();
      if (!const {'jpg', 'jpeg', 'png', 'webp'}.contains(extension)) {
        setState(() {
          failed = true;
          message = 'Elige una fotografía JPG, PNG o WebP para el vestidor.';
        });
        return;
      }
      setState(() {
        tryOnPhoto = photo;
        tryOnResult = null;
        failed = false;
        message = variantId == null
            ? 'Fotografía seleccionada. Ahora elige una prenda.'
            : 'Fotografía seleccionada. Pulsa “Probar esta prenda”.';
      });
    } catch (_) {
      if (mounted) {
        setState(() {
          failed = true;
          message = source == ImageSource.camera
              ? 'No se pudo abrir la cámara. Revisa el permiso e intenta nuevamente.'
              : 'No se pudo abrir la galería. Revisa el permiso e intenta nuevamente.';
        });
      }
    }
  }

  Future<void> generateTryOn() async {
    await run(() async {
      if (tryOnPhoto == null || tryOnProductId == null || variantId == null) {
        throw ApiException(0, 'Selecciona una prenda y una fotografía válida.');
      }

      setState(() => message = '1/4 · Entré al probador virtual.');
      await Future.delayed(const Duration(milliseconds: 250));
      if (!mounted) return;
      setState(() => message = '2/4 · Enviando foto al backend…');

      setState(() => message = '3/4 · Gemini está editando la imagen…');
      final result = await repository.virtualTryOn(
          tryOnPhoto!, tryOnProductId!, variantId!);
      if (!mounted) return;
      setState(() {
        tryOnResult = result;
        message = '4/4 · Respuesta recibida. Imagen generada.';
      });
    });
  }

  Future<void> reserveTryOn() async {
    if (variantId == null)
      throw ApiException(0, 'Selecciona una talla y color.');
    if (availability.isEmpty) {
      throw ApiException(
          0, 'Esta variante no tiene stock disponible para reservar.');
    }
    if (inventoryId == null ||
        !availability.any((i) => i['id_inventario'] == inventoryId)) {
      inventoryId = availability.first['id_inventario'] as int;
    }
    await _queueReservation(inventoryId!, 1);
  }

  String imageUrl(Json item) {
    final value = item['imagen_url'] as String?;
    if (value == null || value.isEmpty) return '';
    return value.startsWith('http') ? value : '${repository.api.baseUrl}$value';
  }

  Future<void> openOrder(Json order) async {
    if (order['id_pedido'] is! int) {
      selectedOrder = order;
      paymentInfo = null;
      page = 'Pedido';
      return;
    }
    final detail = await repository.order(order['id_pedido'] as int);
    selectedOrder = detail;
    paymentInfo = null;
    page = 'Pedido';
    paymentInfo = await repository.payment(order['id_pedido'] as int);
    if (paymentInfo != null) {
      paymentMethod = paymentInfo!['metodo_pago'] as String? ?? paymentMethod;
    }
  }

  Future<bool> confirm(String title, String body,
      {String action = 'Confirmar'}) async {
    return await showDialog<bool>(
            context: context,
            builder: (context) => AlertDialog(
                  title: Text(title),
                  content: Text(body),
                  actions: [
                    TextButton(
                        onPressed: () => Navigator.pop(context, false),
                        child: const Text('Volver')),
                    FilledButton(
                        onPressed: () => Navigator.pop(context, true),
                        child: Text(action)),
                  ],
                )) ??
        false;
  }

  Future<void> checkout() async {
    if (!await confirm('Confirmar pedido',
        'Total: Bs ${cart['total']}\nMétodo: $paymentMethod\nSe creará un pedido que podrás pagar desde su detalle.',
        action: 'Crear pedido')) {
      return;
    }
    if (_salesOffline || !await _hasInternetAccess()) {
      await run(_queueOfflineSale);
      return;
    }
    await run(() async {
      final order = await repository.createOrder();
      // Switch away from the cart immediately: retrying a detail load must never
      // repeat order creation, even when the connection fails after this point.
      cart = {};
      rows = [];
      page = 'Pedidos';
      message =
          'Pedido #${order['id_pedido']} creado. Puedes retomar el pago desde tus pedidos.';
      await openOrder(order);
      if (paymentMethod == 'TARJETA') await _prepareSelectedPayment();
    });
  }

  Future<void> _queueOfflineSale() async {
    final scope = _salesScope;
    final userId = session.userId;
    final items = List<Json>.from(cart['items'] as List? ?? const []);
    if (scope == null || userId == null || items.isEmpty)
      throw ApiException(
          401, 'Inicia sesión como cliente para completar la venta offline.');
    final total = double.tryParse('${cart['total']}') ?? 0;
    final cash = paymentMethod == 'EFECTIVO'
        ? double.tryParse(cashReceived.text.trim())
        : null;
    if (paymentMethod == 'EFECTIVO' && cash == null)
      throw ApiException(0, 'Registra el importe recibido en efectivo.');
    if (cash != null && cash < total)
      throw ApiException(
          0, 'El importe recibido no puede ser menor al total provisional.');
    final linePayload = items
        .map((item) => <String, dynamic>{
              'client_line_id':
                  item['client_line_id'] ?? 'variant-${item['id_variante']}',
              'id_variante': item['id_variante'],
              'cantidad': item['cantidad'],
              if (item['offline_allocations'] is List)
                'offline_allocations': item['offline_allocations'],
            })
        .toList();
    final serverPayload = <String, dynamic>{
      'id_usuario': userId,
      'lineas': linePayload
          .map((line) => {
                'client_line_id': line['client_line_id'],
                'id_variante': line['id_variante'],
                'cantidad': line['cantidad'],
              })
          .toList(),
      'metodo_pago': paymentMethod,
      'datos_pago': {
        if (cash != null) 'importe_recibido': cash.toStringAsFixed(2),
        if (paymentMethod == 'TARJETA')
          'resultado_local': 'PENDIENTE_CONFIRMACION_SERVIDOR',
        if (paymentMethod == 'QR') 'verificacion': 'PENDIENTE',
      },
    };
    final operationId = await _catalogStore.enqueueOperation(
      tenantScope: scope,
      ownerUserId: userId,
      operationType: 'venta.crear',
      payload: {
        'id_usuario': userId,
        'lineas': linePayload,
        'metodo_pago': paymentMethod,
        'datos_pago': {
          if (cash != null) 'importe_recibido': cash.toStringAsFixed(2),
          if (paymentMethod == 'TARJETA')
            'resultado_local': 'PENDIENTE_CONFIRMACION_SERVIDOR',
          if (paymentMethod == 'QR') 'verificacion': 'PENDIENTE',
        },
      },
      syncPayload: serverPayload,
      clientId: outboxClientId,
    );
    final orders = await _reservationStore.orders(scope, userId);
    final localOrder = <String, dynamic>{
      'id_pedido': null,
      'local_operation_uuid': operationId,
      'numero_local': operationId.substring(0, 8).toUpperCase(),
      'fecha_pedido': DateTime.now().toIso8601String(),
      'estado': 'PENDIENTE_SINCRONIZAR',
      'estado_sync': 'PENDIENTE',
      'estado_pago': 'PENDIENTE',
      'metodo_pago': paymentMethod,
      'importe_recibido_local': cash?.toStringAsFixed(2),
      'total': total.toStringAsFixed(2),
      'mensaje_sync': 'Venta registrada. Esperando confirmación',
      'detalles': items
          .map((item) => <String, dynamic>{
                ...item,
                'client_line_id':
                    item['client_line_id'] ?? 'variant-${item['id_variante']}',
                'estado_sync': 'PENDIENTE',
              })
          .toList(),
    };
    orders.insert(0, localOrder);
    await _reservationStore.saveOrders(scope, userId, orders);
    await _reservationStore.save(_salesCartKey(scope, userId), []);
    cart = _cartFromItems([]);
    selectedOrder = localOrder;
    paymentInfo = null;
    page = 'Pedido';
    message = localOrder['mensaje_sync'] as String;
    await ReservationBackgroundSync.schedule();
    await _refreshOutboxState();
    if (await _hasInternetAccess()) await _syncOutbox();
  }

  Future<void> pay() => run(_prepareSelectedPayment);

  Future<void> _prepareSelectedPayment() async {
    final order = selectedOrder!;
    final orderId = order['id_pedido'];
    if (orderId is! int) {
      message = 'Comprobante provisional. La venta y su método de pago '
          'se sincronizarán al recuperar conexión; el cobro aún no está confirmado.';
      return;
    }
    if (!await _hasInternetAccess()) {
      final scope = _salesScope;
      final userId = session.userId;
      if (scope == null || userId == null) {
        throw ApiException(
            401, 'Inicia sesión para guardar la solicitud de pago.');
      }
      final received = paymentMethod == 'EFECTIVO'
          ? double.tryParse(cashReceived.text.trim())
          : null;
      if (paymentMethod == 'EFECTIVO' && received == null) {
        throw ApiException(0, 'Registra el importe recibido en efectivo.');
      }
      final operationId = await _catalogStore.enqueueOperation(
        tenantScope: scope,
        ownerUserId: userId,
        operationType: 'pago.solicitar',
        clientId: outboxClientId,
        payload: {
          'id_usuario': userId,
          'id_pedido': orderId,
          'metodo_pago': paymentMethod,
          'datos_pago': {
            if (received != null)
              'importe_recibido': received.toStringAsFixed(2),
          },
        },
      );
      await ReservationBackgroundSync.schedule();
      message = 'Solicitud provisional guardada ($operationId). '
          'El banco todavía no ha autorizado el pago.';
      await _refreshOutboxState();
      return;
    }
    if (!mounted) return;
    setState(() => message = 'Preparando pago...');
    if (paymentMethod == 'TARJETA') {
      final intent = await repository.createStripeIntent(orderId);
      final payment = Map<String, dynamic>.from(intent['payment'] as Map);
      paymentInfo = {...payment, 'simulation': intent['simulation'] == true};
      if (intent['simulation'] == true && !ApiConfig.paymentDemo) {
        throw ApiException(503,
            'El servidor ofrece pagos demo, pero esta version no permite simularlos.');
      }
      if (intent['simulation'] != true) {
        final publishableKey = intent['publishable_key'] as String? ?? '';
        final clientSecret = intent['client_secret'] as String? ?? '';
        if (publishableKey.isEmpty || clientSecret.isEmpty) {
          throw ApiException(503, 'Stripe no devolvió datos de autorización.');
        }
        try {
          await _stripePaymentSheet.pay(
            publishableKey: publishableKey,
            paymentIntentClientSecret: clientSecret,
          );
        } on StripeException catch (error) {
          final canceled = error.error.code == FailureCode.Canceled;
          message = canceled
              ? 'Pago cancelado. El pedido sigue pendiente y puedes reintentarlo.'
              : (error.error.localizedMessage ??
                  error.error.message ??
                  'Stripe no pudo completar la autorizacion. El pedido sigue pendiente.');
          if (mounted) setState(() {});
          return;
        }
        await _refreshStripePaymentStatus(orderId);
      } else {
        message =
            'Pago simulado de desarrollo. No se realizó un cobro bancario.';
      }
      if (mounted) setState(() {});
      return;
    }
    if (paymentMethod == 'QR') {
      final response = await repository.createQrPayment(orderId);
      paymentInfo = {
        ...Map<String, dynamic>.from(response['payment'] as Map),
        'qr_payload': response['qr_payload'],
        'simulation': response['simulation'] == true,
      };
      message = 'QR de demostración. No representa un pago bancario.';
    } else {
      paymentInfo = await repository.preparePayment(orderId, paymentMethod);
    }
    if (paymentInfo!['estado'] != 'PENDIENTE') {
      message = _paymentStatusMessage(
          paymentInfo!['estado'] as String? ?? 'PENDIENTE');
      await load();
      return;
    }
    _qrForOrder(order['id_pedido'] as int);
    message = 'Pago listo. Revisa los datos y confirma la operación.';
  }

  Future<void> _refreshStripePaymentStatus(int orderId) async {
    for (var attempt = 0; attempt < 15; attempt++) {
      final status = await repository.paymentStatus(orderId);
      paymentInfo = Map<String, dynamic>.from(status['payment'] as Map);
      final orderStatus = status['order_status'] as String?;
      if (selectedOrder != null && orderStatus != null) {
        selectedOrder!['estado'] = orderStatus;
      }
      final paymentStatus = paymentInfo!['estado'] as String?;
      if (paymentStatus != 'PENDIENTE' && paymentStatus != 'PROCESANDO') {
        message = paymentStatus == 'PAGADO'
            ? 'Pago aprobado por Stripe.'
            : 'Stripe no aprobó el pago. Puedes volver a intentarlo.';
        if (mounted) setState(() {});
        return;
      }
      if (attempt < 14) await Future<void>.delayed(const Duration(seconds: 2));
    }
    message = 'Stripe recibió la autorización. El servidor sigue verificando '
        'el pago; el pedido seguirá pendiente hasta su confirmación.';
    if (mounted) setState(() {});
  }

  void _validateCard() {
    final digits = cardNumber.text.replaceAll(RegExp(r'\s+'), '');
    if (!RegExp(r'^\d{13,19}$').hasMatch(digits)) {
      throw ApiException(
          0, 'Ingresa un número de tarjeta válido de 13 a 19 dígitos.');
    }
    if (cardHolder.text.trim().length < 3) {
      throw ApiException(0, 'Ingresa el nombre del titular.');
    }
    if (!RegExp(r'^(0[1-9]|1[0-2])\/\d{2}$').hasMatch(cardExpiry.text.trim())) {
      throw ApiException(0, 'La fecha debe tener el formato MM/AA.');
    }
    if (!RegExp(r'^\d{3,4}$').hasMatch(cardCvv.text.trim())) {
      throw ApiException(0, 'Ingresa un CVV válido de 3 o 4 dígitos.');
    }
  }

  bool _cardShouldApprove() {
    final digits = cardNumber.text.replaceAll(RegExp(r'\s+'), '');
    if (digits == '4000000000000002') return false;
    if (digits.endsWith('4242')) return true;
    throw ApiException(0,
        'Usa una tarjeta de prueba aprobada (4242 4242 4242 4242) o rechazada (4000 0000 0000 0002).');
  }

  String _qrForOrder(int orderId) => orderQrTokens.putIfAbsent(orderId, () {
        final random = Random();
        final suffix =
            List.generate(18, (_) => random.nextInt(16).toRadixString(16))
                .join();
        return 'VESTIDOR-$orderId-$suffix';
      });

  String _paymentStatusMessage(String status) {
    if (status == 'PENDIENTE') return 'Preparando pago';
    if (status == 'APROBADO' || status == 'PAGADO') return 'Pago aprobado';
    if (status == 'FALLIDO' || status == 'RECHAZADO') return 'Pago rechazado';
    return 'Estado del pago: $status';
  }

  Future<void> _simulatePayment([bool? forcedApproval]) async {
    if (paymentInfo == null) return;
    if (!ApiConfig.paymentDemo || paymentInfo!['simulated'] != true) {
      if (mounted) setState(() => message = 'Este pago no admite simulación.');
      return;
    }
    await run(() async {
      if (paymentMethod == 'TARJETA') _validateCard();
      final approve = forcedApproval ??
          (paymentMethod == 'TARJETA' ? _cardShouldApprove() : true);
      setState(() => message = 'Procesando pago...');
      await repository.simulatePayment(paymentInfo!['id_pago'] as int, approve);
      await load();
      message = approve
          ? 'Pago aprobado. Compra confirmada.'
          : 'Pago rechazado. Puedes intentarlo desde este pedido.';
    });
  }

  Map<String, String> _assistantCatalogFilters(String query) {
    final text = query.toLowerCase();
    String? category;
    for (final candidate in [
      'camisa',
      'chaqueta',
      'pantalon',
      'pantalón',
      'vestido',
      'blusa',
      'polera',
      'falda',
      'abrigo',
      'zapato'
    ]) {
      if (text.contains(candidate)) {
        category = candidate;
        break;
      }
    }
    String? color;
    for (final candidate in [
      'negro',
      'blanco',
      'azul',
      'verde',
      'rojo',
      'gris',
      'amarillo',
      'beige',
      'marron',
      'marrón'
    ]) {
      if (text.contains(candidate)) {
        color = candidate;
        break;
      }
    }
    final sizeMatch = RegExp(r'\b(xxl|xxl|xl|xs|s|m|l)\b').firstMatch(text);
    final priceMatch = RegExp(
            r'(?:menor|menos|hasta|maximo|máximo|debajo)\s*(?:a|de)?\s*(?:bs\.?\s*)?(\d+(?:[.,]\d+)?)')
        .firstMatch(text);
    final filters = <String, String>{};
    if (category != null) filters['categoria'] = category;
    if (color != null) filters['color'] = color;
    if (sizeMatch != null) filters['talla'] = sizeMatch.group(1)!;
    if (priceMatch != null) {
      filters['precio_max'] = priceMatch.group(1)!.replaceAll(',', '.');
    }
    return filters;
  }

  List<Json> _catalogAssistantRows(
      List<Json> products, Map<String, String> filters) {
    final result = <Json>[];
    for (final product in products) {
      final variants = (product['variantes'] as List? ?? [])
          .whereType<Map>()
          .map((variant) => Map<String, dynamic>.from(variant))
          .where((variant) =>
              (filters['talla'] == null ||
                  '${variant['talla']}'.toLowerCase() ==
                      filters['talla']!.toLowerCase()) &&
              (filters['color'] == null ||
                  '${variant['color']}'.toLowerCase() ==
                      filters['color']!.toLowerCase()))
          .toList();
      if (variants.isEmpty) continue;
      final variant = variants.first;
      result.add({
        'id_producto': product['id_producto'],
        'id_variante': variant['id_variante'],
        'nombre': product['nombre'],
        'imagen_url': product['imagen_url'],
        'precio': product['precio_base'],
        'talla': variant['talla'],
        'color': variant['color'],
        'categoria': product['categoria'],
      });
    }
    return result;
  }

  Future<void> askFashionAssistant() async {
    final query = fashionAssistant.text.trim();
    if (query.isEmpty) {
      throw ApiException(0, 'Escribe qué prenda estás buscando.');
    }
    await run(() async {
      setState(() {
        assistantStatus = 'Procesando con IA';
        assistantReply = '';
        rows = [];
      });
      final response = await repository.api.request(
          'POST', '/api/experience/fashion-assistant', {'mensaje': query});
      if (response is! Map) {
        throw ApiException(0, 'El asistente no devolvió una respuesta válida.');
      }
      final data = Map<String, dynamic>.from(response);
      final filters = _assistantCatalogFilters(query);
      final exactProducts = await _catalogRequest(filters);
      rows = _catalogAssistantRows(exactProducts, filters);
      assistantReply = data['respuesta'] as String? ??
          'Encontré estas prendas según tu búsqueda.';
      if (rows.isEmpty) {
        final alternativeFilters = <String, String>{
          if (filters['categoria'] != null) 'categoria': filters['categoria']!
        };
        final alternatives = await _catalogRequest(alternativeFilters);
        rows = _catalogAssistantRows(alternatives, alternativeFilters);
        assistantReply = rows.isEmpty
            ? 'No encontré productos exactos ni alternativas disponibles.'
            : 'No encontré productos exactos, estas son alternativas similares.';
      } else if (!_mentionsSizeOrColor(query)) {
        assistantReply =
            '$assistantReply ¿Qué talla necesitas o qué color prefieres?';
      }
      assistantStatus = 'Mostrando resultados';
      if (data.isNotEmpty) return;
      if (data.isEmpty) {
        final rawRows = data['recomendaciones'];
        rows = rawRows is List
            ? rawRows
                .whereType<Map>()
                .map((row) => Map<String, dynamic>.from(row))
                .toList()
            : <Json>[];
        assistantReply = data['respuesta'] as String? ??
            'Encontré estas prendas según tu búsqueda.';
        if (rows.isEmpty) {
          assistantReply =
              'No encontré prendas disponibles para esa búsqueda. Prueba con otra talla, color o categoría.';
        } else if (!_mentionsSizeOrColor(query)) {
          assistantReply =
              '$assistantReply ¿Qué talla necesitas o qué color prefieres?';
        }
        assistantStatus = 'Mostrando resultados';
      }
    });
  }

  bool _mentionsSizeOrColor(String query) {
    final text = query.toLowerCase();
    return RegExp(r'\b(xs|s|m|l|xl|xxl|talla)\b').hasMatch(text) ||
        RegExp(r'\b(negro|blanco|azul|verde|rojo|gris|amarillo|beige)\b')
            .hasMatch(text);
  }

  Future<List<Json>> _loadPersonalizedRecommendations() async {
    if (preferredSize.isEmpty &&
        preferredColors.isEmpty &&
        preferredGarments.isEmpty &&
        priceMinimum.text.trim().isEmpty &&
        priceMaximum.text.trim().isEmpty) {
      return [];
    }
    final filters = <String, String>{
      if (preferredSize.isNotEmpty) 'talla': preferredSize,
      if (priceMaximum.text.trim().isNotEmpty)
        'precio_max': priceMaximum.text.trim()
    };
    final products = await _catalogRequest(filters);
    final minimum = double.tryParse(priceMinimum.text.trim());
    final maximum = double.tryParse(priceMaximum.text.trim());
    return products.where((product) {
      final price = double.tryParse('${product['precio_base']}');
      if (minimum != null && (price == null || price < minimum)) return false;
      if (maximum != null && (price == null || price > maximum)) return false;
      final variants = (product['variantes'] as List? ?? []).whereType<Map>();
      return variants.any((raw) {
        final variant = Map<String, dynamic>.from(raw);
        final colorMatches = preferredColors.isEmpty ||
            preferredColors.any((value) =>
                '${variant['color']}'.toLowerCase() == value.toLowerCase());
        final garmentMatches = preferredGarments.isEmpty ||
            preferredGarments.any((value) =>
                '${product['categoria']?['nombre']}'.toLowerCase().contains(
                    value.toLowerCase().substring(0, min(5, value.length))));
        return colorMatches && garmentMatches;
      });
    }).map((product) {
      final variants = (product['variantes'] as List? ?? []).whereType<Map>();
      final selected = variants.firstWhere(
          (raw) => preferredSize.isEmpty || raw['talla'] == preferredSize,
          orElse: () => variants.first);
      final variant = Map<String, dynamic>.from(selected);
      return <String, dynamic>{
        ...product,
        'id_variante': variant['id_variante'],
        'nombre': product['nombre'],
        'precio': product['precio_base'],
        'talla': variant['talla'],
        'color': variant['color'],
      };
    }).toList();
  }

  Future<void> saveProfile() async {
    if (firstName.text.trim().isEmpty || lastName.text.trim().isEmpty) {
      throw ApiException(0, 'Nombres y apellidos son obligatorios.');
    }
    final minimum = double.tryParse(priceMinimum.text.trim());
    final maximum = double.tryParse(priceMaximum.text.trim());
    if (priceMinimum.text.trim().isNotEmpty &&
        (minimum == null || minimum < 0)) {
      throw ApiException(0, 'El precio mínimo debe ser un número válido.');
    }
    if (priceMaximum.text.trim().isNotEmpty &&
        (maximum == null ||
            maximum < 0 ||
            (minimum != null && maximum < minimum))) {
      throw ApiException(0, 'El precio máximo debe ser mayor al mínimo.');
    }
    if (!await _hasInternetAccess()) {
      throw ApiException(
          0, 'Necesitas conexión para guardar los cambios del perfil.');
    }
    await _saveLocalPreferences();
    await repository.updateProfile({
      'nombres': firstName.text.trim(),
      'apellidos': lastName.text.trim(),
      'telefono': phone.text.trim().isEmpty ? null : phone.text.trim()
    });
    await load();
    message = 'Perfil actualizado';
  }

  Future<void> _saveLocalPreferences() async {
    _localStore ??= await SharedPreferences.getInstance();
    await Future.wait([
      _localStore!.setString(_styleKey('size'), preferredSize),
      _localStore!.setStringList(_styleKey('colors'), preferredColors.toList()),
      _localStore!
          .setStringList(_styleKey('garments'), preferredGarments.toList()),
      _localStore!.setString(_styleKey('preferred'), preferredStyle),
      _localStore!.setString(_styleKey('price_min'), priceMinimum.text.trim()),
      _localStore!.setString(_styleKey('price_max'), priceMaximum.text.trim()),
    ]);
    localStylePreferences
      ..['talla'] = preferredSize
      ..['colores'] = List<String>.from(preferredColors)
      ..['prendas'] = List<String>.from(preferredGarments)
      ..['estilo'] = preferredStyle
      ..['precio_minimo'] = priceMinimum.text.trim()
      ..['precio_maximo'] = priceMaximum.text.trim();
  }

  List<String> get _availableSizes => rows
      .expand((row) => (row['variantes'] as List? ?? const []))
      .map((variant) => (variant as Map)['talla']?.toString() ?? '')
      .where((value) => value.isNotEmpty)
      .toSet()
      .toList()
    ..sort();
  List<String> get _availableColors => rows
      .expand((row) => (row['variantes'] as List? ?? const []))
      .map((variant) => (variant as Map)['color']?.toString() ?? '')
      .where((value) => value.isNotEmpty)
      .toSet()
      .toList()
    ..sort();
  List<String> get _availableCategories => rows
      .map((row) => (row['categoria'] as Map?)?['nombre']?.toString() ?? '')
      .where((value) => value.isNotEmpty)
      .toSet()
      .toList()
    ..sort();

  Widget field(String label, TextEditingController controller,
          {bool secret = false,
          TextInputType? keyboard,
          int? limit,
          ValueChanged<String>? onChanged}) =>
      Padding(
          padding: const EdgeInsets.symmetric(vertical: 8),
          child: TextField(
              controller: controller,
              obscureText: secret,
              enabled: !busy,
              keyboardType: keyboard,
              maxLength: limit,
              onChanged: onChanged,
              autocorrect: !secret,
              decoration: InputDecoration(
                  labelText: label,
                  border: const OutlineInputBorder(),
                  counterText: '')));
  Widget button(String label, Future<void> Function() action,
          {bool enabled = true, bool autoRun = true}) =>
      Padding(
          padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 4),
          child: FilledButton(
              onPressed: busy || !enabled
                  ? null
                  : () => autoRun ? run(action) : action(),
              child: Text(label)));
  Widget empty(String text) => Padding(
      padding: const EdgeInsets.all(24),
      child: Text(text, textAlign: TextAlign.center));
  Widget filters({bool withSearch = true}) => ExpansionTile(
          initiallyExpanded: false,
          title: const Text('Buscar y filtrar'),
          tilePadding: EdgeInsets.zero,
          children: [
            if (withSearch) field('Buscar prenda', search),
            Row(children: [
              Expanded(child: field('Talla', size)),
              const SizedBox(width: 12),
              Expanded(child: field('Color', color))
            ]),
            field('Categoría', category),
            if (withSearch)
              field('Precio máximo (Bs)', maxPrice,
                  keyboard:
                      const TextInputType.numberWithOptions(decimal: true)),
            Wrap(children: [
              button(withSearch ? 'Buscar' : 'Recomendar', load),
              TextButton(
                  onPressed: busy
                      ? null
                      : () {
                          for (final c in [
                            search,
                            size,
                            color,
                            category,
                            maxPrice
                          ]) {
                            c.clear();
                          }
                          run(load);
                        },
                  child: const Text('Limpiar filtros'))
            ])
          ]);
  Widget quantityPicker() => Row(children: [
        const Text('Cantidad'),
        IconButton(
            tooltip: 'Reducir cantidad',
            onPressed:
                busy || quantity <= 1 ? null : () => setState(() => quantity--),
            icon: const Icon(Icons.remove)),
        Text('$quantity'),
        IconButton(
            tooltip: 'Aumentar cantidad',
            onPressed: busy || quantity >= 100
                ? null
                : () => setState(() => quantity++),
            icon: const Icon(Icons.add))
      ]);
  Widget paymentPicker() => DropdownButtonFormField<String>(
      initialValue: paymentMethod,
      decoration: const InputDecoration(labelText: 'Método de pago'),
      items: [
        for (final m in ['QR', 'TARJETA', 'EFECTIVO'])
          DropdownMenuItem(value: m, child: Text(m))
      ],
      onChanged: busy ? null : (m) => setState(() => paymentMethod = m!));

  Widget _statusChip(String status) {
    final approved = status == 'APROBADO' || status == 'PAGADO';
    final rejected = status == 'FALLIDO' || status == 'RECHAZADO';
    final color = approved
        ? Colors.green
        : rejected
            ? Colors.red
            : Colors.orange;
    return Chip(
      avatar: Icon(
          approved
              ? Icons.check_circle
              : rejected
                  ? Icons.cancel
                  : Icons.hourglass_top,
          color: color,
          size: 18),
      label: Text(_paymentStatusMessage(status)),
    );
  }

  Widget _cardPreview() => Container(
      width: double.infinity,
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
          gradient: const LinearGradient(
              colors: [Color(0xff153f33), Color(0xff28745b)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight),
          borderRadius: BorderRadius.circular(20),
          boxShadow: const [
            BoxShadow(
                color: Color(0x22000000), blurRadius: 12, offset: Offset(0, 6))
          ]),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          const Text('VESTIDOR VIRTUAL',
              style: TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 1.2)),
          Icon(Icons.contactless, color: Colors.white.withValues(alpha: .85))
        ]),
        const SizedBox(height: 30),
        Text(
            cardNumber.text.isEmpty
                ? '••••  ••••  ••••  ••••'
                : _maskedCardNumber(),
            style: const TextStyle(
                color: Colors.white, fontSize: 20, letterSpacing: 2)),
        const SizedBox(height: 22),
        Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          Text(
              cardHolder.text.isEmpty
                  ? 'NOMBRE DEL TITULAR'
                  : cardHolder.text.toUpperCase(),
              style: const TextStyle(
                  color: Colors.white, fontSize: 12, letterSpacing: .8)),
          Text(cardExpiry.text.isEmpty ? 'MM/AA' : cardExpiry.text,
              style: const TextStyle(color: Colors.white, fontSize: 12))
        ]),
        const SizedBox(height: 8),
        const Text('CVV  •••',
            style: TextStyle(
                color: Colors.white, fontSize: 11, letterSpacing: 1.2))
      ]));

  String _maskedCardNumber() => _formattedCardNumber();

  String _formattedCardNumber() {
    final digits = cardNumber.text.replaceAll(RegExp(r'\s+'), '');
    final groups = <String>[];
    if (digits.isNotEmpty) {
      return digits
          .replaceAllMapped(RegExp(r'.{1,4}'), (match) => '${match.group(0)}  ')
          .trim();
    }
    for (var i = 0; i < digits.length; i += 4) {
      final end = min(i + 4, digits.length);
      groups.add(i < digits.length - 4 ? '••••' : digits.substring(i, end));
    }
    return groups.join('  ');
  }

  Widget _cardPaymentForm() => Column(children: [
        _cardPreview(),
        const SizedBox(height: 14),
        field('Número de tarjeta', cardNumber,
            keyboard: TextInputType.number,
            limit: 19,
            onChanged: (_) => setState(() {})),
        field('Nombre del titular', cardHolder,
            limit: 80, onChanged: (_) => setState(() {})),
        Row(children: [
          Expanded(
              child: field('Vencimiento (MM/AA)', cardExpiry,
                  limit: 5, onChanged: (_) => setState(() {}))),
          const SizedBox(width: 12),
          Expanded(
              child: field('CVV', cardCvv,
                  keyboard: TextInputType.number, limit: 4, secret: true))
        ]),
        const Text('Datos simulados: no se almacenan ni se envían al servidor.',
            style: TextStyle(fontSize: 12))
      ]);

  Widget _qrPaymentCard() {
    final info = paymentInfo ?? const <String, dynamic>{};
    final orderId = selectedOrder?['id_pedido'];
    final token = info['qr_payload'] as String?;
    if (token == null || info['simulation'] != true) {
      return const Card(
          child: Padding(
        padding: EdgeInsets.all(16),
        child: Text('El proveedor bancario QR no está configurado. El pedido '
            'permanece pendiente y no se considera pagado.'),
      ));
    }
    return Card(
        color: const Color(0xfff3f7f3),
        child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(children: [
              const Text('Escanea este código para pagar',
                  style: TextStyle(fontWeight: FontWeight.bold)),
              const SizedBox(height: 14),
              SizedBox(
                  width: 210,
                  height: 210,
                  child: CustomPaint(painter: _FakeQrPainter(token))),
              const SizedBox(height: 10),
              Text('Pedido #$orderId',
                  style: const TextStyle(fontWeight: FontWeight.bold)),
              Text(
                  'Código asociado: ${token.substring(0, min(18, token.length))}…',
                  style: const TextStyle(fontSize: 11)),
              const SizedBox(height: 10),
              const Text(
                  'Este QR es una simulación y no genera ningún cobro real.',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 12))
            ])));
  }

  Widget _paymentSummary(String method, dynamic amount, int orderId) => Card(
        color: const Color(0xffe8f5ec),
        child: Padding(
          padding: const EdgeInsets.all(18),
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            const Icon(Icons.check_circle, color: Colors.green, size: 44),
            const SizedBox(height: 8),
            const Text('Pago realizado correctamente',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 14),
            Text('Pedido #$orderId'),
            Text('Método: $method'),
            Text('Monto: Bs $amount'),
            const Text('Estado: PAGADO'),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: busy ? null : () => setState(() => page = 'Pedido'),
              icon: const Icon(Icons.receipt_long),
              label: const Text('Ver mi pedido'),
            )
          ]),
        ),
      );

  Widget paymentPanel() {
    final info = paymentInfo;
    if (info == null) return const SizedBox.shrink();
    final status = info['estado'] as String? ?? 'PENDIENTE';
    final orderId = selectedOrder!['id_pedido'] as int;
    final method = info['metodo_pago'] as String? ?? paymentMethod;
    final approved = status == 'APROBADO' || status == 'PAGADO';
    final rejected = status == 'FALLIDO' || status == 'RECHAZADO';
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      _statusChip(status),
      if (approved) _paymentSummary(method, info['monto'], orderId),
      Text('Método: ${info['metodo_pago']} · Total: Bs ${info['monto']}'),
      if (status == 'PENDIENTE') ...[
        const SizedBox(height: 14),
        if (paymentMethod == 'QR') _qrPaymentCard(),
        if (paymentMethod == 'TARJETA' &&
            ApiConfig.paymentDemo &&
            info['simulated'] == true)
          _cardPaymentForm(),
        if (paymentMethod == 'TARJETA' && info['simulated'] != true)
          const Text(
              'La autorización se procesa mediante Stripe PaymentSheet. No se guardan datos de tarjeta.'),
        const SizedBox(height: 8),
        if (ApiConfig.paymentDemo && info['simulated'] == true)
          Row(children: [
            Expanded(
              child: button(
                  paymentMethod == 'QR'
                      ? 'Simular pago realizado'
                      : 'Confirmar y simular pago',
                  _simulatePayment,
                  autoRun: false),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 4),
                child: OutlinedButton(
                  onPressed: busy ? null : () => _simulatePayment(false),
                  child: const Text('Simular rechazo'),
                ),
              ),
            )
          ]),
      ],
      if (rejected)
        Text('Puedes preparar nuevamente el pago desde este pedido.',
            style: TextStyle(color: Theme.of(context).colorScheme.error))
    ]);
  }

  Widget _preferenceChoices(
          String title, List<String> options, Set<String> selected) =>
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
              padding: const EdgeInsets.only(top: 12, bottom: 4),
              child: Text(title,
                  style: const TextStyle(fontWeight: FontWeight.bold))),
          Wrap(
              spacing: 6,
              children: options
                  .map((option) => FilterChip(
                        label: Text(option),
                        selected: selected.contains(option),
                        onSelected: busy
                            ? null
                            : (value) => setState(() {
                                  if (value) {
                                    selected.add(option);
                                  } else {
                                    selected.remove(option);
                                  }
                                }),
                      ))
                  .toList())
        ],
      );

  Widget stylePreferences() => Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            const Text('Preferencias de estilo',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            DropdownButtonFormField<String>(
                initialValue: _availableSizes.contains(preferredSize)
                    ? preferredSize
                    : null,
                decoration: const InputDecoration(labelText: 'Talla habitual'),
                items: [
                  for (final size in _availableSizes)
                    DropdownMenuItem(value: size, child: Text(size))
                ],
                onChanged: busy
                    ? null
                    : (value) => setState(() => preferredSize = value ?? '')),
            _preferenceChoices(
                'Colores preferidos', _availableColors, preferredColors),
            _preferenceChoices('Tipos de prendas favoritas',
                _availableCategories, preferredGarments),
            _stylePreferenceChoices(),
            if (preferredStyle.isNotEmpty)
              TextButton(
                  onPressed:
                      busy ? null : () => setState(() => preferredStyle = ''),
                  child: const Text('Quitar estilo seleccionado')),
            Row(children: [
              Expanded(
                  child: field('Precio mínimo', priceMinimum,
                      keyboard: const TextInputType.numberWithOptions(
                          decimal: true))),
              const SizedBox(width: 12),
              Expanded(
                  child: field('Precio máximo', priceMaximum,
                      keyboard:
                          const TextInputType.numberWithOptions(decimal: true)))
            ])
          ]),
        ),
      );

  Widget _stylePreferenceChoices() => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
              padding: EdgeInsets.only(top: 12, bottom: 4),
              child: Text('Estilo preferido',
                  style: TextStyle(fontWeight: FontWeight.bold))),
          Wrap(
              spacing: 6,
              children: ['Casual', 'Formal', 'Deportivo']
                  .map((style) => ChoiceChip(
                        label: Text(style),
                        selected: preferredStyle == style,
                        onSelected: busy
                            ? null
                            : (selected) => setState(
                                () => preferredStyle = selected ? style : ''),
                      ))
                  .toList())
        ],
      );

  List<Widget> _personalizedRecommendationCards() => [
        const Text('Recomendado para ti',
            style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
        const SizedBox(height: 6),
        const Text('Basado en tus preferencias de estilo y precios.'),
        const SizedBox(height: 10),
        for (final r in personalizedRows)
          Card(
              child: Column(children: [
            imageUrl(r).isEmpty
                ? Container(
                    height: 120,
                    width: double.infinity,
                    color: const Color(0xffe1e9e2),
                    child: const Icon(Icons.checkroom,
                        size: 54, color: Color(0xff0d5848)))
                : Image.network(imageUrl(r),
                    height: 120,
                    width: double.infinity,
                    fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) => const SizedBox(
                        height: 120, child: Icon(Icons.checkroom))),
            ListTile(
                title: Text(r['nombre'] ?? 'Prenda'),
                subtitle: Text(
                    '${r['talla'] ?? ''} · ${r['color'] ?? ''} · Bs ${r['precio'] ?? r['precio_base'] ?? ''}')),
            Wrap(children: [
              button('Ver prenda', () => detail(r)),
              button(
                  'Agregar al carrito', () => add(r['id_variante'] as int, 1))
            ])
          ])),
        if (personalizedRows.isEmpty)
          empty(
              'Completa tus preferencias para recibir recomendaciones personalizadas.')
      ];

  List<Widget> fashionAssistantContent() => [
        if (assistantStatus == 'Esperando consulta' &&
            fashionAssistant.text.trim().isEmpty)
          ..._personalizedRecommendationCards(),
        const SizedBox(height: 14),
        Card(
            color: const Color(0xff153f33),
            child: Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('ASISTENTE DE MODA IA',
                          style: TextStyle(
                              color: Color(0xffa7ddbb),
                              fontWeight: FontWeight.bold,
                              letterSpacing: 1.2)),
                      const SizedBox(height: 8),
                      const Text(
                          'Cuéntame qué quieres vestir y buscaré prendas reales del catálogo.',
                          style: TextStyle(color: Colors.white)),
                      const SizedBox(height: 10),
                      field('Asistente de moda IA', fashionAssistant,
                          limit: 300,
                          onChanged: (_) => setState(() {
                                assistantStatus = 'Esperando consulta';
                                assistantReply = '';
                                rows = [];
                              })),
                      button('Consultar asistente', askFashionAssistant,
                          autoRun: false),
                    ]))),
        const SizedBox(height: 12),
        Text('Estado: $assistantStatus',
            style: const TextStyle(fontWeight: FontWeight.bold)),
        if (assistantReply.isNotEmpty)
          Padding(
              padding: const EdgeInsets.symmetric(vertical: 10),
              child: Text(assistantReply)),
        for (final r in rows)
          Card(
              child: Column(children: [
            imageUrl(r).isEmpty
                ? Container(
                    height: 120,
                    width: double.infinity,
                    color: const Color(0xffe1e9e2),
                    child: const Icon(Icons.checkroom,
                        size: 54, color: Color(0xff0d5848)))
                : Image.network(imageUrl(r),
                    height: 120,
                    width: double.infinity,
                    fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) => const SizedBox(
                        height: 120, child: Icon(Icons.checkroom))),
            ListTile(
                title: Text(r['nombre'] ?? 'Prenda'),
                subtitle: Text(
                    '${r['talla'] ?? ''} · ${r['color'] ?? ''} · Bs ${r['precio'] ?? ''}')),
            Wrap(children: [
              button('Ver prenda', () => detail(r)),
              button(
                  'Agregar al carrito', () => add(r['id_variante'] as int, 1))
            ])
          ])),
        if (rows.isEmpty && assistantStatus == 'Mostrando resultados')
          empty('No hay prendas disponibles para esta consulta.')
      ];

  List<Widget> content() {
    if (page == 'Recomendaciones') return fashionAssistantContent();
    switch (page) {
      case 'Catálogo':
        return [
          if (offlineMode)
            Card(
                color: Theme.of(context).colorScheme.tertiaryContainer,
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Text(
                      'Modo offline${catalogSyncedAt == null ? '' : ' · última sincronización ${MaterialLocalizations.of(context).formatShortDate(catalogSyncedAt!)}'}. La disponibilidad corresponde a la última información descargada.'),
                )),
          if (session.signedIn)
            Card(
                child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                        'Sincronización · ${_networkAvailable ? 'red disponible' : 'sin conexión'}',
                        style: const TextStyle(fontWeight: FontWeight.bold)),
                    Text(
                        'Pendientes: ${outboxRows.where((row) => row['status'] == 'PENDIENTE').length} · Enviando: ${outboxRows.where((row) => row['status'] == 'ENVIANDO').length} · Sincronizadas: ${outboxRows.where((row) => row['status'] == 'SINCRONIZADA').length}'),
                    Text(
                        'Rechazadas: ${outboxRows.where((row) => row['status'] == 'RECHAZADA').length} · Reintento: ${outboxRows.where((row) => row['status'] == 'ERROR_REINTENTABLE').length}'),
                    if (outboxLastSync != null)
                      Text(
                          'Última sincronización: ${MaterialLocalizations.of(context).formatFullDate(DateTime.fromMillisecondsSinceEpoch(outboxLastSync!))}'),
                    for (final operation in outboxRows.where((row) =>
                        row['status'] == 'RECHAZADA' ||
                        row['status'] == 'ERROR_REINTENTABLE'))
                      Text(
                          '${operation['operation_type']}: ${operation['error_category'] ?? ''} ${operation['error_message'] ?? ''}'),
                  ]),
            )),
          if (!session.signedIn)
            Card(
                child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                        'Tienda: ${publicOrganizationSlug.isEmpty ? 'sin seleccionar' : publicOrganizationSlug}',
                        style: const TextStyle(fontWeight: FontWeight.bold)),
                    field('Slug de tienda', organizationSlug),
                    button('Cambiar tienda', selectPublicOrganization),
                    TextButton(
                        onPressed: busy
                            ? null
                            : () =>
                                setState(() => browsingPublicCatalog = false),
                        child: const Text('Iniciar sesión para comprar'))
                  ]),
            )),
          Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                  color: const Color(0xff153f33),
                  borderRadius: BorderRadius.circular(22)),
              child: const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('TU ESTILO, A TU MEDIDA',
                        style: TextStyle(
                            color: Color(0xffa7ddbb),
                            fontSize: 10,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 1.6)),
                    SizedBox(height: 12),
                    Text('Encuentra tu\npróxima prenda.',
                        style: TextStyle(
                            color: Colors.white,
                            fontSize: 24,
                            height: 1.05,
                            fontFamily: 'serif')),
                    SizedBox(height: 12),
                    Text(
                        'Catálogo, recomendaciones y vestidor virtual en una experiencia.',
                        style: TextStyle(color: Color(0xffdbe9e0)))
                  ])),
          const SizedBox(height: 12),
          filters(),
          if (rows.isNotEmpty)
            GridView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: rows.length,
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2,
                  crossAxisSpacing: 10,
                  mainAxisSpacing: 10,
                  childAspectRatio: .67),
              itemBuilder: (context, index) {
                final r = rows[index];
                final categoryName =
                    (r['categoria'] as Map?)?['nombre'] ?? 'Prenda';
                return Card(
                  clipBehavior: Clip.antiAlias,
                  margin: EdgeInsets.zero,
                  child: InkWell(
                    onTap: busy ? null : () => run(() => detail(r)),
                    child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(
                              child: Container(
                            width: double.infinity,
                            color: const Color(0xfff1f3ef),
                            padding: const EdgeInsets.all(8),
                            child: imageUrl(r).isEmpty
                                ? const Icon(Icons.checkroom,
                                    size: 56, color: Color(0xff0d5848))
                                : Image.network(imageUrl(r),
                                    fit: BoxFit.contain,
                                    errorBuilder: (_, __, ___) => const Icon(
                                        Icons.checkroom,
                                        size: 56,
                                        color: Color(0xff0d5848))),
                          )),
                          Padding(
                            padding: const EdgeInsets.fromLTRB(10, 8, 10, 10),
                            child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(categoryName.toString(),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: Theme.of(context)
                                          .textTheme
                                          .labelSmall
                                          ?.copyWith(
                                              color: const Color(0xff567066))),
                                  Text(r['nombre']?.toString() ?? 'Prenda',
                                      maxLines: 2,
                                      overflow: TextOverflow.ellipsis,
                                      style: const TextStyle(
                                          fontWeight: FontWeight.w600)),
                                  const SizedBox(height: 4),
                                  Text(
                                      'Bs ${r['precio_base'] ?? r['precio'] ?? '?'}',
                                      style: const TextStyle(
                                          fontWeight: FontWeight.bold,
                                          color: Color(0xff9b6c18))),
                                ]),
                          ),
                        ]),
                  ),
                );
              },
            ),
          if (rows.isEmpty && !busy && !failed)
            empty('No hay prendas para estos filtros.')
        ];
      case 'Detalle':
        final p = product!;
        return [
          Container(
            height: 190,
            decoration: BoxDecoration(
              color: const Color(0xffe2e9e2),
              borderRadius: BorderRadius.circular(20),
            ),
            child: imageUrl(p).isEmpty
                ? const Center(
                    child: Icon(Icons.checkroom,
                        size: 82, color: Color(0xff0d5848)),
                  )
                : ClipRRect(
                    borderRadius: BorderRadius.circular(20),
                    child: Image.network(
                      imageUrl(p),
                      width: double.infinity,
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => const Center(
                        child: Icon(Icons.checkroom,
                            size: 82, color: Color(0xff0d5848)),
                      ),
                    ),
                  ),
          ),
          const SizedBox(height: 12),
          Text(p['nombre_producto'],
              style: Theme.of(context).textTheme.headlineSmall),
          if (offlineMode)
            const Text(
                'Modo offline. Disponibilidad y precios corresponden a la última información descargada.'),
          Text(p['descripcion'] ?? ''),
          if (p['precio_base'] != null || p['precio'] != null)
            Text('Bs ${p['precio_base'] ?? p['precio']}'),
          DropdownButtonFormField<int>(
              key: ValueKey('variant-$variantId'),
              initialValue: variantId,
              isExpanded: true,
              decoration: const InputDecoration(labelText: 'Talla y color'),
              items: [
                for (final v in p['variantes'])
                  DropdownMenuItem(
                      value: v['id_variante'] as int,
                      child: Text('${v['talla']} · ${v['color']}'))
              ],
              onChanged: busy ? null : (v) => setState(() => variantId = v)),
          quantityPicker(),
          button('Agregar al carrito', () => add(variantId!),
              enabled: variantId != null),
          Text(offlineMode
              ? 'Disponibilidad por sucursal no actualizada sin conexión'
              : 'Disponibilidad del producto por sucursal'),
          for (final i in availability)
            ListTile(
                title:
                    Text(i['sucursal'] ?? i['nombre_sucursal'] ?? 'Sucursal'),
                subtitle: Text(
                    '${i['direccion'] ?? ''} · stock ${i['disponible'] ?? i['stock_disponible'] ?? 0}')),
          if (session.signedIn)
            button('Guardar como favorito', () async {
              await repository.preference('favorita', p['id_producto'] as int);
              message = 'Preferencia guardada';
            }),
          TextButton(
              onPressed: busy ? null : () => go('Reservas'),
              child: const Text('Reservar por talla, color y sucursal')),
          if (session.signedIn)
            FilledButton.tonalIcon(
                onPressed:
                    busy || variantId == null ? null : () => openPhotoTryOn(),
                icon: const Icon(Icons.view_in_ar),
                label: const Text('Abrir probador con cámara')),
          TextButton(
              onPressed: busy ? null : () => go('Catálogo'),
              child: const Text('Volver al catálogo')),
          if (!session.signedIn)
            TextButton(
                onPressed: busy
                    ? null
                    : () => setState(() => browsingPublicCatalog = false),
                child: const Text('Iniciar sesión para reservar o comprar'))
        ];
      case 'Carrito':
        final items = cart['items'] as List? ?? [];
        return [
          if (_salesOffline)
            const Card(
                child: Padding(
                    padding: EdgeInsets.all(12),
                    child: Text(
                        'Modo offline: los precios y la disponibilidad son provisionales hasta que el servidor confirme la venta.'))),
          for (final i in items)
            Card(
                child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(children: [
                      ListTile(
                          leading: i['imagen_url'] == null
                              ? const Icon(Icons.checkroom)
                              : SizedBox(
                                  width: 52,
                                  height: 64,
                                  child: Image.network(
                                      imageUrl(
                                          Map<String, dynamic>.from(i as Map)),
                                      fit: BoxFit.contain,
                                      errorBuilder: (_, __, ___) =>
                                          const Icon(Icons.checkroom))),
                          title: Text(i['producto'] ?? 'Prenda',
                              maxLines: 2, overflow: TextOverflow.ellipsis),
                          subtitle: Text(
                              '${i['talla']} · ${i['color']} · Bs ${i['precio_unitario']} × ${i['cantidad']}')),
                      Wrap(children: [
                        button('Reducir', () async {
                          await _updateCartLine(
                              Map<String, dynamic>.from(i as Map),
                              i['cantidad'] - 1);
                          await load();
                        }, enabled: i['cantidad'] > 1),
                        button('Aumentar', () async {
                          await _updateCartLine(
                              Map<String, dynamic>.from(i as Map),
                              i['cantidad'] + 1);
                          await load();
                        }),
                        button('Quitar', () async {
                          await _removeCartLine(
                              Map<String, dynamic>.from(i as Map));
                          await load();
                        })
                      ])
                    ]))),
          if (items.isEmpty && !busy && !failed) ...[
            const SizedBox(height: 28),
            const Icon(Icons.shopping_bag_outlined,
                size: 64, color: Color(0xff7d9188)),
            empty(
                'Tu carrito est? vac?o. Explora el cat?logo y guarda tus prendas favoritas aqu?.'),
            button('Volver al cat?logo', () => go('Cat?logo')),
          ],
          if (items.isNotEmpty) ...[
            const Divider(height: 24),
            Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
              const Text('Subtotal'),
              Text('Bs ${cart['total'] ?? '0.00'}'),
            ]),
            const SizedBox(height: 6),
            Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
              const Text('Total',
                  style: TextStyle(fontWeight: FontWeight.bold)),
              Text('Bs ${cart['total'] ?? '0.00'}',
                  style: Theme.of(context).textTheme.titleLarge),
            ]),
          ],
          if (items.isNotEmpty) ...[
            const SizedBox(height: 20),
            paymentPicker(),
            if (paymentMethod == 'EFECTIVO')
              field('Importe recibido (Bs)', cashReceived,
                  keyboard: TextInputType.number),
            button(
                _salesOffline ? 'Registrar venta offline' : 'Confirmar compra',
                checkout,
                autoRun: false)
          ]
        ];
      case 'Pedidos':
        return [
          for (final o in rows)
            Card(
                child: ListTile(
                    title: Text(o['id_pedido'] == null
                        ? 'Pedido local ${o['numero_local'] ?? ''} · ${o['estado_sync'] ?? o['estado']}'
                        : 'Pedido #${o['id_pedido']} · ${o['estado']}'),
                    subtitle: Text('Bs ${o['total']} · ${o['fecha_pedido']}'),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: busy ? null : () => run(() => openOrder(o)))),
          if (rows.isEmpty && !busy && !failed) empty('Todavía no hay pedidos.')
        ];
      case 'Pedido':
        final o = selectedOrder!;
        return [
          Text(
              o['id_pedido'] == null
                  ? 'Comprobante provisional #${o['numero_local'] ?? ''}'
                  : 'Pedido #${o['id_pedido']}',
              style: Theme.of(context).textTheme.headlineSmall),
          Text('Estado: ${o['estado']}'),
          if (o['estado_sync'] != null)
            Text(o['mensaje_sync'] ??
                'Estado de sincronización: ${o['estado_sync']}'),
          if (o['estado_pago'] == 'PENDIENTE')
            const Text(
                'Pago pendiente de conciliación o confirmación del servidor.'),
          Text('Total: Bs ${o['total']}'),
          for (final d in o['detalles'] as List? ?? [])
            Card(
                child: ListTile(
                    title: Text(d['producto']),
                    subtitle: Text(
                        '${d['talla']} · ${d['color']} · ${d['cantidad']} × Bs ${d['precio_unitario']}'))),
          if (paymentInfo != null) paymentPanel(),
          if (o['id_pedido'] is int && o['estado'] == 'PENDIENTE') ...[
            const SizedBox(height: 20),
            if (paymentInfo == null || paymentInfo!['estado'] == 'FALLIDO')
              paymentPicker(),
            button(
                paymentInfo == null || paymentInfo!['estado'] == 'FALLIDO'
                    ? 'Preparar pago'
                    : 'Actualizar método de pago',
                pay,
                autoRun: false)
          ],
          TextButton(
              onPressed: busy ? null : () => go('Pedidos'),
              child: const Text('Volver a mis pedidos'))
        ];
      case 'Reservas':
        return [
          if (reservationsOfflineMode)
            const Text(
                'Modo offline: la disponibilidad corresponde a la última descarga. El servidor confirma el resultado al sincronizar.'),
          button('Sincronizar reservas pendientes', () async {
            await _syncOutbox();
            await _loadReservations();
          }),
          DropdownButtonFormField<int>(
              key: ValueKey('inventory-$inventoryId'),
              initialValue: inventoryId,
              isExpanded: true,
              decoration: const InputDecoration(labelText: 'Prenda y sucursal'),
              items: [
                for (final i in availability)
                  DropdownMenuItem(
                      value: i['id_inventario'] as int,
                      child: Text(
                          '${i['producto']} · ${i['talla']} · ${i['color']} · ${i['sucursal']} (${i['disponible']})',
                          overflow: TextOverflow.ellipsis))
              ],
              onChanged: busy ? null : (v) => setState(() => inventoryId = v)),
          quantityPicker(),
          button('Reservar', () async {
            await _queueReservation(inventoryId!, quantity);
          }, enabled: inventoryId != null),
          if (availability.isEmpty && !busy)
            empty('No hay prendas disponibles para reservar.'),
          const Text('Mis reservas'),
          for (final r in rows)
            Card(
                child: Column(children: [
              ListTile(
                  title: Text('${r['producto']} · ${r['estado']}'),
                  subtitle: Text(
                      '${r['sucursal']} · ${r['talla']} · ${r['color']} · ${r['cantidad']} unidades')),
              if (r['id_reserva'] is int &&
                  (r['id_reserva'] as int) > 0 &&
                  ['PENDIENTE', 'RESERVADA', 'CONFIRMADA']
                      .contains(r['estado']))
                button('Comprar reserva', () async {
                  await run(() async {
                    await repository.purchaseReservation(r);
                    await load();
                    message =
                        'Reserva agregada al carrito. Continúa con el checkout.';
                    go('Carrito');
                  });
                }, autoRun: false),
              if (['PENDIENTE', 'RESERVADA', 'CONFIRMADA']
                      .contains(r['estado']) ||
                  (r['id_reserva'] == 0 && r['local_operation_uuid'] != null))
                button('Cancelar reserva', () async {
                  if (!await confirm('Cancelar reserva',
                      'Se liberará el stock de esta reserva.')) {
                    return;
                  }
                  await run(() async {
                    await _cancelReservation(r);
                  });
                }, autoRun: false)
            ])),
          if (rows.isEmpty && !busy && !failed)
            empty('Todavía no tienes reservas.')
        ];
      case 'Cambios':
        return [
          if (reservationsOfflineMode)
            const Card(
                child: Padding(
                    padding: EdgeInsets.all(12),
                    child: Text(
                        'Modo offline: se muestran compras, variantes y sucursales descargadas. Precio y stock pueden haber cambiado.'))),
          const Text('Compras elegibles',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
          if (exchangeEligible.isEmpty)
            const Text(
                'No hay compras elegibles descargadas. Conéctate para consultar pedidos pagados y entregados dentro del plazo.'),
          for (final purchase in exchangeEligible)
            Card(
                child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                              'Pedido #${purchase['id_pedido']} · ${purchase['producto']} ${purchase['talla']} · ${purchase['color']}',
                              style:
                                  const TextStyle(fontWeight: FontWeight.bold)),
                          Text(
                              'Compra: ${purchase['fecha_compra']} · entrega confirmada: ${purchase['fecha_entrega']} · precio pagado: Bs ${purchase['precio_pagado']}'),
                          if (exchangeOptions[purchase['id_detalle']]
                              case final option?) ...[
                            DropdownButtonFormField<int>(
                              initialValue:
                                  exchangeVariantChoice[purchase['id_detalle']],
                              decoration: const InputDecoration(
                                  labelText: 'Prenda de la misma categoría'),
                              items: [
                                for (final variant
                                    in option['variantes'] as List? ?? const [])
                                  DropdownMenuItem<int>(
                                      value: variant['id_variante'] as int,
                                      child: Text(
                                          '${variant['producto']} · ${variant['talla']} · ${variant['color']}'))
                              ],
                              onChanged: (value) => setState(() =>
                                  exchangeVariantChoice[
                                      purchase['id_detalle'] as int] = value),
                            ),
                            DropdownButtonFormField<int>(
                              initialValue:
                                  exchangeBranchChoice[purchase['id_detalle']],
                              decoration: const InputDecoration(
                                  labelText: 'Sucursal del cambio'),
                              items: [
                                for (final branch
                                    in option['sucursales'] as List? ??
                                        const [])
                                  DropdownMenuItem<int>(
                                      value: branch['id_sucursal'] as int,
                                      child: Text(branch['nombre'] as String))
                              ],
                              onChanged: (value) => setState(() =>
                                  exchangeBranchChoice[
                                      purchase['id_detalle'] as int] = value),
                            ),
                            Text(
                                'Disponibilidad descargada: ${((option['variantes'] as List? ?? const []).where((variant) => variant['id_variante'] == exchangeVariantChoice[purchase['id_detalle']]).firstOrNull?['stock'] as List? ?? const []).map((stock) => '${stock['sucursal']}: ${stock['disponible']}').join(' · ')}'),
                            button(
                                'Solicitar cambio',
                                () => _requestExchange(
                                    purchase['id_detalle'] as int)),
                          ] else
                            TextButton(
                                onPressed:
                                    busy ? null : () => run(_loadExchanges),
                                child: const Text(
                                    'Descargar variantes y sucursales')),
                        ]))),
          field('Motivo del cambio', exchangeReason, limit: 255),
          const SizedBox(height: 12),
          const Text('Historial de cambios',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
          if (exchangeRows.isEmpty)
            const Text('Aún no hay solicitudes de cambio.'),
          for (final exchange in exchangeRows)
            Card(
                child: ListTile(
              leading: Icon(exchange['state'] == 'INCIDENCIA_CONCILIACION'
                  ? Icons.warning_amber
                  : Icons.swap_horiz),
              title: Text(
                  'Cambio ${exchange['id'] == null ? 'local' : '#${exchange['id']}'} · ${exchange['state']}'),
              subtitle: Text(
                  '${exchange['original_product'] ?? 'Prenda original'} → ${exchange['replacement_product'] ?? 'sustituto pendiente'} ${exchange['replacement_size'] ?? ''} · sync ${exchange['sync_status'] ?? 'SINCRONIZADA'}${exchange['sync_message'] == null ? '' : ' · ${exchange['sync_message']}'}'),
            )),
        ];
      case 'Recomendaciones':
        return [
          filters(withSearch: false),
          for (final r in rows)
            Card(
                child: Column(children: [
              ListTile(
                  title: Text(r['nombre']),
                  subtitle: Text(
                      '${r['talla']} · ${r['color']} · Bs ${r['precio']}\n${r['motivo']}')),
              Wrap(children: [
                button('Ver prenda', () => detail(r)),
                button('Agregar al carrito', () => add(r['id_variante'], 1))
              ])
            ])),
          if (rows.isEmpty && !busy && !failed)
            empty('No hay recomendaciones para estos filtros.')
        ];
      case 'Vestidor':
        return [
          Container(
              width: double.infinity,
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                  color: const Color(0xff153f33),
                  borderRadius: BorderRadius.circular(18)),
              child: const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('FASHION STORE · PROBADOR CON CÁMARA',
                        style: TextStyle(
                            color: Color(0xffa7ddbb),
                            fontSize: 10,
                            letterSpacing: 1.4,
                            fontWeight: FontWeight.bold)),
                    SizedBox(height: 8),
                    Text('Pruébate una prenda real',
                        style: TextStyle(
                            color: Colors.white,
                            fontSize: 24,
                            fontFamily: 'serif')),
                    SizedBox(height: 8),
                    Text(
                        'Usa una foto o la cámara del móvil y visualiza la prenda del catálogo sobre tu cuerpo.',
                        style: TextStyle(color: Color(0xffdbe9e0)))
                  ])),
          DropdownButtonFormField<int>(
              key: ValueKey('fitting-$variantId'),
              initialValue: rows.any((r) => r['id_variante'] == variantId)
                  ? variantId
                  : null,
              isExpanded: true,
              decoration: const InputDecoration(labelText: 'Prenda compatible'),
              items: [
                for (final r in rows)
                  DropdownMenuItem(
                      value: r['id_variante'] as int,
                      child: Text(
                          '${r['nombre']} · ${r['talla']} · ${r['color']}',
                          overflow: TextOverflow.ellipsis))
              ],
              onChanged: busy
                  ? null
                  : (v) => setState(() {
                        variantId = v;
                        final selected =
                            rows.firstWhere((r) => r['id_variante'] == v);
                        tryOnProductId = selected['id_producto'] as int;
                        tryOnProductName = selected['nombre'] as String?;
                        fitting = null;
                        tryOnResult = null;
                        garmentScale = 1;
                        garmentOffset = 0;
                        _filterFittingAvailability();
                      })),
          if (tryOnProductName != null)
            Text('Prenda seleccionada: $tryOnProductName'),
          const Text(
              'Usa una fotografía de cuerpo completo o torso, de frente y con buena iluminación.'),
          Wrap(spacing: 8, runSpacing: 8, children: [
            OutlinedButton.icon(
                onPressed:
                    busy ? null : () => pickTryOnPhoto(ImageSource.camera),
                icon: const Icon(Icons.camera_alt),
                label: const Text('Tomar fotografía')),
            OutlinedButton.icon(
                onPressed:
                    busy ? null : () => pickTryOnPhoto(ImageSource.gallery),
                icon: const Icon(Icons.photo_library),
                label: const Text('Elegir de galería')),
          ]),
          if (tryOnPhoto != null) ...[
            ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Image.file(File(tryOnPhoto!.path),
                    height: 240, fit: BoxFit.cover)),
            if (variantId == null)
              const Text(
                  'Selecciona una prenda antes de probar la fotografía.'),
            button('Probar esta prenda', generateTryOn,
                enabled: variantId != null && tryOnProductId != null,
                autoRun: false),
          ],
          if (rows.isEmpty && !busy && !failed)
            empty('No hay prendas compatibles disponibles.'),
          if (variantId != null && availability.isNotEmpty) ...[
            DropdownButtonFormField<int>(
                key: ValueKey('tryon-branch-$inventoryId'),
                initialValue:
                    availability.any((i) => i['id_inventario'] == inventoryId)
                        ? inventoryId
                        : null,
                isExpanded: true,
                decoration:
                    const InputDecoration(labelText: 'Sucursal para reservar'),
                items: [
                  for (final i in availability)
                    DropdownMenuItem(
                        value: i['id_inventario'] as int,
                        child:
                            Text('${i['sucursal']} · stock ${i['disponible']}'))
                ],
                onChanged:
                    busy ? null : (v) => setState(() => inventoryId = v)),
            button('Reservar esta prenda', reserveTryOn,
                enabled: inventoryId != null),
          ] else if (variantId != null)
            const Text(
                'Esta talla y color no tienen stock disponible para reservar.'),
          if (tryOnResult != null) ...[
            const Text('PRUEBA VIRTUAL',
                style: TextStyle(fontWeight: FontWeight.bold)),
            Image.memory(base64Decode(tryOnResult!['image_base64'] as String),
                fit: BoxFit.contain),
            Text(
                '${tryOnResult!['nombre']} · ${tryOnResult!['talla'] ?? ''} · ${tryOnResult!['color'] ?? ''}'),
            const Text(
                'Representación visual aproximada. El ajuste real de la prenda puede variar.'),
            Wrap(spacing: 8, children: [
              button('Probar otra prenda', () async {
                setState(() {
                  variantId = null;
                  tryOnProductId = null;
                  tryOnProductName = null;
                  tryOnResult = null;
                });
              }, autoRun: false),
              button(
                  'Tomar otra foto', () => pickTryOnPhoto(ImageSource.camera),
                  autoRun: false),
              button('Agregar al carrito', () => add(variantId!, 1)),
              if (product != null)
                button('Volver al producto', () => detail(product!)),
            ])
          ],
          ExpansionTile(title: const Text('Visor 3D de respaldo'), children: [
            const Padding(
                padding: EdgeInsets.all(12),
                child: Text(
                    'El probador con cámara es la experiencia principal. El visor 3D queda disponible como alternativa cuando no puedas usar una foto.')),
          ]),
        ];
      case 'Perfil':
        return [
          Text(profileEmail, style: Theme.of(context).textTheme.titleMedium),
          if (loyaltySnapshot != null &&
              loyaltySnapshot!['program'] != null) ...[
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Mis puntos',
                        style: TextStyle(
                            fontSize: 20, fontWeight: FontWeight.bold)),
                    Text('${loyaltySnapshot!['balance']} puntos disponibles'),
                    if (loyaltySnapshot!['tier'] != null)
                      Text('Nivel ${loyaltySnapshot!['tier']['name']}'),
                    if (loyaltySnapshot!['next_tier'] != null)
                      Text(
                          'Te faltan ${loyaltySnapshot!['next_tier']['minimum_points'] - loyaltySnapshot!['balance']} puntos para ${loyaltySnapshot!['next_tier']['name']}.'),
                    const SizedBox(height: 8),
                    const Text(
                        'Los puntos se acreditan cuando la compra queda confirmada.'),
                    for (final movement
                        in (loyaltySnapshot!['movements'] as List? ?? const [])
                            .take(10))
                      ListTile(
                        dense: true,
                        contentPadding: EdgeInsets.zero,
                        title: Text(switch (movement['kind']) {
                          'ACUMULACION' => 'Puntos acumulados',
                          'CANJE' => 'Canje de puntos',
                          'REVERSO' => 'Reversión de puntos',
                          'EXPIRACION' => 'Puntos vencidos',
                          _ => movement['kind'].toString(),
                        }),
                        subtitle: Text(
                            DateTime.tryParse(movement['created_at'] ?? '')
                                    ?.toLocal()
                                    .toString() ??
                                ''),
                        trailing: Text('${movement['points']} pts'),
                      ),
                  ],
                ),
              ),
            ),
          ],
          field('Nombres', firstName, limit: 100),
          field('Apellidos', lastName, limit: 100),
          field('Teléfono', phone, keyboard: TextInputType.phone, limit: 30),
          stylePreferences(),
          button('Guardar perfil', saveProfile),
          button('Cerrar sesión', logout)
        ];
      default:
        return [];
    }
  }

  List<Widget> authContent() => [
        const Icon(Icons.checkroom, size: 64),
        Text(register ? 'Crea tu cuenta' : 'Tu estilo, a tu medida',
            style: Theme.of(context).textTheme.headlineSmall),
        if (!browsingPublicCatalog) ...[
          field('Slug de tienda para explorar o registrarte', organizationSlug),
          button('Explorar catálogo', selectPublicOrganization)
        ] else
          TextButton(
              onPressed: busy
                  ? null
                  : () => setState(() => browsingPublicCatalog = false),
              child: const Text('Volver al inicio de sesión')),
        field('Correo', email,
            keyboard: TextInputType.emailAddress, limit: 255),
        field('Contraseña', password, secret: true),
        if (register) ...[
          field('Nombres', firstName, limit: 100),
          field('Apellidos', lastName, limit: 100)
        ],
        button(register ? 'Registrarse' : 'Iniciar sesión', authenticate),
        TextButton(
            onPressed: busy
                ? null
                : () => setState(() {
                      register = !register;
                      message = '';
                    }),
            child: Text(register ? 'Ya tengo cuenta' : 'Crear cuenta')),
        ExpansionTile(title: const Text('Recuperar contraseña'), children: [
          button('Solicitar recuperación', () async {
            repository.api.baseUrl = ClientSession.validateServer(server.text);
            if (!email.text.trim().contains('@')) {
              throw ApiException(
                  0, 'Ingresa tu correo para recuperar la contraseña.');
            }
            final r = await repository.requestReset(email.text);
            if (!mounted) return;
            resetToken.text = r['token'] ?? '';
            message = r['message'];
          }),
          field('Token de recuperación', resetToken),
          button('Restablecer contraseña', () async {
            if (resetToken.text.trim().isEmpty || password.text.length < 8) {
              throw ApiException(0,
                  'Ingresa el token y una nueva contraseña de al menos 8 caracteres.');
            }
            repository.api.baseUrl = ClientSession.validateServer(server.text);
            await repository.resetPassword(resetToken.text, password.text);
            if (!mounted) return;
            resetToken.clear();
            password.clear();
            message = 'Contraseña actualizada. Inicia sesión.';
          })
        ]),
        ExpansionTile(title: const Text('Conexión al servidor'), children: [
          field('Dirección de API', server, keyboard: TextInputType.url),
          const Text('La aplicación usa HTTPS con la API de FashionStore.')
        ])
      ];

  @override
  Widget build(BuildContext context) {
    if (!session.ready) {
      return const Scaffold(
          body: Center(
              child: CircularProgressIndicator(
                  semanticsLabel: 'Recuperando sesión')));
    }
    final loggedIn = session.signedIn;
    return PopScope(
        canPop: !loggedIn || page == 'Catálogo',
        onPopInvokedWithResult: (didPop, result) {
          if (!didPop && !busy) go(page == 'Pedido' ? 'Pedidos' : 'Catálogo');
        },
        child: Scaffold(
            appBar: AppBar(
                title: Text(loggedIn
                    ? page
                    : browsingPublicCatalog
                        ? 'Tienda $publicOrganizationSlug'
                        : 'Fashion Store'),
                actions: [
                  if (loggedIn)
                    IconButton(
                        tooltip: 'Actualizar',
                        onPressed: busy ? null : () => run(load),
                        icon: const Icon(Icons.refresh))
                ]),
            drawer: loggedIn
                ? Drawer(
                    child: SafeArea(
                        child: ListView(children: [
                    const ListTile(
                        leading: Icon(Icons.checkroom),
                        title: Text('Fashion Store'),
                        subtitle: Text('Tu cuenta de cliente')),
                    for (final destination in [
                      'Catálogo',
                      'Carrito',
                      'Pedidos',
                      'Cambios',
                      'Reservas',
                      'Recomendaciones',
                      'Vestidor',
                      'Perfil'
                    ])
                      ListTile(
                          selected: page == destination,
                          title: Text(destination),
                          onTap: busy
                              ? null
                              : () {
                                  Navigator.pop(context);
                                  go(destination);
                                }),
                    const Divider(),
                    ListTile(
                        title: const Text('Cerrar sesión'),
                        leading: const Icon(Icons.logout),
                        onTap: busy
                            ? null
                            : () {
                                Navigator.pop(context);
                                run(logout);
                              })
                  ])))
                : null,
            body: SafeArea(
                child: Center(
                    child: ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 760),
                        child: RefreshIndicator(
                            onRefresh: loggedIn ? () => run(load) : () async {},
                            child: ListView(
                                key: ValueKey('page-$page-$loggedIn'),
                                physics: const AlwaysScrollableScrollPhysics(),
                                padding: const EdgeInsets.all(20),
                                children: [
                                  if (busy) const LinearProgressIndicator(),
                                  if (message.isNotEmpty)
                                    Semantics(
                                        liveRegion: true,
                                        child: Card(
                                            color: failed
                                                ? Theme.of(context)
                                                    .colorScheme
                                                    .errorContainer
                                                : Theme.of(context)
                                                    .colorScheme
                                                    .secondaryContainer,
                                            child: Padding(
                                                padding:
                                                    const EdgeInsets.all(16),
                                                child: Text(message)))),
                                  if (failed && loggedIn)
                                    TextButton(
                                        onPressed:
                                            busy ? null : () => run(load),
                                        child: const Text('Volver a cargar')),
                                  if (loggedIn || browsingPublicCatalog)
                                    ...content()
                                  else
                                    ...authContent(),
                                  const SizedBox(height: 24)
                                ]))))),
            bottomNavigationBar: loggedIn
                ? NavigationBar(
                    selectedIndex: ['Carrito', 'Pedidos', 'Cambios', 'Perfil']
                            .contains(page)
                        ? ['Carrito', 'Pedidos', 'Cambios', 'Perfil']
                                .indexOf(page) +
                            1
                        : 0,
                    onDestinationSelected: busy
                        ? null
                        : (index) => go([
                              'Catálogo',
                              'Carrito',
                              'Pedidos',
                              'Cambios',
                              'Perfil'
                            ][index]),
                    destinations: const [
                        NavigationDestination(
                            icon: Icon(Icons.storefront), label: 'Catálogo'),
                        NavigationDestination(
                            icon: Icon(Icons.shopping_bag_outlined),
                            label: 'Carrito'),
                        NavigationDestination(
                            icon: Icon(Icons.receipt_long), label: 'Pedidos'),
                        NavigationDestination(
                            icon: Icon(Icons.swap_horiz), label: 'Cambios'),
                        NavigationDestination(
                            icon: Icon(Icons.person_outline), label: 'Perfil')
                      ])
                : null));
  }

  @override
  void dispose() {
    session.removeListener(sessionChanged);
    unawaited(_connectivitySubscription?.cancel());
    session.dispose();
    unawaited(_catalogStore.close());
    unawaited(_reservationStore.close());
    if (widget.repository == null) repository.api.dispose();
    for (final c in [
      email,
      password,
      firstName,
      lastName,
      phone,
      search,
      size,
      color,
      category,
      maxPrice,
      resetToken,
      fashionAssistant,
      priceMinimum,
      priceMaximum,
      cardNumber,
      cardHolder,
      cardExpiry,
      cardCvv,
      cashReceived,
      exchangeReason,
      server,
      organizationSlug
    ]) {
      c.dispose();
    }
    super.dispose();
  }
}
