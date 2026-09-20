export interface SizePreferences { talla_superior?: string | null; talla_pantalon?: string | null; }
export interface FittingVariant { id_variante: number; talla: string; color: string; stock_disponible?: number; }

export class PreferredSizeResolver {
  static resolve(product: any, preferences: SizePreferences, variants: FittingVariant[], requested?: number) {
    if (requested) {
      const selected = variants.find(v => v.id_variante === requested);
      return { variant: selected, warning: selected ? null : 'La variante solicitada ya no está disponible.' };
    }
    const name = `${product?.nombre ?? product?.categoria ?? ''}`.toLowerCase();
    const preferred = (name.includes('pantal') ? preferences.talla_pantalon : preferences.talla_superior)?.trim();
    if (!preferred) return { variant: undefined, warning: null };
    const match = variants.find(v => v.talla.toLowerCase() === preferred.toLowerCase());
    if (!match) return { variant: undefined, warning: null };
    if (match.stock_disponible === 0) return { variant: undefined, warning: `Tu talla preferida ${preferred} no está disponible actualmente.` };
    return { variant: match, warning: null };
  }
}
