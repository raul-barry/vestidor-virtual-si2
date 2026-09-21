export interface AdminCategory { id_categoria: number; nombre: string; }
export interface AdminProduct { id_producto: number; nombre: string; descripcion: string | null; precio_base: string; estado: string; categoria: AdminCategory; imagen_url?: string | null; }
export interface ProductRequest { nombre: string; descripcion?: string | null; precio_base: number; id_categoria: number; }
