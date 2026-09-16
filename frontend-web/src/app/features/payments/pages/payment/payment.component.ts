import { Component, OnInit, inject } from '@angular/core';
import { CurrencyPipe } from '@angular/common';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { catchError, forkJoin, of } from 'rxjs';
import { Order } from '../../../../shared/models/order.model';
import { Payment } from '../../../../shared/models/payment.model';
import { OrderService } from '../../../orders/services/order.service';
import { PaymentMethod, PaymentService } from '../../services/payment.service';

@Component({
  selector: 'app-payment',
  standalone: true,
  imports: [
    CurrencyPipe,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatSnackBarModule
  ],
  templateUrl: './payment.component.html',
  styleUrl: './payment.component.scss'
})
export class PaymentComponent implements OnInit {
  private readonly formBuilder = inject(NonNullableFormBuilder);
  private readonly route = inject(ActivatedRoute);
  private readonly orderService = inject(OrderService);
  private readonly paymentService = inject(PaymentService);
  private readonly snackBar = inject(MatSnackBar);

  readonly paymentForm = this.formBuilder.group({
    metodo_pago: ['QR' as PaymentMethod, [Validators.required]]
  });

  order: Order | null = null;
  payment: Payment | null = null;
  isLoading = true;
  isSubmitting = false;

  ngOnInit(): void {
    const orderId = Number(this.route.snapshot.paramMap.get('id_pedido'));
    if (!Number.isInteger(orderId) || orderId <= 0) {
      this.handleLoadError();
      return;
    }

    forkJoin({
      order: this.orderService.getOrderDetail(orderId),
      payment: this.paymentService.getPaymentByOrder(orderId).pipe(
        catchError((error: { status?: number }) => {
          if (error.status === 404) {
            return of(null);
          }
          throw error;
        })
      )
    }).subscribe({
      next: (response) => {
        this.order = response.order;
        this.payment = response.payment;
        this.isLoading = false;
      },
      error: () => this.handleLoadError()
    });
  }

  createPayment(): void {
    if (!this.order || this.paymentForm.invalid) {
      return;
    }

    this.isSubmitting = true;
    this.paymentService.createPayment(this.order.id_pedido, this.paymentForm.controls.metodo_pago.value).subscribe({
      next: (payment) => {
        this.payment = payment;
        this.isSubmitting = false;
        this.snackBar.open('Pago creado correctamente', 'Cerrar', { duration: 3000 });
      },
      error: (error: { error?: { message?: string } }) => {
        this.isSubmitting = false;
        this.snackBar.open(error.error?.message ?? 'No fue posible crear el pago', 'Cerrar', {
          duration: 5000
        });
      }
    });
  }

  private handleLoadError(): void {
    this.isLoading = false;
    this.snackBar.open('No fue posible cargar la información de pago', 'Cerrar', { duration: 5000 });
  }

  processPayment(approve: boolean): void {
    if (!this.payment || this.isSubmitting) return;
    this.isSubmitting = true;
    const request = approve ? this.paymentService.approvePayment(this.payment.id_pago) : this.paymentService.rejectPayment(this.payment.id_pago);
    request.subscribe({ next: payment => { this.payment = payment; this.isSubmitting = false; this.ngOnInit(); },
      error: error => { this.isSubmitting = false; this.snackBar.open(error.error?.message || error.error?.detail || 'No se pudo procesar el pago', 'Cerrar', {duration: 5000}); } });
  }
}
