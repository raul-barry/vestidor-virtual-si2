export interface ProductoVariante {
  id_variante: number;
  sku: string;
  talla: string;
  color: string;
}

export interface Categoria {
  id_categoria: number;
  nombre: string;
}

export interface Producto {
  id_producto: number;
  nombre: string;
  descripcion: string | null;
  precio_base: string;
  estado: string;
  categoria: Categoria;
  variantes: ProductoVariante[];
  imagen_url?: string | null;
}

export interface ProductVariantsResponse {
  id_producto: number;
  nombre_producto: string;
  tallas: string[];
  colores: string[];
  variantes: ProductoVariante[];
}

export interface DisponibilidadSucursal {
  id_sucursal: number;
  nombre_sucursal: string;
  direccion: string;
  stock_disponible: number;
}

export interface ProductAvailabilityResponse {
  id_producto: number;
  nombre_producto: string;
  disponibilidad: DisponibilidadSucursal[];
}
