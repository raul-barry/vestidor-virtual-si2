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
  tipo_entrega?: 'RECOJO_SUCURSAL' | 'DELIVERY' | null;
  id_sucursal_entrega?: number | null;
  direccion_entrega?: string | null;
  referencia_entrega?: string | null;
  telefono_entrega?: string | null;
  detalles?: OrderDetail[];
}

export interface DeliveryBranch {
  id_sucursal: number;
  nombre: string;
  direccion: string;
}

export interface CreateOrderRequest {
  tipo_entrega: 'RECOJO_SUCURSAL' | 'DELIVERY';
  id_sucursal_entrega?: number;
  direccion_entrega?: string;
  referencia_entrega?: string;
  telefono_entrega?: string;
}
