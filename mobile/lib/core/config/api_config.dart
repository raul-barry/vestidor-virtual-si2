import 'package:flutter/foundation.dart';

class ApiConfig {
  const ApiConfig._();
  static const baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://vestidor-virtual-backend.onrender.com',
  );
  static const allowInsecureApi = bool.fromEnvironment(
    'ALLOW_INSECURE_API',
    defaultValue: kDebugMode,
  );
  static const paymentDemo =
      bool.fromEnvironment('PAYMENT_DEMO', defaultValue: false);
}
