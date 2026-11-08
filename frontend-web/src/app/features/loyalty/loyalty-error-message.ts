const FIELD_LABELS: Record<string, string> = {
  active: 'estado del programa', name: 'nombre', points_per_currency: 'puntos por cada boliviano',
  currency_per_point: 'valor de cada punto', minimum_redeem_points: 'puntos mínimos para canjear',
  max_discount_percent: 'descuento máximo', expiration_days: 'días de vencimiento',
  code: 'código del nivel', tiers: 'niveles', customer_id: 'cliente', amount: 'monto de compra',
  points: 'puntos a canjear',
};

function cleanText(value: unknown): string | null {
  if (typeof value !== 'string') return null;
  const text = value.trim();
  if (!text || /^(?:\[object Object\]|undefined|null|Internal Server Error)$/i.test(text)) return null;
  return text;
}

function validationMessage(error: Record<string, unknown>): string | null {
  const source = cleanText(error['msg']);
  if (!source) return null;
  const location = Array.isArray(error['loc'])
    ? error['loc'].filter((part): part is string => typeof part === 'string' && part !== 'body' && part !== 'query')
    : [];
  const rawField = location.at(-1);
  const field = rawField ? FIELD_LABELS[rawField] ?? rawField.replaceAll('_', ' ') : 'dato ingresado';
  let explanation: string | null = null;
  if (/^field required$/i.test(source)) explanation = 'es obligatorio';
  else if (/^input should be a valid integer$/i.test(source)) explanation = 'debe ser un número entero';
  else if (/^input should be a valid number$/i.test(source)) explanation = 'debe ser un número';
  else if (/^input should be a valid string$/i.test(source)) explanation = 'debe ser texto';
  else if (/^input should be greater than 0$/i.test(source)) explanation = 'debe ser mayor que cero';
  else if (/^input should be greater than or equal to 0$/i.test(source)) explanation = 'no puede ser negativo';
  else if (/^input should be less than or equal to 100$/i.test(source)) explanation = 'no puede superar 100';
  else if (/^string should have at least (\d+) characters$/i.test(source)) explanation = `debe tener al menos ${source.match(/\d+/)?.[0]} caracteres`;
  else if (/^string should have at most (\d+) characters$/i.test(source)) explanation = `no debe superar ${source.match(/\d+/)?.[0]} caracteres`;
  if (explanation) return `El campo ${field} ${explanation}.`;
  if (/[áéíóúñ¿¡]/i.test(source)) return `${field}: ${source}`;
  return `El campo ${field} contiene un valor no válido.`;
}

function extractMessage(value: unknown): string | null {
  const text = cleanText(value);
  if (text) return text;
  if (Array.isArray(value)) {
    const messages = value.map((item) => {
      if (typeof item === 'string') return cleanText(item);
      return item && typeof item === 'object' ? validationMessage(item as Record<string, unknown>) : null;
    }).filter((item): item is string => !!item);
    return messages.length ? messages.join(' ') : null;
  }
  if (!value || typeof value !== 'object') return null;
  const record = value as Record<string, unknown>;
  const direct = cleanText(record['message']) ?? cleanText(record['msg']);
  if (direct) return direct;
  return validationMessage(record) ?? extractMessage(record['detail']) ?? extractMessage(record['error']);
}

/** Converts FastAPI/Angular HTTP error bodies into displayable Spanish text. */
export function loyaltyErrorMessage(error: unknown, fallback: string): string {
  if (error && typeof error === 'object') {
    const record = error as Record<string, unknown>;
    const body = record['error'];
    if (body && typeof body === 'object') {
      const bodyRecord = body as Record<string, unknown>;
      const message = extractMessage(bodyRecord['detail']) ?? extractMessage(bodyRecord['message']) ?? extractMessage(bodyRecord);
      if (message) return message;
    } else {
      const bodyMessage = extractMessage(body);
      if (bodyMessage) return bodyMessage;
    }
    const direct = extractMessage(record['detail']) ?? extractMessage(record['message']);
    if (direct) return direct;
  }
  return cleanText(fallback) ?? 'No se pudo completar la operación de fidelización.';
}
