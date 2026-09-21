import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import { Payment } from '../../../shared/models/payment.model';

export type PaymentMethod = Payment['metodo_pago'];

export interface StripeIntentResponse {
  client_secret: string;
  publishable_key: string;
  payment: Payment;
  simulation?: boolean;
}

export interface QrPaymentResponse {
  payment: Payment;
  qr_payload: string;
  provider_reference: string;
  simulation: boolean;
}

export interface PaymentStatusResponse {
  payment: Payment;
  order_status: string;
}

@Injectable({ providedIn: 'root' })
export class PaymentService {
  constructor(private readonly api: ApiService) {}

  createPayment(id_pedido: number, metodo_pago: PaymentMethod): Observable<Payment> {
    return this.api.post<Payment>('/api/payments', { id_pedido, metodo_pago });
  }

  getPaymentByOrder(id_pedido: number): Observable<Payment> {
    return this.api.get<Payment>(`/api/payments/order/${id_pedido}`);
  }

  createStripeIntent(id_pedido: number): Observable<StripeIntentResponse> {
    return this.api.post<StripeIntentResponse>('/api/payments/stripe/create-intent', { id_pedido });
  }

  createQrPayment(id_pedido: number): Observable<QrPaymentResponse> {
    return this.api.post<QrPaymentResponse>('/api/payments/qr', { id_pedido, metodo_pago: 'QR' });
  }

  confirmQrPayment(id_pago: number): Observable<Payment> {
    return this.api.post<Payment>(`/api/payments/qr/${id_pago}/confirm`, {});
  }

  getPaymentStatus(id_pedido: number): Observable<PaymentStatusResponse> {
    return this.api.get<PaymentStatusResponse>(`/api/payments/${id_pedido}/status`);
  }

  approvePayment(id_pago: number): Observable<Payment> {
    return this.api.put<Payment>(`/api/payments/${id_pago}/approve`, {});
  }

  rejectPayment(id_pago: number): Observable<Payment> {
    return this.api.put<Payment>(`/api/payments/${id_pago}/reject`, {});
  }
}
