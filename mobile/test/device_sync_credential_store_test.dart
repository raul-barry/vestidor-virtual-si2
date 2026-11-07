import 'dart:convert';

import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vestidor_virtual_mobile/services/session_store.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  const channel = MethodChannel('plugins.it_nomads.com/flutter_secure_storage');
  final messenger =
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;
  final calls = <MethodCall>[];

  setUp(() {
    calls.clear();
    messenger.setMockMethodCallHandler(channel, (call) async {
      calls.add(call);
      if (call.method == 'read' &&
          (call.arguments as Map)['key'] ==
              'fashion_store_device_sync_credential') {
        return null;
      }
      return null;
    });
  });

  tearDown(() => messenger.setMockMethodCallHandler(channel, null));

  test('initializes secure storage and returns empty when key is absent',
      () async {
    final credentials = await SecureDeviceSyncCredentialStore().readAll();

    expect(credentials, isEmpty);
    expect(calls.map((call) => call.method), ['read']);
    expect((calls.single.arguments as Map)['key'],
        'fashion_store_device_sync_credential');
  });

  test('decodes credentials while retaining organization and user scope',
      () async {
    messenger.setMockMethodCallHandler(channel, (call) async {
      calls.add(call);
      return jsonEncode({
        '1:7': {'organization_id': 1, 'user_id': 7, 'credential': 'device'},
        '2:8': {'organization_id': 2, 'user_id': 8, 'credential': 'other'},
      });
    });

    final credentials = await SecureDeviceSyncCredentialStore().readAll();

    expect(credentials.keys, containsAll(['1:7', '2:8']));
    expect((credentials['1:7'] as Map)['organization_id'], 1);
    expect((credentials['2:8'] as Map)['user_id'], 8);
    expect(calls.single.method, 'read');
  });

  test('treats MissingPluginException as an empty credential store',
      () async {
    messenger.setMockMethodCallHandler(channel, null);

    expect(await SecureDeviceSyncCredentialStore().readAll(), isEmpty);
  });
}
