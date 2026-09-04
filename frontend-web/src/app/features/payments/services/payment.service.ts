import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import { Payment } from '../../../shared/models/payment.model';

export type PaymentMethod = Payment['metodo_pago'];

@Injectable({ providedIn: 'root' })
export class PaymentService {
  constructor(private readonly api: ApiService) {}

  createPayment(id_pedido: number, metodo_pago: PaymentMethod): Observable<Payment> {
    return this.api.post<Payment>('/api/payments', { id_pedido, metodo_pago });
  }

  getPaymentByOrder(id_pedido: number): Observable<Payment> {
    return this.api.get<Payment>(`/api/payments/order/${id_pedido}`);
  }

  approvePayment(id_pago: number): Observable<Payment> {
    return this.api.put<Payment>(`/api/payments/${id_pago}/approve`, {});
  }

  rejectPayment(id_pago: number): Observable<Payment> {
    return this.api.put<Payment>(`/api/payments/${id_pago}/reject`, {});
  }
}
