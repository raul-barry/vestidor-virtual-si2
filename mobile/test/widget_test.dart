import 'package:flutter_test/flutter_test.dart';
import 'package:vestidor_virtual_mobile/main.dart';

void main() {
  testWidgets('Client opens login and can switch to registration', (tester) async {
    await tester.pumpWidget(const VestidorVirtualApp());
    expect(find.text('Iniciar sesión'), findsOneWidget);
    await tester.tap(find.text('Crear cuenta'));
    await tester.pumpAndSettle();
    expect(find.text('Nombres'), findsOneWidget);
    expect(find.text('Apellidos'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
