export interface AdminSize { id_talla: number; nombre: string; estado: string; }
export interface SizeRequest { nombre: string; }
export interface SizeUpdateRequest { nombre?: string; }