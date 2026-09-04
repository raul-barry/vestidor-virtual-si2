export interface InventoryAdmin { id_inventario: number; producto: string; sku: string; talla: string; color: string; sucursal: string; stock: number; stock_bajo: boolean; }
export interface InventoryCreateRequest { id_variante: number; id_sucursal: number; stock: number; }
export interface StockActionRequest { cantidad: number; motivo: string; }
export interface StockAdjustmentRequest { nuevo_stock: number; motivo: string; }
export interface StockMovement { tipo: string; cantidad: number; stock_anterior: number; stock_nuevo: number; motivo?: string; usuario: string; fecha: string; }
