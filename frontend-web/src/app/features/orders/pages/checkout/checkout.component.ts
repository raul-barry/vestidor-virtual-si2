import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { CurrencyPipe } from '@angular/common';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Router } from '@angular/router';
import { Cart } from '../../../../shared/models/cart.model';
import { CreateOrderRequest, DeliveryBranch, Order } from '../../../../shared/models/order.model';
import { CartService } from '../../../cart/services/cart.service';
import { OrderService } from '../../services/order.service';
import { OfflineSaleOrder, OutboxSyncService } from '../../../../core/services/outbox-sync.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-checkout',
  standalone: true,
  imports: [
    CurrencyPipe,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    ReactiveFormsModule,
    MatSnackBarModule
  ],
  templateUrl: './checkout.component.html',
  styleUrl: './checkout.component.scss'
})
export class CheckoutComponent implements OnInit, OnDestroy {
  private readonly cartService = inject(CartService);
  private readonly orderService = inject(OrderService);
  private readonly formBuilder = inject(NonNullableFormBuilder);
  private readonly snackBar = inject(MatSnackBar);
  private readonly router = inject(Router);
  private readonly outbox = inject(OutboxSyncService);

  cart: Cart | null = null;
  createdOrder: Order | null = null;
  createdOfflineOrder: OfflineSaleOrder | null = null;
  isLoading = true;
  isSubmitting = false;
  branches: DeliveryBranch[] = [];
  offlineCart = false;
  private readonly outboxSubscription: Subscription;
  readonly deliveryForm = this.formBuilder.group({
    tipo_entrega: ['RECOJO_SUCURSAL' as CreateOrderRequest['tipo_entrega'], Validators.required],
    id_sucursal_entrega: [0],
    direccion_entrega: [''],
    referencia_entrega: [''],
    telefono_entrega: [''],
    metodo_pago: ['EFECTIVO' as 'EFECTIVO' | 'TARJETA' | 'QR', Validators.required],
    importe_recibido: [''],
  });

  constructor() {
    this.outboxSubscription = this.outbox.summary$.subscribe(() => void this.refreshOfflineReceipt());
  }

  ngOnInit(): void {
    this.cartService.getCart().subscribe({
      next: (serverCart) => {
        void this.outbox.localCart().then(localCart => {
          if (this.outbox.isOfflineModifiedCart(localCart)) {
            this.cart = localCart;
            this.offlineCart = true;
          } else {
            this.cart = serverCart;
            this.offlineCart = false;
            void this.outbox.saveLocalCart(serverCart);
          }
          this.isLoading = false;
        }).catch(() => {
          this.cart = serverCart;
          this.offlineCart = false;
          this.isLoading = false;
        });
      },
      error: (error: { error?: { message?: string } }) => {
        void this.outbox.localCart().then(cart => {
          this.cart = cart;
          this.offlineCart = !!cart;
          this.isLoading = false;
          if (!cart) this.handleLoadError(error);
        });
      }
    });
    this.orderService.getDeliveryBranches().subscribe({
      next: branches => this.branches = branches,
      error: () => this.snackBar.open('No fue posible cargar las sucursales de recojo', 'Cerrar', { duration: 5000 })
    });
  }

  get isDelivery(): boolean { return this.deliveryForm.controls.tipo_entrega.value === 'DELIVERY'; }
  get isOnline(): boolean { return typeof navigator === 'undefined' || navigator.onLine; }

  ngOnDestroy(): void { this.outboxSubscription.unsubscribe(); }

  createOrder(): void {
    if (!this.cart || this.cart.items.length === 0) {
      this.snackBar.open('Tu carrito está vacío', 'Cerrar', { duration: 4000 });
      return;
    }

    const request = this.deliveryRequest();
    const online = typeof navigator === 'undefined' || navigator.onLine;
    if (!request && online && !this.offlineCart) return;
    if (!online || this.offlineCart) {
      const value = this.deliveryForm.getRawValue();
      const delivery = request ?? {};
      const received = Number(value.importe_recibido);
      this.isSubmitting = true;
      void this.outbox.queueOfflineSale(this.cart, delivery, value.metodo_pago,
        value.metodo_pago === 'EFECTIVO' ? received : undefined).then(order => {
          this.createdOfflineOrder = order;
          this.cart = { ...this.cart!, items: [], total: '0.00' };
          this.isSubmitting = false;
          void this.router.navigate([], { queryParams: { offline_order: order.numero_local }, queryParamsHandling: 'merge' });
          this.snackBar.open('Venta registrada. Esperando confirmación.', 'Cerrar', { duration: 5000 });
          if (typeof navigator === 'undefined' || navigator.onLine) void this.outbox.syncPending();
        }).catch(error => {
          this.isSubmitting = false;
          this.snackBar.open(error?.message ?? 'No fue posible guardar la venta offline', 'Cerrar', { duration: 5000 });
        });
      return;
    }
    if (!request) return;
    this.isSubmitting = true;
    this.orderService.createOrder(request).subscribe({
      next: (order) => {
        this.createdOrder = order;
        void this.outbox.saveLocalCart({ id_carrito: 0, estado: 'LOCAL', items: [], total: '0.00' });
        this.isSubmitting = false;
        this.snackBar.open('Pedido creado correctamente', 'Cerrar', { duration: 3000 });
      },
      error: (error: { error?: { message?: string } }) => {
        this.isSubmitting = false;
        this.snackBar.open(error.error?.message ?? 'No fue posible crear el pedido', 'Cerrar', {
          duration: 5000
        });
      }
    });
  }

  async syncOfflineSale(): Promise<void> {
    await this.outbox.syncPending();
    await this.refreshOfflineReceipt();
  }

  payOfflineOrder(): void {
    const id = this.createdOfflineOrder?.id_pedido;
    if (typeof id === 'number' && Number.isInteger(id) && id > 0) void this.router.navigate(['/payments', id]);
  }

  private async refreshOfflineReceipt(): Promise<void> {
    if (!this.createdOfflineOrder) return;
    const order = (await this.outbox.localOrders()).find(item => item.local_operation_uuid === this.createdOfflineOrder?.local_operation_uuid);
    if (order) this.createdOfflineOrder = order;
  }

  private deliveryRequest(): CreateOrderRequest | null {
    const value = this.deliveryForm.getRawValue();
    if (value.tipo_entrega === 'RECOJO_SUCURSAL') {
      if (value.id_sucursal_entrega <= 0) {
        this.snackBar.open('Selecciona una sucursal de recojo', 'Cerrar', { duration: 4000 });
        return null;
      }
      return { tipo_entrega: value.tipo_entrega, id_sucursal_entrega: value.id_sucursal_entrega };
    }
    if (value.direccion_entrega.trim().length < 3 || value.telefono_entrega.trim().length < 6) {
      this.snackBar.open('Delivery requiere dirección y teléfono', 'Cerrar', { duration: 4000 });
      return null;
    }
    return {
      tipo_entrega: value.tipo_entrega,
      direccion_entrega: value.direccion_entrega.trim(),
      referencia_entrega: value.referencia_entrega.trim() || undefined,
      telefono_entrega: value.telefono_entrega.trim(),
    };
  }

  payOrder(): void {
    if (this.createdOrder) {
      void this.router.navigate(['/payments', this.createdOrder.id_pedido]);
    }
  }

  private handleLoadError(error: { error?: { message?: string } }): void {
    this.isLoading = false;
    this.snackBar.open(error.error?.message ?? 'No fue posible cargar el carrito', 'Cerrar', {
      duration: 5000
    });
  }
}
