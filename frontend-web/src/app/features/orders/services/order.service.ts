import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import { CreateOrderRequest, DeliveryBranch, Order } from '../../../shared/models/order.model';

@Injectable({ providedIn: 'root' })
export class OrderService {
  constructor(private readonly api: ApiService) {}

  createOrder(request: CreateOrderRequest): Observable<Order> {
    return this.api.post<Order>('/api/orders', request);
  }

  getDeliveryBranches(): Observable<DeliveryBranch[]> {
    return this.api.get<DeliveryBranch[]>('/api/orders/delivery-branches');
  }

  getOrders(): Observable<Order[]> {
    return this.api.get<Order[]>('/api/orders');
  }

  getOrderDetail(id_pedido: number): Observable<Order> {
    return this.api.get<Order>(`/api/orders/${id_pedido}`);
  }
}
