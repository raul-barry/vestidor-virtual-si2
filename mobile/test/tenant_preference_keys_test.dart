import 'package:flutter_test/flutter_test.dart';
import 'package:vestidor_virtual_mobile/services/tenant_preference_keys.dart';

void main() {
  test('private style preferences use the organization from the JWT scope', () {
    final fashion = TenantPreferenceKeys.forContext(
        name: 'colors', organizationId: 1, publicSlug: null);
    final urban = TenantPreferenceKeys.forContext(
        name: 'colors', organizationId: 2, publicSlug: null);
    expect(fashion, isNot(urban));
    expect(fashion, 'style_org_1_colors');
    expect(urban, 'style_org_2_colors');
  });

  test('anonymous style preferences use the selected public store slug', () {
    final fashion = TenantPreferenceKeys.forContext(
        name: 'size', organizationId: null, publicSlug: 'fashionstore');
    final elegance = TenantPreferenceKeys.forContext(
        name: 'size', organizationId: null, publicSlug: 'elegance-boutique');
    expect(fashion, isNot(elegance));
    expect(fashion, 'style_store_fashionstore_size');
  });

  test('unselected tenant does not reuse a prior company preference key', () {
    final key = TenantPreferenceKeys.forContext(
        name: 'preferred', organizationId: null, publicSlug: null);
    expect(key, 'style_unselected_preferred');
    expect(key, isNot('style_size'));
  });
}
