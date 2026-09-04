import 'package:flutter/material.dart';

void main() {
  runApp(const VestidorVirtualApp());
}

class VestidorVirtualApp extends StatelessWidget {
  const VestidorVirtualApp({super.key});

  @override
  Widget build(BuildContext context) {
    return const MaterialApp(
      debugShowCheckedModeBanner: false,
      home: SizedBox.shrink(),
    );
  }
}
