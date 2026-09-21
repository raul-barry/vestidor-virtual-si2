export interface AdminBranch { id_sucursal: number; nombre: string; direccion: string; ciudad: string; estado: string; }
export interface BranchRequest { nombre: string; direccion: string; ciudad: string; }
export interface BranchUpdateRequest { nombre?: string; direccion?: string; }