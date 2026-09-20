export type LogicalState = 'ACTIVO' | 'INACTIVO';

export interface Supplier {
  id_proveedor: number;
  nombre: string;
  descripcion: string;
  persona_contacto: string;
  telefono: string;
  correo: string;
  direccion: string;
  estado: LogicalState;
}

export type SupplierRequest = Omit<Supplier, 'id_proveedor'>;

export interface Collection {
  id_coleccion: number;
  nombre: string;
  descripcion: string;
  temporada: string;
  anio: number | null;
  fecha_inicio: string | null;
  fecha_fin: string | null;
  estado: LogicalState;
}

export type CollectionRequest = Omit<Collection, 'id_coleccion'>;

export interface CollectionProduct {
  id_producto: number;
  nombre: string;
  id_coleccion: number | null;
}
