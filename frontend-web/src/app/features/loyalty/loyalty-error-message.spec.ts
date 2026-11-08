import { loyaltyErrorMessage } from './loyalty-error-message';

describe('loyaltyErrorMessage', () => {
  it('reads FastAPI string and object details', () => {
    expect(loyaltyErrorMessage({ error: { detail: 'El programa está desactivado.' } }, 'Error genérico')).toBe('El programa está desactivado.');
    expect(loyaltyErrorMessage({ error: { detail: { code: 'INVALID', message: 'El saldo no alcanza.' } } }, 'Error genérico')).toBe('El saldo no alcanza.');
    expect(loyaltyErrorMessage({ error: { message: 'No se pudo acumular puntos.' } }, 'Error genérico')).toBe('No se pudo acumular puntos.');
  });

  it('translates FastAPI validation details and fields', () => {
    expect(loyaltyErrorMessage({ error: { detail: [
      { loc: ['body', 'points'], msg: 'Input should be greater than 0' },
      { loc: ['body', 'minimum_redeem_points'], msg: 'Field required' },
    ] } }, 'Error genérico')).toBe('El campo puntos a canjear debe ser mayor que cero. El campo puntos mínimos para canjear es obligatorio.');
  });

  it('uses a safe fallback for empty or non-displayable values', () => {
    for (const body of [null, {}, { detail: '[object Object]' }, { detail: 'undefined' }, { detail: 'null' }]) {
      const message = loyaltyErrorMessage({ error: body }, 'No se pudo guardar la configuración.');
      expect(message).toBe('No se pudo guardar la configuración.');
      expect(message).not.toMatch(/\[object Object\]|undefined|null/);
    }
  });
});
