export interface CartItem {
  id_detalle: number;
  producto: string;
  talla: string;
  color: string;
  cantidad: number;
  precio_unitario: string;
}

export interface Cart {
  id_carrito: number;
  estado: string;
  items: CartItem[];
  total: string;
}
