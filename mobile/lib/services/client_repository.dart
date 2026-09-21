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

  Future<void> register(Json data) async {
    await api.request('POST', '/api/auth/register', data);
  }

  Future<Json> requestReset(String email) => object(
      'POST', '/api/auth/request-password-reset', {'correo': email.trim()});
  Future<void> resetPassword(String token, String password) async {
    await api.request('POST', '/api/auth/reset-password',
        {'token': token.trim(), 'nueva_password': password});
  }

  Future<List<Json>> catalog([Map<String, String> filters = const {}]) {
    final q = query(filters);
    return list(q.isEmpty
        ? '/api/catalog/products'
        : '/api/catalog/products/search?$q');
  }

  Future<Json> variants(int id) =>
      object('GET', '/api/catalog/products/$id/variants');
  Future<Json> availability(int id) =>
      object('GET', '/api/catalog/products/$id/availability');
  Future<Json> cart() => object('GET', '/api/cart');
  Future<void> addItem(int variant, int quantity) async {
    await api.request('POST', '/api/cart/items',
        {'id_variante': variant, 'cantidad': quantity});
  }

  Future<void> changeQuantity(int id, int quantity) async {
    await api.request('PUT', '/api/cart/items/$id', {'cantidad': quantity});
  }

  Future<void> removeItem(int id) async {
    await api.request('DELETE', '/api/cart/items/$id');
  }

  Future<List<Json>> orders() => list('/api/orders');
  Future<Json> order(int id) => object('GET', '/api/orders/$id');
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

  Future<Json> simulatePayment(int id, bool approve) =>
      object('PUT', '/api/payments/$id/${approve ? 'approve' : 'reject'}');
  Future<List<Json>> reservations() => list('/api/reservations');
  Future<List<Json>> reservationAvailability() =>
      list('/api/reservations/availability');
  Future<void> reserve(int inventory, int quantity) async {
    await api.request('POST', '/api/reservations',
        {'id_inventario': inventory, 'cantidad': quantity});
  }

  Future<void> cancelReservation(int id) async {
    await api.request('PUT', '/api/reservations/$id', {'estado': 'CANCELADA'});
  }

  Future<Json> profile() => object('GET', '/api/users/profile');
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
    return Map<String, dynamic>.from(await api.multipart('/api/experience/virtual-try-on', {'product_id': '$productId', 'variant_id': '$variantId'}, await photo.readAsBytes(), photo.name, mime) as Map);
  }
  Future<void> preference(String type, int product, [int? variant]) async {
    await api.request('POST', '/api/experience/preferences',
        {'tipo': type, 'id_producto': product, 'id_variante': variant});
  }
}
