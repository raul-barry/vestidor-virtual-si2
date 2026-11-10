import 'api_client.dart';
import 'package:image_picker/image_picker.dart';

typedef Json = Map<String, dynamic>;

/// The only mobile mapping of the existing client API. Prices, stock and order
/// transitions are always resolved by the backend, never recalculated here.
class ClientRepository {
  ClientRepository(this.api);
  final ApiClient api;
  Future<Json> object(String method, String path, [Object? body]) async =>
      Map<String, dynamic>.from(await api.request(method, path, body) as Map);
  Future<List<Json>> list(String path) async =>
      (await api.request('GET', path) as List)
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList();
  String query(Map<String, String> filters) => Uri(queryParameters: {
        for (final entry in filters.entries)
          if (entry.value.trim().isNotEmpty) entry.key: entry.value.trim(),
      }).query;
  Future<Json> login(String email, String password) => object('POST',
      '/api/auth/login', {'correo': email.trim(), 'password': password});
  Future<void> logout() async {
    await api.request('POST', '/api/auth/logout');
  }

  Future<Json> issueDeviceSyncCredential(String clientId) =>
      object('POST', '/api/sync/device-credentials', {'client_id': clientId});
  Future<void> revokeDeviceSyncCredential(int id) async {
    await api.request('DELETE', '/api/sync/device-credentials/$id');
  }

  Future<void> register(Json data, {String? organizationSlug}) async {
    final slug = organizationSlug?.trim().toLowerCase() ?? '';
    if (!RegExp(r'^[a-z0-9]+(?:-[a-z0-9]+)*$').hasMatch(slug)) {
      throw ApiException(0, 'Selecciona una tienda antes de crear una cuenta.');
    }
    await api.request(
        'POST',
        '/api/auth/register?${Uri(queryParameters: {
              'organization_slug': slug
            }).query}',
        data);
  }

  Future<Json> requestReset(String email) => object(
      'POST', '/api/auth/request-password-reset', {'correo': email.trim()});
  Future<void> resetPassword(String token, String password) async {
    await api.request('POST', '/api/auth/reset-password',
        {'token': token.trim(), 'nueva_password': password});
  }

  String _catalogQuery(Map<String, String> filters, String? organizationSlug) {
    final values = <String, String>{};
    if (api.token == null) {
      final slug = organizationSlug?.trim().toLowerCase() ?? '';
      if (!RegExp(r'^[a-z0-9]+(?:-[a-z0-9]+)*$').hasMatch(slug)) {
        throw ApiException(
            0, 'Selecciona una tienda para consultar el catálogo.');
      }
      values['organization_slug'] = slug;
    }
    values.addAll({
      for (final entry in filters.entries)
        if (entry.value.trim().isNotEmpty) entry.key: entry.value.trim(),
    });
    return Uri(queryParameters: values).query;
  }

  Future<List<Json>> catalog(
      [Map<String, String> filters = const {},
      String? organizationSlug]) async {
    final q = _catalogQuery(filters, organizationSlug);
    return list(
        '/api/catalog/products${filters.values.any((value) => value.trim().isNotEmpty) ? '/search' : ''}?$q');
  }

  Future<Json> variants(int id, {String? organizationSlug}) async => object(
      'GET',
      '/api/catalog/products/$id/variants?${_catalogQuery(const {}, organizationSlug)}');
  Future<Json> availability(int id, {String? organizationSlug}) async => object(
      'GET',
      '/api/catalog/products/$id/availability?${_catalogQuery(const {}, organizationSlug)}');
  Future<Json> cart() => object('GET', '/api/cart');
  Future<void> addItem(int variant, int quantity, {int? reservationId}) async {
    await api.request('POST', '/api/cart/items', {
      'id_variante': variant,
      'cantidad': quantity,
      if (reservationId != null) 'id_reserva': reservationId,
    });
  }

  Future<void> changeQuantity(int id, int quantity) async {
    await api.request('PUT', '/api/cart/items/$id', {'cantidad': quantity});
  }

  Future<void> removeItem(int id) async {
    await api.request('DELETE', '/api/cart/items/$id');
  }

  Future<List<Json>> orders() => list('/api/orders');
  Future<Json> order(int id) => object('GET', '/api/orders/$id');
  Future<List<Json>> eligibleExchangePurchases() =>
      list('/api/exchanges/eligible');
  Future<Json> exchangeOptions(int detailId) =>
      object('GET', '/api/exchanges/options?id_detalle=$detailId');
  Future<List<Json>> exchanges() => list('/api/exchanges');
  Future<Json> requestExchange(Json data) =>
      object('POST', '/api/exchanges', data);
  Future<Json> createOrder() => object('POST', '/api/orders');
  Future<Json?> payment(int orderId) async {
    try {
      return await object('GET', '/api/payments/order/$orderId');
    } on ApiException catch (e) {
      if (e.status != 404) rethrow;
      return null;
    }
  }

  Future<Json> preparePayment(int orderId, String method) async {
    final existing = await payment(orderId);
    if (existing != null && existing['estado'] != 'FALLIDO') return existing;
    try {
      return await object('POST', '/api/payments',
          {'id_pedido': orderId, 'metodo_pago': method});
    } on ApiException catch (e) {
      if (e.status != 409) rethrow;
      final concurrent = await payment(orderId);
      if (concurrent == null) rethrow;
      return concurrent;
    }
  }

  Future<Json> createStripeIntent(int orderId) => object(
      'POST', '/api/payments/stripe/create-intent', {'id_pedido': orderId});

  Future<Json> paymentStatus(int orderId) =>
      object('GET', '/api/payments/$orderId/status');

  Future<Json> createQrPayment(int orderId) => object(
      'POST', '/api/payments/qr', {'id_pedido': orderId, 'metodo_pago': 'QR'});

  Future<Json> simulatePayment(int id, bool approve) =>
      object('PUT', '/api/payments/$id/${approve ? 'approve' : 'reject'}');
  Future<List<Json>> reservations() => list('/api/reservations');
  Future<List<Json>> reservationAvailability({int? variantId}) => list(
      '/api/reservations/availability${variantId == null ? '' : '?id_variante=$variantId'}');
  Future<void> reserve(int inventory, int quantity) async {
    await api.request('POST', '/api/reservations',
        {'id_inventario': inventory, 'cantidad': quantity});
  }

  Future<void> cancelReservation(int id) async {
    await api.request('PUT', '/api/reservations/$id', {'estado': 'CANCELADA'});
  }

  Future<void> purchaseReservation(Json reservation) async {
    await addItem(
      reservation['id_variante'] as int,
      reservation['cantidad'] as int,
      reservationId: reservation['id_reserva'] as int,
    );
  }

  Future<Json> profile() => object('GET', '/api/users/profile');
  Future<Json> loyalty() => object('GET', '/api/loyalty/me');
  Future<Json> updateProfile(Json data) =>
      object('PUT', '/api/users/profile', data);
  Future<List<Json>> recommendations(Map<String, String> filters) =>
      list('/api/experience/recommendations?${query(filters)}');
  Future<List<Json>> fittingVariants() => list('/api/experience/fitting');
  Future<Json> fit(int variant) =>
      object('POST', '/api/experience/fitting', {'id_variante': variant});
  Future<Json> virtualTryOn(XFile photo, int productId, int variantId) async {
    final extension = photo.name.split('.').last.toLowerCase();
    final mime = switch (extension) {
      'jpg' || 'jpeg' => 'image/jpeg',
      'png' => 'image/png',
      'webp' => 'image/webp',
      _ => throw ApiException(
          0, 'Elige una fotografía JPG, PNG o WebP para el vestidor.'),
    };
    return Map<String, dynamic>.from(await api.multipart(
        '/api/experience/virtual-try-on',
        {'product_id': '$productId', 'variant_id': '$variantId'},
        await photo.readAsBytes(),
        photo.name,
        mime,
        requestTimeout: const Duration(seconds: 120)) as Map);
  }

  Future<void> preference(String type, int product, [int? variant]) async {
    await api.request('POST', '/api/experience/preferences',
        {'tipo': type, 'id_producto': product, 'id_variante': variant});
  }
}
