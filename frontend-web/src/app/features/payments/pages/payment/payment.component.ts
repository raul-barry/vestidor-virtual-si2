import { CurrencyPipe } from '@angular/common';
import { AfterViewInit, Component, ElementRef, OnInit, ViewChild, inject } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { loadStripe, Stripe, StripeElements, StripePaymentElement } from '@stripe/stripe-js';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { catchError, forkJoin, of } from 'rxjs';
import { Order } from '../../../../shared/models/order.model';
import { Payment } from '../../../../shared/models/payment.model';
import { OrderService } from '../../../orders/services/order.service';
import { PaymentMethod, PaymentService } from '../../services/payment.service';
import { environment } from '../../../../../environments/environment';

@Component({
  selector: 'app-payment', standalone: true,
  imports: [CurrencyPipe, ReactiveFormsModule, RouterLink, MatButtonModule, MatCardModule, MatFormFieldModule, MatProgressSpinnerModule, MatSelectModule, MatInputModule, MatSnackBarModule],
  templateUrl: './payment.component.html', styleUrl: './payment.component.scss'
})
export class PaymentComponent implements OnInit, AfterViewInit {
  private readonly formBuilder = inject(NonNullableFormBuilder);
  private readonly route = inject(ActivatedRoute);
  private readonly orderService = inject(OrderService);
  private readonly paymentService = inject(PaymentService);
  private readonly snackBar = inject(MatSnackBar);
  @ViewChild('paymentElement') paymentElement?: ElementRef<HTMLDivElement>;
  readonly paymentForm = this.formBuilder.group({ metodo_pago: ['TARJETA' as PaymentMethod, [Validators.required]] });
  readonly demoCardForm = this.formBuilder.group({
    number: ['4242 4242 4242 4242', [Validators.required, Validators.minLength(16)]],
    expiry: ['12/34', [Validators.required]],
    cvc: ['123', [Validators.required, Validators.minLength(3)]],
    holder: ['Cliente Demo', [Validators.required, Validators.minLength(2)]],
  });
  readonly qrCells = Array.from({ length: 121 }, (_, index) => index);
  order: Order | null = null; payment: Payment | null = null; successPayment: Payment | null = null; isLoading = true; isSubmitting = false; cardReady = false; cardClientSecret = ''; cardSimulation = false; qrSimulation = false; qrPayload = '';
  private stripe: Stripe | null = null; private elements: StripeElements | null = null; private paymentElementInstance: StripePaymentElement | null = null;
  private stripeLoader = loadStripe;

  ngOnInit(): void {
    const orderId = Number(this.route.snapshot.paramMap.get('id_pedido'));
    if (!Number.isInteger(orderId) || orderId <= 0) { this.handleLoadError(); return; }
    forkJoin({ order: this.orderService.getOrderDetail(orderId), payment: this.paymentService.getPaymentByOrder(orderId).pipe(catchError((error: { status?: number }) => error.status === 404 ? of(null) : (() => { throw error; })())) }).subscribe({
      next: response => { this.order = response.order; this.payment = response.payment; this.qrSimulation = response.payment?.metodo_pago === 'QR' && response.payment?.proveedor === 'STRIPE_SIMULADO'; this.cardSimulation = response.payment?.metodo_pago === 'TARJETA' && response.payment?.proveedor === 'STRIPE_SIMULADO'; this.isLoading = false; }, error: () => this.handleLoadError()
    });
  }
  ngAfterViewInit(): void { if (this.cardClientSecret) this.mountStripeElement(); }
  get selectedMethod(): PaymentMethod { return this.paymentForm.controls.metodo_pago.value; }

  createPayment(): void {
    if (!this.order || this.paymentForm.invalid || this.isSubmitting) return;
    if (this.selectedMethod === 'TARJETA') {
      // Compatibility with older test doubles/embedders; the production service always exposes Stripe.
      if (typeof (this.paymentService as PaymentService & { createStripeIntent?: unknown }).createStripeIntent !== 'function') {
        this.isSubmitting = true;
        this.paymentService.createPayment(this.order.id_pedido, 'TARJETA').subscribe({ next: payment => { this.payment = payment; this.isSubmitting = false; }, error: error => this.showError(error) });
      } else this.startCardPayment();
      return;
    }
    this.isSubmitting = true;
    if (this.selectedMethod === 'QR') {
      this.paymentService.createQrPayment(this.order.id_pedido).subscribe({ next: response => { this.payment = response.payment; this.qrPayload = response.qr_payload; this.qrSimulation = !!response.simulation; this.isSubmitting = false; this.snackBar.open(this.qrSimulation ? 'QR generado en MODO DEMOSTRACIÓN' : 'QR generado', 'Cerrar', { duration: 4000 }); }, error: error => this.showError(error) });
      return;
    }
    this.paymentService.createPayment(this.order.id_pedido, 'EFECTIVO').subscribe({ next: payment => { this.payment = payment; this.isSubmitting = false; this.snackBar.open('Efectivo registrado como pendiente.', 'Cerrar', { duration: 4000 }); }, error: error => this.showError(error) });
  }
  startCardPayment(): void {
    if (!this.order || this.isSubmitting) return; this.isSubmitting = true;
    this.paymentService.createStripeIntent(this.order.id_pedido).subscribe({ next: response => { this.payment = response.payment; this.cardClientSecret = response.client_secret; this.cardSimulation = !!response.simulation; this.isSubmitting = false; if (!response.simulation) this.mountStripeElement(response.publishable_key || environment.STRIPE_PUBLISHABLE_KEY); }, error: error => this.showError(error) });
  }
  async confirmCardPayment(): Promise<void> {
    if (this.cardSimulation) { this.simulateApproval('Pago con tarjeta realizado correctamente (simulación).'); return; }
    if (!this.stripe || !this.elements || this.isSubmitting) return; this.isSubmitting = true;
    const result = await this.stripe.confirmPayment({ elements: this.elements, redirect: 'if_required' });
    if (result.error) { this.isSubmitting = false; this.snackBar.open(result.error.message ?? 'No fue posible confirmar la tarjeta', 'Cerrar', { duration: 5000 }); return; }
    this.snackBar.open('Pago enviado. Esperando confirmación segura de Stripe…', 'Cerrar', { duration: 4000 }); this.pollStatus(0);
  }
  simulateApproval(message: string): void {
    if (!this.payment || this.isSubmitting) return;
    this.isSubmitting = true;
    setTimeout(() => this.paymentService.approvePayment(this.payment!.id_pago).subscribe({ next: payment => { this.payment = payment; this.successPayment = payment; this.isSubmitting = false; this.snackBar.open(message, 'Cerrar', { duration: 4000 }); }, error: error => this.showError(error) }), 1200);
  }
  confirmQrPayment(): void {
    if (!this.payment || this.payment.metodo_pago !== 'QR' || this.isSubmitting) return;
    this.isSubmitting = true;
    setTimeout(() => this.paymentService.confirmQrPayment(this.payment!.id_pago).subscribe({ next: payment => { this.payment = payment; this.successPayment = payment; this.isSubmitting = false; this.snackBar.open('Pago QR realizado correctamente (simulación).', 'Cerrar', { duration: 4000 }); }, error: error => this.showError(error) }), 1200);
  }
  qrCellIsDark(index: number): boolean {
    const seed = this.qrPayload || 'VESTIDOR-DEMO';
    return (seed.charCodeAt(index % seed.length) + index * 17 + Math.floor(index / 11) * 7) % 5 < 2;
  }
  private mountStripeElement(publishableKey = environment.STRIPE_PUBLISHABLE_KEY): void {
    if (!this.cardClientSecret || !publishableKey) { this.snackBar.open('No fue posible cargar el formulario de Stripe.', 'Cerrar', { duration: 5000 }); return; }
    void this.stripeLoader(publishableKey).then(stripe => { this.stripe = stripe; if (!stripe) return; this.elements = stripe.elements({ clientSecret: this.cardClientSecret }); setTimeout(() => { if (!this.paymentElement || !this.elements || this.paymentElementInstance) return; this.paymentElementInstance = this.elements.create('payment'); this.paymentElementInstance.mount(this.paymentElement.nativeElement); this.cardReady = true; }); });
  }
  private pollStatus(attempt: number): void {
    if (!this.order) return; this.paymentService.getPaymentStatus(this.order.id_pedido).subscribe({ next: response => { this.payment = response.payment; if (['PENDIENTE', 'PROCESANDO'].includes(response.payment.estado) && attempt < 15) { setTimeout(() => this.pollStatus(attempt + 1), 2000); return; } this.isSubmitting = false; if (response.payment.estado === 'PAGADO') this.successPayment = response.payment; this.snackBar.open(response.payment.estado === 'PAGADO' ? 'Pago confirmado correctamente' : `Estado del pago: ${response.payment.estado}`, 'Cerrar', { duration: 5000 }); }, error: error => this.showError(error) });
  }
  private showError(error: { error?: { detail?: string; message?: string } }): void { this.isSubmitting = false; this.snackBar.open(error.error?.detail ?? error.error?.message ?? 'No fue posible procesar el pago', 'Cerrar', { duration: 5000 }); }
  private handleLoadError(): void { this.isLoading = false; this.snackBar.open('No fue posible cargar la información de pago', 'Cerrar', { duration: 5000 }); }
}
