export type OrderStatus = 'PENDIENTE' | 'CONFIRMADO' | 'PREPARANDO' | 'ENVIADO' | 'ENTREGADO' | 'CANCELADO';
export interface OrderAdmin { id_pedido: number; cliente: string; fecha: string; estado: OrderStatus; total: string; }
export interface OrderDetailAdmin extends OrderAdmin { detalles: Array<{ producto: string; talla: string; color: string; cantidad: number; precio_unitario: string }>; pago: { id_pago: number; metodo_pago: string; monto: string; estado: string } | null; }
export interface UpdateOrderStatusRequest { estado: OrderStatus; }
