import 'package:flutter/material.dart';
import 'features/client_app.dart';
import 'services/client_repository.dart';
import 'services/session_store.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const VestidorVirtualApp());
}

class VestidorVirtualApp extends StatelessWidget {
  const VestidorVirtualApp({super.key, this.repository, this.sessionStore});
  final ClientRepository? repository;
  final SessionStore? sessionStore;
  @override
  Widget build(BuildContext context) => MaterialApp(
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
            useMaterial3: true,
            colorScheme:
                ColorScheme.fromSeed(seedColor: const Color(0xff00695c)),
            scaffoldBackgroundColor: const Color(0xfff6f5f1),
            inputDecorationTheme:
                const InputDecorationTheme(border: OutlineInputBorder()),
            appBarTheme: const AppBarTheme(centerTitle: false)),
        home: ClientHome(repository: repository, sessionStore: sessionStore),
      );
}
