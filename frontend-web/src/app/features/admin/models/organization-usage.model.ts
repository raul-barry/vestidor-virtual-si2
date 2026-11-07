export interface OrganizationUsage {
  organizacion_id: number;
  organizacion_nombre: string;
  periodo_desde: string | null;
  periodo_hasta: string | null;
  plan_codigo: string | null;
  plan_nombre: string | null;
  estado_suscripcion: 'ACTIVA' | 'VENCIDA' | 'CANCELADA' | 'FINALIZADA' | 'SIN_SUSCRIPCION';
  fecha_inicio_suscripcion: string | null;
  fecha_fin_suscripcion: string | null;
  sucursales_activas: number;
  limite_sucursales: number | null;
  usuarios_activos: number;
  productos_registrados: number;
  pedidos_periodo: number;
  ventas_periodo: string;
  reservas_periodo: number;
  inventario_disponible: number;
  inventario_reservado: number;
  inventario_vendido: number;
}
