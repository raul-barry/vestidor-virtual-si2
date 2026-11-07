import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:vestidor_virtual_mobile/services/stripe_payment_sheet_service.dart';

class FakePaymentSheetDriver implements PaymentSheetDriver {
  final calls = <String>[];
  String? key;
  String? secret;
  String? merchant;
  String? returnUrl;
  Object? failure;
  Completer<void>? presentGate;

  @override
  Future<void> configure(String publishableKey) async {
    calls.add('configure');
    key = publishableKey;
  }

  @override
  Future<void> initialize({
    required String paymentIntentClientSecret,
    required String merchantDisplayName,
    required String returnURL,
  }) async {
    calls.add('initialize');
    secret = paymentIntentClientSecret;
    merchant = merchantDisplayName;
    returnUrl = returnURL;
  }

  @override
  Future<void> present() async {
    calls.add('present');
    if (presentGate != null) await presentGate!.future;
    if (failure != null) throw failure!;
  }
}

void main() {
  test('configures and initializes PaymentSheet with the server intent', () async {
    final driver = FakePaymentSheetDriver();
    await StripePaymentSheetService(driver: driver).pay(
      publishableKey: 'pk_test_mock',
      paymentIntentClientSecret: 'pi_test_secret',
    );

    expect(driver.calls, ['configure', 'initialize', 'present']);
    expect(driver.key, 'pk_test_mock');
    expect(driver.secret, 'pi_test_secret');
    expect(driver.merchant, 'FashionStore');
    expect(driver.returnUrl, 'flutterstripe://redirect');
  });

  test('successful presentation completes normally', () async {
    final driver = FakePaymentSheetDriver();
    await expectLater(
      StripePaymentSheetService(driver: driver).pay(
        publishableKey: 'pk_test_mock',
        paymentIntentClientSecret: 'pi_secret',
      ),
      completes,
    );
  });

  for (final scenario in <String, Object>{
    'cancellation': StateError('Canceled'),
    'provider rejection': StateError('Payment rejected'),
    'connection failure': const _ConnectionFailure(),
  }.entries) {
    test('propagates ${scenario.key} without claiming payment success', () async {
      final driver = FakePaymentSheetDriver()..failure = scenario.value;
      await expectLater(
        StripePaymentSheetService(driver: driver).pay(
          publishableKey: 'pk_test_mock',
          paymentIntentClientSecret: 'pi_secret',
        ),
        throwsA(same(scenario.value)),
      );
    });
  }

  test('an interrupted attempt can retry the same PaymentIntent', () async {
    final driver = FakePaymentSheetDriver()
      ..failure = const _ConnectionFailure();
    final service = StripePaymentSheetService(driver: driver);
    await expectLater(
      service.pay(
        publishableKey: 'pk_test_mock',
        paymentIntentClientSecret: 'pi_same_secret',
      ),
      throwsA(isA<_ConnectionFailure>()),
    );
    driver.failure = null;
    await service.pay(
      publishableKey: 'pk_test_mock',
      paymentIntentClientSecret: 'pi_same_secret',
    );
    expect(driver.calls.where((call) => call == 'present'), hasLength(2));
    expect(driver.secret, 'pi_same_secret');
  });

  test('concurrent duplicate taps share one PaymentSheet presentation', () async {
    final gate = Completer<void>();
    final driver = FakePaymentSheetDriver()..presentGate = gate;
    final service = StripePaymentSheetService(driver: driver);
    final first = service.pay(
      publishableKey: 'pk_test_mock',
      paymentIntentClientSecret: 'pi_same_secret',
    );
    final second = service.pay(
      publishableKey: 'pk_test_mock',
      paymentIntentClientSecret: 'pi_same_secret',
    );

    await Future<void>.delayed(Duration.zero);
    // Future wrappers need not be identical; verify the operation itself was
    // only configured, initialized, and presented once.
    expect(driver.calls.where((call) => call == 'configure'), hasLength(1));
    expect(driver.calls.where((call) => call == 'initialize'), hasLength(1));
    expect(driver.calls.where((call) => call == 'present'), hasLength(1));
    gate.complete();
    await Future.wait([first, second]);
  });
}

class _ConnectionFailure implements Exception {
  const _ConnectionFailure();
}
