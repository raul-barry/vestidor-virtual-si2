import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import { InventoryAdmin, InventoryCreateRequest, StockActionRequest, StockAdjustmentRequest, StockMovement } from '../models/inventory-admin.model';

@Injectable({ providedIn: 'root' })
export class InventoryAdminService {
  constructor(private readonly api: ApiService) {}
  getInventory(): Observable<InventoryAdmin[]> { return this.api.get<InventoryAdmin[]>('/api/admin/inventory'); }
  createInventory(data: InventoryCreateRequest): Observable<InventoryAdmin> { return this.api.post<InventoryAdmin>('/api/admin/inventory', data); }
  increaseStock(id: number, data: StockActionRequest): Observable<InventoryAdmin> { return this.api.post<InventoryAdmin>(`/api/admin/inventory/${id}/increase`, data); }
  decreaseStock(id: number, data: StockActionRequest): Observable<InventoryAdmin> { return this.api.post<InventoryAdmin>(`/api/admin/inventory/${id}/decrease`, data); }
  adjustStock(id: number, data: StockAdjustmentRequest): Observable<InventoryAdmin> { return this.api.put<InventoryAdmin>(`/api/admin/inventory/${id}/adjust`, data); }
  getMovements(id: number): Observable<StockMovement[]> { return this.api.get<StockMovement[]>(`/api/admin/inventory/${id}/movements`); }
}
