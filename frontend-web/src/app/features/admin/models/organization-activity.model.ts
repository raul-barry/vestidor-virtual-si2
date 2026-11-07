export interface OrganizationActivity {
  id: number;
  organizacion_id: number;
  usuario_id: number | null;
  rol: string;
  accion: string;
  entidad: string;
  entidad_id: string | null;
  fecha_hora: string;
  resultado: string;
  detalles: Record<string, unknown>;
}

export interface OrganizationActivityPage {
  items: OrganizationActivity[];
  total: number;
  limit: number;
  offset: number;
}
