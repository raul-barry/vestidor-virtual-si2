export interface Payment {
  id_pago: number;
  id_pedido: number;
  metodo_pago: 'EFECTIVO' | 'QR' | 'TARJETA';
  monto: string;
  estado: 'PENDIENTE' | 'PROCESANDO' | 'PAGADO' | 'FALLIDO' | 'CANCELADO' | 'REQUIERE_REVISION';
  fecha_pago: string;
  proveedor?: string | null;
  referencia_externa?: string | null;
  currency?: string;
  simulated?: boolean;
  cash_received?: string | null;
  cash_change?: string;
}
