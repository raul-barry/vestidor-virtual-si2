export interface Payment {
  id_pago: number;
  id_pedido: number;
  metodo_pago: 'EFECTIVO' | 'QR' | 'TARJETA';
  monto: string;
  estado: 'PENDIENTE' | 'PROCESANDO' | 'PAGADO' | 'FALLIDO' | 'CANCELADO';
  fecha_pago: string;
  proveedor?: string | null;
  referencia_externa?: string | null;
}
