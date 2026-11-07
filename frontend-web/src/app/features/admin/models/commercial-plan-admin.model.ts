export interface CommercialPlanFeatureAdmin {
  id_plan_caracteristica: number;
  codigo: string;
  nombre: string;
  descripcion: string | null;
  habilitada: boolean;
  limite: number | null;
  configuracion: Record<string, unknown> | null;
  configuracionTexto?: string;
}

export interface CommercialPlanAdmin {
  id_plan: number;
  codigo: 'ESTILO' | 'MODA' | 'GLAMOUR' | string;
  nombre: string;
  descripcion: string | null;
  max_sucursales: number | null;
  activo: boolean;
  caracteristicas: CommercialPlanFeatureAdmin[];
}

export interface CommercialPlanUpdate {
  nombre?: string;
  descripcion?: string | null;
  max_sucursales?: number | null;
  activo?: boolean;
}

export interface CommercialPlanFeatureUpdate {
  codigo: string;
  habilitada?: boolean;
  limite?: number | null;
  configuracion?: Record<string, unknown> | null;
}
