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
