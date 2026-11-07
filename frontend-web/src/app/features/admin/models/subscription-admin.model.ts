export interface SubscriptionFeatureAdmin {
  id_plan_caracteristica: number;
  codigo: string;
  nombre: string;
  descripcion: string | null;
  habilitada: boolean;
  limite: number | null;
  configuracion: Record<string, unknown> | null;
}

export interface SubscriptionPlanAdmin {
  id_plan: number;
  codigo: 'ESTILO' | 'MODA' | 'GLAMOUR' | string;
  nombre: string;
  descripcion: string | null;
  max_sucursales: number | null;
  caracteristicas: SubscriptionFeatureAdmin[];
}

export interface SubscriptionAdmin {
  id_suscripcion: number;
  organizacion_id: number;
  plan_id: number;
  plan_codigo: string;
  plan_nombre: string;
  estado: 'ACTIVA' | 'VENCIDA' | 'CANCELADA' | 'FINALIZADA';
  fecha_inicio: string;
  fecha_fin: string | null;
  fecha_creacion: string;
  fecha_actualizacion: string;
  creado_por_id: number | null;
}

export interface SubscriptionRequestAdmin {
  plan_id: number;
  fecha_fin?: string | null;
}
