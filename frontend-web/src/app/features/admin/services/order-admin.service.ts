import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import { OrderAdmin, OrderDetailAdmin, OrderStatus, UpdateOrderStatusRequest } from '../models/order-admin.model';
@Injectable({providedIn:'root'})
export class OrderAdminService { constructor(private api:ApiService){} getOrders(filters?:{estado?:string}):Observable<OrderAdmin[]>{return this.api.get<OrderAdmin[]>(`/api/admin/orders${filters?.estado?`?estado=${encodeURIComponent(filters.estado)}`:''}`)} getOrderDetail(id:number):Observable<OrderDetailAdmin>{return this.api.get<OrderDetailAdmin>(`/api/admin/orders/${id}`)} updateStatus(id:number,data:UpdateOrderStatusRequest):Observable<OrderAdmin>{return this.api.put<OrderAdmin>(`/api/admin/orders/${id}/status`,data)} }
