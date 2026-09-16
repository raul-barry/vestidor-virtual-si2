import 'package:flutter/material.dart';
import '../services/api_client.dart';

class ClientHome extends StatefulWidget {
  const ClientHome({super.key});
  @override
  State<ClientHome> createState() => _ClientHomeState();
}

class _ClientHomeState extends State<ClientHome> {
  final api = ApiClient();
  final email = TextEditingController();
  final password = TextEditingController();
  final firstName = TextEditingController();
  final lastName = TextEditingController();
  final phone = TextEditingController();
  final search = TextEditingController();
  final size = TextEditingController();
  final color = TextEditingController();
  final category = TextEditingController();
  final resetToken = TextEditingController();
  late final server = TextEditingController(text: api.baseUrl);
  bool busy = false;
  bool register = false;
  String page = 'Catálogo';
  String message = '';
  List<dynamic> rows = [];
  List<dynamic> availability = [];
  Map<String, dynamic> cart = {};
  Map<String, dynamic>? product;
  Map<String, dynamic>? fitting;
  int? variantId;
  int? inventoryId;
  int quantity = 1;
  String paymentMethod = 'QR';
  double garmentScale = 1;
  double garmentOffset = 0;

  Future<void> run(Future<void> Function() action) async {
    if (busy) return;
    setState(() { busy = true; message = ''; });
    try { await action(); }
    catch (e) { if (mounted) setState(() => message = e.toString().replaceFirst('Exception: ', '')); }
    finally { if (mounted) setState(() => busy = false); }
  }

  Future<void> load() async {
    switch (page) {
      case 'Catálogo':
        final query = Uri(queryParameters: {'nombre': search.text, 'talla': size.text, 'color': color.text, 'categoria': category.text}).query;
        rows = await api.request('GET', '/api/catalog/products/search?$query');
      case 'Carrito':
        cart = Map<String,dynamic>.from(await api.request('GET', '/api/cart'));
      case 'Pedidos':
        rows = await api.request('GET', '/api/orders');
      case 'Reservas':
        rows = await api.request('GET', '/api/reservations');
        availability = await api.request('GET', '/api/reservations/availability');
        if (!availability.any((i) => i['id_inventario'] == inventoryId)) inventoryId = null;
      case 'Recomendaciones':
        final query = Uri(queryParameters: {'talla': size.text, 'color': color.text, 'categoria': category.text}).query;
        rows = await api.request('GET', '/api/experience/recommendations?$query');
      case 'Vestidor':
        rows = await api.request('GET', '/api/experience/fitting');
        if (!rows.any((r) => r['id_variante'] == variantId)) variantId = null;
      case 'Perfil':
        final profile = await api.request('GET', '/api/users/profile');
        firstName.text = profile['nombres']; lastName.text = profile['apellidos']; phone.text = profile['telefono'] ?? '';
      default:
        break;
    }
    if (mounted) setState(() {});
  }

  void go(String destination) {
    if (busy) return;
    setState(() { page = destination; rows = []; product = null; fitting = null; variantId = null; });
    run(load);
  }

  Future<void> authenticate() async {
    final uri = Uri.tryParse(server.text.trim());
    if (uri == null || !['http', 'https'].contains(uri.scheme) || uri.host.isEmpty) throw Exception('URL de API inválida');
    api.baseUrl = server.text.trim();
    if (email.text.isEmpty || password.text.length < 8) throw Exception('Ingrese correo y contraseña de al menos 8 caracteres');
    if (register) await api.request('POST', '/api/auth/register', {'nombres': firstName.text, 'apellidos': lastName.text, 'correo': email.text.trim(), 'password': password.text});
    final response = await api.request('POST', '/api/auth/login', {'correo': email.text.trim(), 'password': password.text});
    api.token = response['access_token'];
    if (response['rol'] != 'CLIENTE') {
      await api.request('POST', '/api/auth/logout'); api.token = null;
      throw Exception('Use la aplicación web para administrar la tienda');
    }
    password.clear(); page = 'Catálogo'; await load();
  }

  Future<void> detail(dynamic row) async {
    final result = await api.request('GET', '/api/catalog/products/${row['id_producto']}/variants');
    final stock = await api.request('GET', '/api/catalog/products/${row['id_producto']}/availability');
    product = {...Map<String,dynamic>.from(row), ...Map<String,dynamic>.from(result)};
    availability = stock['disponibilidad']; variantId = null; page = 'Detalle';
  }

  Future<void> add(int id) async {
    await api.request('POST', '/api/cart/items', {'id_variante': id, 'cantidad': quantity});
    message = 'Prenda agregada al carrito';
  }

  Future<void> pay(dynamic order) async {
    dynamic payment;
    try { payment = await api.request('GET', '/api/payments/order/${order['id_pedido']}'); }
    on ApiException catch (e) { if (e.status != 404) rethrow; }
    payment ??= await api.request('POST', '/api/payments', {'id_pedido': order['id_pedido'], 'metodo_pago': paymentMethod});
    if (payment['estado'] == 'RECHAZADO') payment = await api.request('POST', '/api/payments', {'id_pedido': order['id_pedido'], 'metodo_pago': paymentMethod});
    if (payment['estado'] != 'PENDIENTE') { message = 'Pago ${payment['estado']}'; return; }
    if (!mounted) return;
    final approve = await showDialog<bool>(context: context, builder: (context) => AlertDialog(
      title: const Text('Pago de demostración'),
      content: Text('Pedido #${order['id_pedido']} · Bs ${order['total']}\nNo se realiza un cobro real.'),
      actions: [TextButton(onPressed: () => Navigator.pop(context), child: const Text('Volver')),
        TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Simular rechazo')),
        FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Simular aprobación'))]));
    if (approve == null) return;
    await api.request('PUT', '/api/payments/${payment['id_pago']}/${approve ? 'approve' : 'reject'}');
    await load(); message = approve ? 'Pago aprobado e inventario actualizado' : 'Pago rechazado';
  }

  Widget field(String label, TextEditingController controller, {bool secret = false}) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 6),
    child: TextField(controller: controller, obscureText: secret, enabled: !busy,
      decoration: InputDecoration(labelText: label, border: const OutlineInputBorder())));

  Widget button(String label, Future<void> Function() action) => Padding(padding: const EdgeInsets.all(4),
    child: FilledButton(onPressed: busy ? null : () => run(action), child: Text(label)));

  Widget filters({bool withSearch = true}) => Column(children: [
    if (withSearch) field('Buscar prenda', search),
    Row(children: [Expanded(child: field('Talla', size)), const SizedBox(width: 8), Expanded(child: field('Color', color))]),
    field('Categoría', category), button(withSearch ? 'Buscar y filtrar' : 'Recomendar', load)]);

  Widget quantityPicker() => Row(children: [const Text('Cantidad: '), IconButton(onPressed: busy || quantity <= 1 ? null : () => setState(() => quantity--), icon: const Icon(Icons.remove)),
    Text('$quantity'), IconButton(onPressed: busy || quantity >= 100 ? null : () => setState(() => quantity++), icon: const Icon(Icons.add))]);

  List<Widget> content() {
    switch (page) {
      case 'Catálogo':
        return [filters(), for (final r in rows) Card(child: ListTile(title: Text(r['nombre']), subtitle: Text('${r['categoria']['nombre']} · Bs ${r['precio_base']}'),
          trailing: const Icon(Icons.chevron_right), onTap: busy ? null : () => run(() => detail(r)))), if (rows.isEmpty) const Text('No hay prendas para estos filtros.')];
      case 'Detalle':
        final p = product!;
        return [Text(p['nombre_producto'], style: Theme.of(context).textTheme.headlineSmall), Text(p['descripcion'] ?? ''),
          DropdownButtonFormField<int>(initialValue: variantId, isExpanded: true, decoration: const InputDecoration(labelText: 'Talla y color'),
            items: [for (final v in p['variantes']) DropdownMenuItem(value: v['id_variante'] as int, child: Text('${v['talla']} · ${v['color']}'))],
            onChanged: busy ? null : (v) => setState(() => variantId = v)), quantityPicker(),
          if (variantId != null) button('Agregar al carrito', () => add(variantId!)),
          const Text('Disponibilidad por sucursal'), for (final i in availability) ListTile(title: Text(i['nombre_sucursal']), subtitle: Text('${i['direccion']} · stock ${i['stock_disponible']}')),
          TextButton(onPressed: busy ? null : () => go('Reservas'), child: const Text('Reservar por talla, color y sucursal')),
          TextButton(onPressed: busy ? null : () => go('Catálogo'), child: const Text('Volver al catálogo'))];
      case 'Carrito':
        return [for (final i in cart['items'] ?? []) Card(child: Column(children: [
          ListTile(title: Text(i['producto']), subtitle: Text('${i['talla']} · ${i['color']} · Bs ${i['precio_unitario']} × ${i['cantidad']}')),
          Wrap(children: [button('−', () async { if(i['cantidad'] > 1) { await api.request('PUT', '/api/cart/items/${i['id_detalle']}', {'cantidad': i['cantidad'] - 1}); await load(); }}),
            button('+', () async { await api.request('PUT', '/api/cart/items/${i['id_detalle']}', {'cantidad': i['cantidad'] + 1}); await load(); }),
            button('Quitar', () async { await api.request('DELETE', '/api/cart/items/${i['id_detalle']}'); await load(); })])])),
          Text('Total: Bs ${cart['total'] ?? 0}'),
          if ((cart['items'] as List? ?? []).isNotEmpty) button('Confirmar compra', () async { final order = await api.request('POST', '/api/orders'); page = 'Pedidos'; await load(); message = 'Pedido #${order['id_pedido']} creado. Seleccione pagar.'; })];
      case 'Pedidos':
        return [DropdownButton<String>(value: paymentMethod, items: [for(final m in ['QR','TARJETA','EFECTIVO']) DropdownMenuItem(value:m, child:Text(m))], onChanged: busy ? null : (m)=>setState(()=>paymentMethod=m!)),
          for(final o in rows) Card(child: ExpansionTile(title: Text('Pedido #${o['id_pedido']} · ${o['estado']}'), subtitle:Text('Bs ${o['total']} · ${o['fecha_pedido']}'),
            children:[for(final d in o['detalles']) ListTile(title:Text(d['producto']),subtitle:Text('${d['talla']} · ${d['color']} · ${d['cantidad']} × Bs ${d['precio_unitario']}')),
              if(o['estado']=='PENDIENTE') button('Pagar (simulación)',()=>pay(o))])),if(rows.isEmpty) const Text('Todavía no hay pedidos.')];
      case 'Reservas':
        return [DropdownButtonFormField<int>(initialValue: inventoryId,isExpanded:true,decoration:const InputDecoration(labelText:'Prenda y sucursal'),
          items:[for(final i in availability) DropdownMenuItem(value:i['id_inventario'] as int,child:Text('${i['producto']} · ${i['talla']} · ${i['color']} · ${i['sucursal']} (${i['disponible']})',overflow:TextOverflow.ellipsis))],
          onChanged:busy?null:(v)=>setState(()=>inventoryId=v)),quantityPicker(),
          if(inventoryId!=null) button('Reservar',()async{await api.request('POST','/api/reservations',{'id_inventario':inventoryId,'cantidad':quantity});await load();message='Reserva creada';}),
          for(final r in rows) Card(child:Column(children:[ListTile(title:Text('${r['producto']} · ${r['estado']}'),subtitle:Text('${r['sucursal']} · ${r['talla']} · ${r['color']} · ${r['cantidad']} unidades')),
            if(r['estado']!='CANCELADA') button('Cancelar reserva',()async{await api.request('PUT','/api/reservations/${r['id_reserva']}',{'estado':'CANCELADA'});await load();})]))];
      case 'Recomendaciones':
        return [filters(withSearch:false),for(final r in rows) Card(child:Column(children:[ListTile(title:Text(r['nombre']),subtitle:Text('${r['talla']} · ${r['color']} · Bs ${r['precio']}\n${r['motivo']}')),
          button('Ver prenda',()=>detail(r)),button('Agregar al carrito',()=>add(r['id_variante']))]))];
      case 'Vestidor':
        return [const Text('Vista orientativa sobre maniquí. Selecciona una prenda y ajusta su tamaño.'),
          DropdownButtonFormField<int>(initialValue:variantId,isExpanded:true,items:[for(final r in rows) DropdownMenuItem(value:r['id_variante'] as int,child:Text('${r['nombre']} · ${r['talla']} · ${r['color']}',overflow:TextOverflow.ellipsis))],onChanged:busy?null:(v)=>setState(()=>variantId=v)),
          if(variantId!=null) button('Probar prenda',()async{fitting=Map<String,dynamic>.from(await api.request('POST','/api/experience/fitting',{'id_variante':variantId}));}),
          const Text('Tamaño'),Slider(value:garmentScale,min:.5,max:1.8,onChanged:(v)=>setState(()=>garmentScale=v)),
          const Text('Posición vertical'),Slider(value:garmentOffset,min:-60,max:100,onChanged:(v)=>setState(()=>garmentOffset=v)),
          SizedBox(height:400,child:CustomPaint(painter:FittingPainter(fitting,garmentScale,garmentOffset),child:const SizedBox.expand())),
          if(fitting!=null) button('Agregar al carrito',()=>add(fitting!['id_variante']))];
      case 'Perfil':
        return [field('Nombres',firstName),field('Apellidos',lastName),field('Teléfono',phone),button('Guardar perfil',()async{await api.request('PUT','/api/users/profile',{'nombres':firstName.text,'apellidos':lastName.text,if(phone.text.isNotEmpty)'telefono':phone.text});message='Perfil actualizado';})];
      default:return [];
    }
  }

  @override
  Widget build(BuildContext context) {
    final loggedIn = api.token != null;
    return Scaffold(appBar:AppBar(title:Text(loggedIn?page:'Vestidor Virtual'),actions:[if(loggedIn)IconButton(onPressed:busy?null:()=>run(load),icon:const Icon(Icons.refresh))]),
      drawer:loggedIn?Drawer(child:SafeArea(child:ListView(children:[for(final destination in ['Catálogo','Carrito','Pedidos','Reservas','Recomendaciones','Vestidor','Perfil'])
        ListTile(title:Text(destination),onTap:busy?null:(){Navigator.pop(context);go(destination);}),
        ListTile(title:const Text('Cerrar sesión'),onTap:busy?null:(){Navigator.pop(context);run(()async{try{await api.request('POST','/api/auth/logout');}finally{api.token=null;rows=[];cart={};product=null;fitting=null;}});})]))):null,
      body:SafeArea(child:ListView(padding:const EdgeInsets.all(16),children:[if(busy)const LinearProgressIndicator(),if(message.isNotEmpty)Padding(padding:const EdgeInsets.all(12),child:Text(message)),
        if(loggedIn)...content() else ...[
          field('Servidor API (en emulador Android: http://10.0.2.2:8000)',server),field('Correo',email),field('Contraseña',password,secret:true),
          if(register)...[field('Nombres',firstName),field('Apellidos',lastName)],button(register?'Registrarse':'Iniciar sesión',authenticate),
          TextButton(onPressed:busy?null:()=>setState(()=>register=!register),child:Text(register?'Ya tengo cuenta':'Crear cuenta')),
          ExpansionTile(title:const Text('Recuperar contraseña'),children:[button('Solicitar token de desarrollo',()async{api.baseUrl=server.text.trim();final r=await api.request('POST','/api/auth/request-password-reset',{'correo':email.text.trim()});resetToken.text=r['token']??'';message=r['message'];}),field('Token de recuperación',resetToken),
            button('Restablecer con la contraseña indicada arriba',()async{await api.request('POST','/api/auth/reset-password',{'token':resetToken.text,'nueva_password':password.text});message='Contraseña actualizada';})])]])));
  }

  @override
  void dispose(){api.dispose();for(final c in [email,password,firstName,lastName,phone,search,size,color,category,resetToken,server]){c.dispose();}super.dispose();}
}

class FittingPainter extends CustomPainter {
  FittingPainter(this.garment,this.scale,this.offset);
  final Map<String,dynamic>? garment;
  final double scale;
  final double offset;
  @override
  void paint(Canvas canvas,Size size){
    canvas.translate(size.width/2,0);
    final body=Paint()..color=const Color(0xffb7bfca);
    canvas.drawCircle(const Offset(0,40),28,body);
    canvas.drawRRect(RRect.fromRectAndRadius(const Rect.fromLTWH(-40,75,80,155),const Radius.circular(20)),body);
    canvas.drawRect(const Rect.fromLTWH(-38,210,30,175),body);canvas.drawRect(const Rect.fromLTWH(8,210,30,175),body);
    canvas.drawRect(const Rect.fromLTWH(-65,90,25,145),body);canvas.drawRect(const Rect.fromLTWH(40,90,25,145),body);
    if(garment==null)return;
    final colors={'azul':Colors.blue.shade800,'negro':Colors.black87,'blanco':Colors.white,'gris':Colors.grey,'verde':Colors.green.shade700,'rojo':Colors.red};
    final paint=Paint()..color=colors['${garment!['color']}'.toLowerCase()]??Colors.purple;
    final pants=garment!['garment']=='pants';canvas.translate(0,(pants?205:80)+offset);canvas.scale(scale);
    final path=Path();
    if(pants){path.moveTo(-42,0);path.lineTo(42,0);path.lineTo(48,180);path.lineTo(10,180);path.lineTo(0,55);path.lineTo(-10,180);path.lineTo(-48,180);}
    else{path.moveTo(-35,0);path.lineTo(-15,-8);path.quadraticBezierTo(0,12,15,-8);path.lineTo(35,0);path.lineTo(80,38);path.lineTo(58,64);path.lineTo(40,45);path.lineTo(40,145);path.lineTo(-40,145);path.lineTo(-40,45);path.lineTo(-58,64);path.lineTo(-80,38);}
    path.close();canvas.drawPath(path,paint);canvas.drawPath(path,Paint()..color=Colors.black54..style=PaintingStyle.stroke..strokeWidth=2);
  }
  @override
  bool shouldRepaint(covariant FittingPainter oldDelegate)=>oldDelegate.garment!=garment||oldDelegate.scale!=scale||oldDelegate.offset!=offset;
}
