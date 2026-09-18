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
            colorScheme: ColorScheme.fromSeed(
                seedColor: const Color(0xff0d5848),
                brightness: Brightness.light,
                surface: const Color(0xfffffdf8)),
            scaffoldBackgroundColor: const Color(0xfff4f3ee),
            textTheme: ThemeData.light().textTheme.copyWith(
                headlineSmall: const TextStyle(
                    fontFamily: 'serif', fontWeight: FontWeight.w600, color: Color(0xff1c2c27)),
                titleLarge: const TextStyle(fontWeight: FontWeight.w700, color: Color(0xff1c2c27))),
            cardTheme: CardThemeData(
                elevation: 0,
                color: const Color(0xfffffdf8),
                margin: const EdgeInsets.symmetric(vertical: 6),
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(18),
                    side: const BorderSide(color: Color(0xffdce3df)))),
            inputDecorationTheme: InputDecorationTheme(
                filled: true,
                fillColor: const Color(0xfffffdf8),
                contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: Color(0xffcbd6d0))),
                focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: Color(0xff0d5848), width: 2))),
            appBarTheme: const AppBarTheme(centerTitle: false, backgroundColor: Color(0xfffffdf8), foregroundColor: Color(0xff1c2c27), elevation: 0),
            navigationBarTheme: NavigationBarThemeData(
                indicatorColor: const Color(0xffd8e9df),
                labelTextStyle: WidgetStateProperty.all(const TextStyle(fontWeight: FontWeight.w600, fontSize: 12)))),
        home: ClientHome(repository: repository, sessionStore: sessionStore),
      );
}
