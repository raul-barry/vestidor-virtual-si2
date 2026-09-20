export interface AdminPermission { id_permiso:number; codigo:string; descripcion:string|null; }
export interface AdminRole { id_rol:number; nombre:string; descripcion:string|null; estado:string; protegido:boolean; permisos:AdminPermission[]; }
export interface RoleRequest { nombre:string; descripcion:string|null; permisos:number[]; }
