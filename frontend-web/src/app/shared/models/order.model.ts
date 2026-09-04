export interface OrderDetail {
  producto: string;
  talla: string;
  color: string;
  cantidad: number;
  precio_unitario: string;
}

export interface Order {
  id_pedido: number;
  fecha_pedido?: string;
  estado: string;
  total: string;
  detalles?: OrderDetail[];
}
