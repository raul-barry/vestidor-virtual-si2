import 'package:flutter/material.dart';
import '../core/config/api_config.dart';
import '../services/api_client.dart';
import '../services/client_repository.dart';
import '../services/client_session.dart';
import '../services/session_store.dart';
import 'fitting_painter.dart';

class ClientHome extends StatefulWidget {
  const ClientHome({super.key, this.repository, this.sessionStore});
  final ClientRepository? repository;
  final SessionStore? sessionStore;
  @override
  State<ClientHome> createState() => _ClientHomeState();
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
  late final TextEditingController server;
  bool busy = false;
  bool register = false;
  bool failed = false;
  String page = 'Catálogo';
  String message = '';
  List<Json> rows = [];
  List<Json> availability = [];
  Json cart = {};
  Json? product;
  Json? fitting;
  Json? selectedOrder;
  Json? paymentInfo;
  int? variantId;
  int? inventoryId;
  int quantity = 1;
  String paymentMethod = 'QR';
  String profileEmail = '';
  double garmentScale = 1;
  double garmentOffset = 0;
  bool _wasSignedIn = false;

  @override
  void initState() {
    super.initState();
    repository = widget.repository ?? ClientRepository(ApiClient());
    server = TextEditingController(text: repository.api.baseUrl);
    session = ClientSession(
        repository, widget.sessionStore ?? const SecureSessionStore());
    session.addListener(sessionChanged);
    restore();
  }

  Future<void> restore() async {
    await session.restore();
    if (!mounted) return;
    server.text = repository.api.baseUrl;
    if (session.signedIn) await run(load);
  }

  void clearClientData() {
    rows = [];
    availability = [];
    cart = {};
    product = null;
    fitting = null;
    selectedOrder = null;
    paymentInfo = null;
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

  void sessionChanged() {
    if (!mounted) return;
    setState(() {
      if (_wasSignedIn && !session.signedIn) {
        Navigator.of(context).popUntil((route) => route.isFirst);
        clearClientData();
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
        rows = await repository.catalog(filterValues);
      case 'Carrito':
        cart = await repository.cart();
      case 'Pedidos':
        rows = await repository.orders();
      case 'Pedido':
        final id = selectedOrder!['id_pedido'] as int;
        selectedOrder = await repository.order(id);
        paymentInfo = await repository.payment(id);
      case 'Reservas':
        rows = await repository.reservations();
        availability = await repository.reservationAvailability();
        if (!availability.any((i) => i['id_inventario'] == inventoryId)) {
          inventoryId = null;
        }
      case 'Recomendaciones':
        rows = await repository.recommendations({
          'talla': size.text,
          'color': color.text,
          'categoria': category.text
        });
      case 'Vestidor':
        rows = await repository.fittingVariants();
        if (!rows.any((r) => r['id_variante'] == variantId)) {
          variantId = null;
          fitting = null;
        }
      case 'Perfil':
        final profile = await repository.profile();
        if (!mounted) return;
        firstName.text = profile['nombres'];
        lastName.text = profile['apellidos'];
        phone.text = profile['telefono'] ?? '';
        profileEmail = profile['correo'];
      case 'Detalle':
        if (product != null) await detail(product!);
    }
  }

  Future<void> go(String destination) async {
    if (busy) return;
    setState(() {
      page = destination;
      rows = [];
      availability = [];
      product = null;
      fitting = null;
      selectedOrder = null;
      paymentInfo = null;
      variantId = null;
      inventoryId = null;
      quantity = 1;
    });
    await run(load);
  }

  Future<void> authenticate() async {
    if (!email.text.trim().contains('@') || password.text.isEmpty) {
      throw ApiException(0, 'Ingresa un correo válido y tu contraseña.');
    }
    repository.api.baseUrl = ClientSession.validateServer(server.text);
    if (register) {
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
      });
      register = false;
    }
    await session.login(server.text, email.text, password.text);
    if (!mounted) return;
    password.clear();
    page = 'Catálogo';
    rows = [];
    await load();
  }

  Future<void> logout() async {
    try {
      await session.logout();
    } on ApiException {
      message =
          'Sesión cerrada en este dispositivo. No fue posible contactar al servidor.';
    }
  }

  Future<void> detail(Json row) async {
    final result = await repository.variants(row['id_producto'] as int);
    final stock = await repository.availability(row['id_producto'] as int);
    product = {...row, ...result};
    availability = (stock['disponibilidad'] as List)
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
    variantId = null;
    quantity = 1;
    page = 'Detalle';
  }

  Future<void> add(int id, [int? count]) async {
    await repository.addItem(id, count ?? quantity);
    message = 'Prenda agregada al carrito';
  }

  Future<void> openOrder(Json order) async {
    final detail = await repository.order(order['id_pedido'] as int);
    selectedOrder = detail;
    paymentInfo = null;
    page = 'Pedido';
    paymentInfo = await repository.payment(order['id_pedido'] as int);
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
    });
  }

  Future<void> pay() async {
    await run(() async {
      final order = selectedOrder!;
      paymentInfo = await repository.preparePayment(
          order['id_pedido'] as int, paymentMethod);
      if (paymentInfo!['estado'] != 'PENDIENTE') {
        message = 'Pago ${paymentInfo!['estado']}';
        await load();
      }
    });
    if (paymentInfo == null || paymentInfo!['estado'] != 'PENDIENTE') return;

    if (!ApiConfig.paymentDemo) {
      if (mounted) {
        setState(() {
          message =
              'Pago registrado y pendiente de confirmación. No se ha realizado un cobro.';
        });
      }
      return;
    }
    if (!mounted) return;
    final order = selectedOrder!;
    final approve = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
                title: const Text('Pago de demostración'),
                content: Text(
                    'Pedido #${order['id_pedido']} · Bs ${paymentInfo!['monto']}\nMétodo: ${paymentInfo!['metodo_pago']}\nNo se realiza ningún cobro real.'),
                actions: [
                  TextButton(
                      onPressed: () => Navigator.pop(context),
                      child: const Text('Más tarde')),
                  TextButton(
                      onPressed: () => Navigator.pop(context, false),
                      child: const Text('Simular rechazo')),
                  FilledButton(
                      onPressed: () => Navigator.pop(context, true),
                      child: const Text('Simular aprobación'))
                ]));
    if (approve == null) return;
    await run(() async {
      await repository.simulatePayment(paymentInfo!['id_pago'] as int, approve);
      await load();
      message = approve
          ? 'Pago aprobado. Compra confirmada.'
          : 'Pago rechazado. Puedes intentarlo desde este pedido.';
    });
  }

  Future<void> saveProfile() async {
    if (firstName.text.trim().isEmpty || lastName.text.trim().isEmpty) {
      throw ApiException(0, 'Nombres y apellidos son obligatorios.');
    }
    await repository.updateProfile({
      'nombres': firstName.text.trim(),
      'apellidos': lastName.text.trim(),
      'telefono': phone.text.trim().isEmpty ? null : phone.text.trim()
    });
    await load();
    message = 'Perfil actualizado';
  }

  Widget field(String label, TextEditingController controller,
          {bool secret = false, TextInputType? keyboard, int? limit}) =>
      Padding(
          padding: const EdgeInsets.symmetric(vertical: 8),
          child: TextField(
              controller: controller,
              obscureText: secret,
              enabled: !busy,
              keyboardType: keyboard,
              maxLength: limit,
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
          initiallyExpanded: true,
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

  List<Widget> content() {
    switch (page) {
      case 'Catálogo':
        return [
          Text('Encuentra tu próxima prenda',
              style: Theme.of(context).textTheme.headlineSmall),
          filters(),
          for (final r in rows)
            Card(
                child: ListTile(
                    leading: const Icon(Icons.checkroom),
                    title: Text(r['nombre']),
                    subtitle: Text(
                        '${r['categoria']['nombre']} · Bs ${r['precio_base']}'),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: busy ? null : () => run(() => detail(r)))),
          if (rows.isEmpty && !busy && !failed)
            empty('No hay prendas para estos filtros.')
        ];
      case 'Detalle':
        final p = product!;
        return [
          Text(p['nombre_producto'],
              style: Theme.of(context).textTheme.headlineSmall),
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
          const Text('Disponibilidad del producto por sucursal'),
          for (final i in availability)
            ListTile(
                title: Text(i['nombre_sucursal']),
                subtitle:
                    Text('${i['direccion']} · stock ${i['stock_disponible']}')),
          button('Guardar como favorito', () async {
            await repository.preference('favorita', p['id_producto'] as int);
            message = 'Preferencia guardada';
          }),
          TextButton(
              onPressed: busy ? null : () => go('Reservas'),
              child: const Text('Reservar por talla, color y sucursal')),
          TextButton(
              onPressed: busy ? null : () => go('Vestidor'),
              child: const Text('Abrir vestidor virtual')),
          TextButton(
              onPressed: busy ? null : () => go('Catálogo'),
              child: const Text('Volver al catálogo'))
        ];
      case 'Carrito':
        final items = cart['items'] as List? ?? [];
        return [
          for (final i in items)
            Card(
                child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(children: [
                      ListTile(
                          title: Text(i['producto']),
                          subtitle: Text(
                              '${i['talla']} · ${i['color']} · Bs ${i['precio_unitario']} × ${i['cantidad']}')),
                      Wrap(children: [
                        button('Reducir', () async {
                          await repository.changeQuantity(
                              i['id_detalle'], i['cantidad'] - 1);
                          await load();
                        }, enabled: i['cantidad'] > 1),
                        button('Aumentar', () async {
                          await repository.changeQuantity(
                              i['id_detalle'], i['cantidad'] + 1);
                          await load();
                        }),
                        button('Quitar', () async {
                          await repository.removeItem(i['id_detalle']);
                          await load();
                        })
                      ])
                    ]))),
          if (items.isEmpty && !busy && !failed)
            empty('Tu carrito está vacío.'),
          Text('Total: Bs ${cart['total'] ?? '0.00'}',
              style: Theme.of(context).textTheme.titleLarge),
          if (items.isNotEmpty) ...[
            const SizedBox(height: 20),
            paymentPicker(),
            button('Confirmar compra', checkout, autoRun: false)
          ]
        ];
      case 'Pedidos':
        return [
          for (final o in rows)
            Card(
                child: ListTile(
                    title: Text('Pedido #${o['id_pedido']} · ${o['estado']}'),
                    subtitle: Text('Bs ${o['total']} · ${o['fecha_pedido']}'),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: busy ? null : () => run(() => openOrder(o)))),
          if (rows.isEmpty && !busy && !failed) empty('Todavía no hay pedidos.')
        ];
      case 'Pedido':
        final o = selectedOrder!;
        return [
          Text('Pedido #${o['id_pedido']}',
              style: Theme.of(context).textTheme.headlineSmall),
          Text('Estado: ${o['estado']}'),
          Text('Total: Bs ${o['total']}'),
          for (final d in o['detalles'] as List? ?? [])
            Card(
                child: ListTile(
                    title: Text(d['producto']),
                    subtitle: Text(
                        '${d['talla']} · ${d['color']} · ${d['cantidad']} × Bs ${d['precio_unitario']}'))),
          if (paymentInfo != null)
            Text(
                'Pago: ${paymentInfo!['estado']} · ${paymentInfo!['metodo_pago']}'),
          if (o['estado'] == 'PENDIENTE') ...[
            const SizedBox(height: 20),
            if (paymentInfo == null || paymentInfo!['estado'] == 'RECHAZADO')
              paymentPicker(),
            button(
                ApiConfig.paymentDemo
                    ? 'Pagar (demostración)'
                    : 'Registrar pago',
                pay,
                autoRun: false)
          ],
          TextButton(
              onPressed: busy ? null : () => go('Pedidos'),
              child: const Text('Volver a mis pedidos'))
        ];
      case 'Reservas':
        return [
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
            final available = availability.firstWhere(
                (i) => i['id_inventario'] == inventoryId)['disponible'] as int;
            if (quantity > available) {
              throw ApiException(0,
                  'La cantidad supera la disponibilidad mostrada. Actualiza la lista.');
            }
            await repository.reserve(inventoryId!, quantity);
            await load();
            message = 'Reserva creada';
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
              if (['PENDIENTE', 'CONFIRMADA'].contains(r['estado']))
                button('Cancelar reserva', () async {
                  if (!await confirm('Cancelar reserva',
                      'Se liberará el stock de esta reserva.')) {
                    return;
                  }
                  await run(() async {
                    await repository.cancelReservation(r['id_reserva']);
                    await load();
                    message = 'Reserva cancelada';
                  });
                }, autoRun: false)
            ])),
          if (rows.isEmpty && !busy && !failed)
            empty('Todavía no tienes reservas.')
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
          const Text(
              'Prueba orientativa sobre maniquí. La ilustración representa tipo y color; no es una fotografía ni calcula el ajuste físico.'),
          DropdownButtonFormField<int>(
              key: ValueKey('fitting-$variantId'),
              initialValue: variantId,
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
                        fitting = null;
                        garmentScale = 1;
                        garmentOffset = 0;
                      })),
          button('Probar prenda', () async {
            fitting = await repository.fit(variantId!);
          }, enabled: variantId != null),
          if (rows.isEmpty && !busy && !failed)
            empty('No hay prendas compatibles disponibles.'),
          const Text('Tamaño'),
          Slider(
              value: garmentScale,
              min: .5,
              max: 1.8,
              onChanged: busy ? null : (v) => setState(() => garmentScale = v)),
          const Text('Posición vertical'),
          Slider(
              value: garmentOffset,
              min: -60,
              max: 100,
              onChanged:
                  busy ? null : (v) => setState(() => garmentOffset = v)),
          ClipRect(
              child: SizedBox(
                  height: 400,
                  child: Semantics(
                      label: 'Maniquí con la prenda seleccionada',
                      child: CustomPaint(
                          painter: FittingPainter(
                              fitting, garmentScale, garmentOffset),
                          child: const SizedBox.expand())))),
          if (fitting != null) ...[
            Text(
                '${fitting!['nombre']} · ${fitting!['talla']} · ${fitting!['color']}'),
            button('Agregar al carrito', () => add(fitting!['id_variante'], 1))
          ]
        ];
      case 'Perfil':
        return [
          Text(profileEmail, style: Theme.of(context).textTheme.titleMedium),
          field('Nombres', firstName, limit: 100),
          field('Apellidos', lastName, limit: 100),
          field('Teléfono', phone, keyboard: TextInputType.phone, limit: 30),
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
          const Text(
              'En emulador Android: http://10.0.2.2:8000. En un teléfono, usa la IP local del servidor.')
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
                title: Text(loggedIn ? page : 'Vestidor Virtual'),
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
                        title: Text('Vestidor Virtual'),
                        subtitle: Text('Tu cuenta de cliente')),
                    for (final destination in [
                      'Catálogo',
                      'Carrito',
                      'Pedidos',
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
                                  if (loggedIn)
                                    ...content()
                                  else
                                    ...authContent(),
                                  const SizedBox(height: 24)
                                ]))))),
            bottomNavigationBar: loggedIn
                ? NavigationBar(
                    selectedIndex:
                        ['Carrito', 'Pedidos', 'Perfil'].contains(page)
                            ? ['Carrito', 'Pedidos', 'Perfil'].indexOf(page) + 1
                            : 0,
                    onDestinationSelected: busy
                        ? null
                        : (index) => go([
                              'Catálogo',
                              'Carrito',
                              'Pedidos',
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
                            icon: Icon(Icons.person_outline), label: 'Perfil')
                      ])
                : null));
  }

  @override
  void dispose() {
    session.removeListener(sessionChanged);
    session.dispose();
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
      server
    ]) {
      c.dispose();
    }
    super.dispose();
  }
}
