export interface DashboardReport {
  usuarios_totales: number;
  clientes_totales: number;
  productos_totales: number;
  pedidos_totales: number;
  ventas_totales: string;
  productos_stock_bajo: number;
}

export interface SalesReport {
  ventas_totales: string;
  cantidad_pedidos: number;
  promedio_compra: string;
  pedidos_por_estado: Record<string, number>;
}

export interface ProductRanking {
  producto: string;
  cantidad_vendida: number;
  ingresos_generados: string;
}

export interface CategoryRanking {
  categoria: string;
  cantidad_vendida: number;
  ventas_generadas: string;
}

export interface InventoryReport {
  stock_total: number;
  productos_stock_bajo: number;
  productos_sin_stock: number;
  movimientos_recientes: Array<{ producto: string; tipo: string; cantidad: number; fecha: string }>;
}

export interface CustomerReport {
  usuarios_registrados: number;
  clientes_activos: number;
  clientes_nuevos_mes: number;
  clientes_con_compras: number;
}

export type AiReportType = 'ventas' | 'productos' | 'sucursales' | 'inventario' | 'tendencias';

export interface ReportBranch {
  id_sucursal: number;
  nombre: string;
}

export interface BranchComparisonFilters {
  fecha_inicio: string;
  fecha_fin: string;
  id_sucursal: number[];
}

export interface BranchComparisonAccess {
  comparacion_sucursales: boolean;
  exportacion_pdf_excel: boolean;
}

export interface BranchSalesComparison {
  organizacion: string;
  periodo: { desde: string; hasta: string };
  periodo_anterior: { desde: string; hasta: string };
  zona_horaria: string;
  sucursales: Array<{
    id_sucursal: number;
    sucursal: string;
    ranking: number;
    ingresos_netos: string;
    cantidad_ventas: number;
    ticket_promedio: string;
    ingresos_periodo_anterior: string;
    ventas_periodo_anterior: number;
    variacion_porcentual: string | null;
  }>;
  totales: { ingresos_netos: string; cantidad_ventas: number; ticket_promedio: string; variacion_porcentual: string | null };
  destacados: {
    mayores_ingresos: number | null;
    mas_transacciones: number | null;
    mayor_ticket_promedio: number | null;
    menores_ingresos: number | null;
  };
}

export interface ReportFeatures {
  reportes_ia: boolean;
  /** @deprecated Compatibility alias returned during API transition. */
  reportes_gemini?: boolean;
  reportes_voz: boolean;
  comparacion_sucursales: boolean;
  exportacion_pdf_excel: boolean;
}

export interface AiReportRequest {
  tipo: AiReportType;
  fecha_inicio?: string;
  fecha_fin?: string;
  id_sucursal?: number;
  consulta: string;
  canal: 'texto' | 'voz';
}

export interface AiReportResponse {
  tipo: AiReportType;
  periodo: { desde: string; hasta: string };
  metricas_calculadas: Record<string, unknown>;
  observaciones_ia: string[];
  recomendaciones_ia: string[];
}

export type PredictiveFeatureCode =
  | 'machine_learning'
  | 'prediccion_demanda'
  | 'segmentacion_kmeans'
  | 'dashboard_predictivo';

export type PredictiveFeatures = Record<PredictiveFeatureCode, boolean>;

export interface PredictiveFilters {
  fecha_inicio?: string;
  fecha_fin?: string;
  id_sucursal?: number;
  id_producto?: number;
}

export interface PredictiveResult {
  producto_id: number;
  producto: string;
  sucursal_id: number;
  sucursal: string;
  estado_modelo: 'evaluado' | 'datos_insuficientes';
  stock_disponible: number | null;
  tendencia: string;
  riesgo_inventario: string;
  prediccion_7_dias: null | {
    demanda_esperada: number;
    demanda_diaria: number[];
    desde: string;
    hasta: string;
  };
  evaluacion: { mae: number | null; wape_porcentaje: number | null };
}

export interface PredictiveDashboard {
  periodo: { desde: string; hasta: string };
  modelo: {
    version: string;
    actualizado_en: string;
    metodo: string;
    minimo_dias_historicos: number;
  };
  evaluacion: {
    productos_evaluados: number;
    mae_unidades: number | null;
    wape_porcentaje: number | null;
    metodo: string;
  };
  tendencia_historica_semanal: Array<{ semana_desde: string; unidades_vendidas: number }>;
  predicciones: PredictiveResult[];
  productos_con_datos_insuficientes: number;
}

export interface CustomerSegments {
  estado: 'calculado' | 'datos_insuficientes';
  clientes_analizados: number;
  minimo_clientes?: number;
  variables: string[];
  algoritmo?: string;
  k?: number;
  indice_davies_bouldin?: number;
  actualizado_en: string;
  segmentos: Array<{
    segmento: number;
    clientes: number;
    caracteristicas: string[];
    promedios: {
      compras_pagadas: number;
      gasto_pagado: number;
      dias_desde_ultima_compra: number;
    };
  }>;
}

export interface PredictiveHistory {
  periodo_evaluado: { desde: string; hasta: string };
  nota: string;
  resultados: Array<{
    producto_id: number;
    producto: string;
    sucursal_id: number;
    sucursal: string;
    periodo: { desde: string; hasta: string };
    demanda_predicha: number;
    demanda_real: number;
    error_absoluto: number;
    tipo_resultado: 'backtest_reconstruido';
  }>;
}
