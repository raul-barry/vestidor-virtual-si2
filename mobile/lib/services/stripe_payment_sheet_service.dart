import 'package:flutter_stripe/flutter_stripe.dart';

abstract interface class PaymentSheetDriver {
  Future<void> configure(String publishableKey);
  Future<void> initialize({
    required String paymentIntentClientSecret,
    required String merchantDisplayName,
    required String returnURL,
  });
  Future<void> present();
}

class StripePaymentSheetDriver implements PaymentSheetDriver {
  @override
  Future<void> configure(String publishableKey) async {
    Stripe.publishableKey = publishableKey;
    Stripe.urlScheme = 'flutterstripe';
    await Stripe.instance.applySettings();
  }

  @override
  Future<void> initialize({
    required String paymentIntentClientSecret,
    required String merchantDisplayName,
    required String returnURL,
  }) async {
    await Stripe.instance.initPaymentSheet(
      paymentSheetParameters: SetupPaymentSheetParameters(
        paymentIntentClientSecret: paymentIntentClientSecret,
        merchantDisplayName: merchantDisplayName,
        returnURL: returnURL,
      ),
    );
  }

  @override
  Future<void> present() async {
    await Stripe.instance.presentPaymentSheet();
  }
}

/// Presents an existing server-created PaymentIntent. It never creates or
/// confirms an intent itself; retrying uses the same intent supplied by caller.
class StripePaymentSheetService {
  StripePaymentSheetService({PaymentSheetDriver? driver})
      : _driver = driver ?? StripePaymentSheetDriver();

  final PaymentSheetDriver _driver;
  Future<void>? _inFlight;

  Future<void> pay({
    required String publishableKey,
    required String paymentIntentClientSecret,
  }) {
    final active = _inFlight;
    if (active != null) return active;
    final operation = _pay(
      publishableKey: publishableKey,
      paymentIntentClientSecret: paymentIntentClientSecret,
    );
    _inFlight = operation;
    return operation.whenComplete(() => _inFlight = null);
  }

  Future<void> _pay({
    required String publishableKey,
    required String paymentIntentClientSecret,
  }) async {
    if (publishableKey.isEmpty || paymentIntentClientSecret.isEmpty) {
      throw ArgumentError('Stripe credentials are required.');
    }
    await _driver.configure(publishableKey);
    await _driver.initialize(
      paymentIntentClientSecret: paymentIntentClientSecret,
      merchantDisplayName: 'FashionStore',
      returnURL: 'flutterstripe://redirect',
    );
    await _driver.present();
  }
}
