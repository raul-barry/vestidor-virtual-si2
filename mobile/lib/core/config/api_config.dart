import 'package:flutter/foundation.dart';

class ApiConfig {
  const ApiConfig._();
  static String get baseUrl =>
      const String.fromEnvironment('API_BASE_URL').isNotEmpty
          ? const String.fromEnvironment('API_BASE_URL')
          : !kIsWeb && defaultTargetPlatform == TargetPlatform.android
              ? 'http://10.0.2.2:8000'
              : 'http://localhost:8000';
  static const paymentDemo =
      bool.fromEnvironment('PAYMENT_DEMO', defaultValue: true);
}
