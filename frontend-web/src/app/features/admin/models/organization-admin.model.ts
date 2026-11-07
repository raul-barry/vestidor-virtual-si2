export interface OrganizationAdmin {
  id_organizacion: number;
  nombre: string;
  razon_social: string | null;
  nit: string | null;
  correo_contacto: string | null;
  telefono_contacto: string | null;
  direccion: string | null;
  logo_url: string | null;
  slug: string;
  estado: 'ACTIVA' | 'INACTIVA';
  fecha_creacion: string | null;
  fecha_actualizacion: string | null;
}

export interface OrganizationBranchAdmin {
  id_sucursal: number;
  nombre: string;
  direccion: string;
  ciudad: string;
  estado: string;
}

export interface OrganizationUserAdmin {
  id_usuario: number;
  nombre: string;
  correo: string;
  rol: string;
  estado: string;
  fecha_registro: string;
}

export interface CreateOrganizationRequest {
  nombre: string;
  razon_social?: string | null;
  nit?: string | null;
  correo_contacto?: string | null;
  telefono_contacto?: string | null;
  direccion?: string | null;
  logo_url?: string | null;
  slug?: string;
}

export type UpdateOrganizationRequest = Partial<Omit<CreateOrganizationRequest, 'nombre' | 'slug'>> & Partial<Pick<CreateOrganizationRequest, 'nombre' | 'slug'>>;

export interface OrganizationAdminRequest {
  nombres: string;
  apellidos: string;
  correo: string;
  telefono?: string | null;
  password: string;
}

export interface TenantProvisionRequest {
  organization: CreateOrganizationRequest;
  administrator: OrganizationAdminRequest;
  subscription: { plan_id: number; fecha_fin?: string | null };
}

export interface TenantProvisionResult {
  organization: OrganizationAdmin;
  administrator: { id_usuario: number; id_organizacion: number; nombres: string; apellidos: string; correo: string; rol: string };
  subscription: import('./subscription-admin.model').SubscriptionAdmin;
}
