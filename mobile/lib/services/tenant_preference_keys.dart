class TenantPreferenceKeys {
  const TenantPreferenceKeys._();

  static String forContext({
    required String name,
    required int? organizationId,
    required String? publicSlug,
  }) {
    final scope = organizationId != null
        ? 'org_$organizationId'
        : publicSlug != null && publicSlug.isNotEmpty
            ? 'store_$publicSlug'
            : 'unselected';
    return 'style_${scope}_$name';
  }
}
