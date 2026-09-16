import 'package:flutter/material.dart';
import 'features/client_app.dart';

void main() {
  runApp(const VestidorVirtualApp());
}

class VestidorVirtualApp extends StatelessWidget {
  const VestidorVirtualApp({super.key});

  @override
  Widget build(BuildContext context) {
    return const MaterialApp(
      debugShowCheckedModeBanner: false,
      home: ClientHome(),
    );
  }
}
