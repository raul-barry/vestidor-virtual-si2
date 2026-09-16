export interface UserAdmin { id_usuario: number; nombres: string; apellidos: string; correo: string; telefono: string | null; rol: string; estado: 'ACTIVO' | 'INACTIVO'; fecha_creacion?: string; }
export interface CreateUserAdminRequest { nombres: string; apellidos: string; correo: string; telefono?: string | null; password: string; rol: string; id_sucursal?: number | null; }
export interface UpdateUserStatusRequest { estado: 'ACTIVO' | 'INACTIVO'; }
export interface UpdateUserRoleRequest { id_rol: number; }
