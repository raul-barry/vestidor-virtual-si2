import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import { OutboxSyncService } from '../../core/services/outbox-sync.service';

@Component({
  standalone: true,
  imports: [CommonModule, FormsModule],
  styles: [`main{max-width:1100px;margin:auto;padding:2rem}fieldset,form{display:flex;flex-wrap:wrap;gap:1rem;margin:1rem 0;padding:1rem;border:1px solid #d7dfda;border-radius:10px}label{display:grid;gap:.3rem;min-width:180px}input,select,button{padding:.5rem}table{width:100%;border-collapse:collapse}th,td{padding:.6rem;border-bottom:1px solid #ddd;text-align:left}.notice{padding:.7rem;background:#edf6ef;border-radius:8}`],
  template: `
    <main>
      <h1>Venta presencial</h1>
      <p class="notice" role="status">{{message || (online ? 'Conexión disponible' : 'Modo offline: se aceptan únicamente ventas de contado en efectivo.')}}</p>
      <fieldset><legend>Tipo de cliente</legend>
        <label><input type="radio" name="customerType" [(ngModel)]="customerType" value="CLIENTE_REGISTRADO" (ngModelChange)="clearCustomer()"> Cliente registrado</label>
        <label><input type="radio" name="customerType" [(ngModel)]="customerType" value="CONSUMIDOR_FINAL" (ngModelChange)="clearCustomer()"> Consumidor final</label>
        @if(customerType==='CLIENTE_REGISTRADO'){<label>Cliente<select [(ngModel)]="customerId" (ngModelChange)="refreshLoyalty()"><option [ngValue]="0">Seleccionar cliente</option>@for(c of customers;track c.id_cliente){<option [ngValue]="c.id_cliente">{{c.nombre}}</option>}</select></label>}
      </fieldset>
      <fieldset><legend>Facturación</legend>
        <label><input type="checkbox" [(ngModel)]="invoice" (ngModelChange)="clearInvoice()"> Requiere datos de facturación</label>
        @if(invoice){<label>NIT / CI<input [(ngModel)]="nitCi"></label><label>Razón social<input [(ngModel)]="businessName"></label>}
      </fieldset>
      <fieldset><legend>Sucursal de la venta</legend>
        <label>Sucursal<select [(ngModel)]="branchId" (ngModelChange)="clearLines()"><option [ngValue]="0">Seleccionar sucursal</option>@for(b of branches;track b.id_sucursal){<option [ngValue]="b.id_sucursal">{{b.nombre}}</option>}</select></label>
      </fieldset>
      <form (ngSubmit)="add()">
        <label>Producto<select name="inventory" [(ngModel)]="inventoryId"><option [ngValue]="0">Seleccionar prenda</option>@for(i of branchInventory;track i.id_inventario){<option [ngValue]="i.id_inventario">{{i.producto}} · {{i.talla}} · {{i.color}} · stock {{i.stock}}</option>}</select></label>
        <label>Cantidad<input name="quantity" type="number" [(ngModel)]="quantity" min="1"></label><button [disabled]="!inventoryId">Agregar</button>
      </form>
      <table><tr><th>Prenda</th><th>Cantidad</th><th>Subtotal</th><th></th></tr>@for(line of lines;track line.id_inventario){<tr><td>{{line.producto}} · {{line.talla}} · {{line.color}}</td><td>{{line.cantidad}}</td><td>Bs {{line.cantidad * line.precio | number:'1.2-2'}}</td><td><button (click)="remove(line.id_inventario)">Quitar</button></td></tr>}</table>
      @if(loyaltyEnabled && customerType==='CLIENTE_REGISTRADO' && online){<fieldset><legend>Puntos del cliente</legend><p>Saldo: {{loyaltyBalance}} puntos</p><label>Puntos a canjear<input type="number" min="0" [(ngModel)]="pointsToRedeem" (ngModelChange)="estimateLoyalty()"></label>@if(loyaltyDiscount){<p>Descuento estimado: Bs {{loyaltyDiscount | number:'1.2-2'}}</p>}@if(loyaltyError){<p class="notice">{{loyaltyError}}</p>}</fieldset>}
      <p>Subtotal: Bs {{subtotal | number:'1.2-2'}} · Descuento de puntos: Bs {{loyaltyDiscount | number:'1.2-2'}}</p><p>Total: <strong>Bs {{total | number:'1.2-2'}}</strong></p>
      <label>Método de pago<select [(ngModel)]="paymentMethod"><option>EFECTIVO</option><option [disabled]="!online">QR</option><option [disabled]="!online">TARJETA</option></select></label>
      @if(paymentMethod==='EFECTIVO'){<label>Efectivo recibido<input type="number" min="0" step="0.01" [(ngModel)]="cashReceived"></label>}
      <button (click)="sell()" [disabled]="busy || !lines.length">{{busy?'Registrando…':online?'Confirmar venta y pago':'Guardar venta pendiente'}}</button>
    </main>`
})
export class PosComponent implements OnInit, OnDestroy {
  private readonly api = inject(ApiService);
  private readonly outbox = inject(OutboxSyncService);
  private connectivityListener = () => { this.online = navigator.onLine; if (this.online) this.loadOptions(); };
  customers: any[] = [];
  inventory: any[] = [];
  lines: any[] = [];
  customerType = 'CLIENTE_REGISTRADO';
  customerId = 0;
  invoice = false;
  nitCi = '';
  businessName = '';
  branchId = 0;
  inventoryId = 0;
  quantity = 1;
  paymentMethod = 'EFECTIVO';
  cashReceived: number | null = null;
  busy = false;
  message = '';
  online = navigator.onLine;
  loyaltyEnabled = false;
  loyaltyBalance = 0;
  pointsToRedeem = 0;
  loyaltyDiscount = 0;
  loyaltyError = '';

  ngOnInit(): void {
    window.addEventListener('online', this.connectivityListener);
    window.addEventListener('offline', this.connectivityListener);
    this.loadOptions();
  }

  ngOnDestroy(): void {
    window.removeEventListener('online', this.connectivityListener);
    window.removeEventListener('offline', this.connectivityListener);
  }

  private async loadOptions(): Promise<void> {
    this.online = navigator.onLine;
    if (!this.online) { await this.loadCachedOptions(); return; }
    this.api.get<any>('/api/commerce/pos/options').subscribe({
      next: async response => {
        this.customers = response.clientes ?? [];
        this.inventory = response.inventario ?? [];
        await this.outbox.cachePosOptions({ clientes: this.customers, inventario: this.inventory });
        this.message = '';
      },
      error: async () => {
        await this.loadCachedOptions();
        this.message = this.inventory.length ? 'No se pudo actualizar. Se usan las opciones descargadas anteriormente.' : 'No fue posible cargar las opciones de venta; conecta el equipo para descargarlas.';
      }
    });
    this.api.get<any>('/api/loyalty/pos/status').subscribe({next:r=>this.loyaltyEnabled=!!r.enabled,error:()=>this.loyaltyEnabled=false});
  }

  private async loadCachedOptions(): Promise<void> {
    const cached = await this.outbox.cachedPosOptions();
    if (cached) { this.customers = cached['clientes'] ?? []; this.inventory = cached['inventario'] ?? []; }
  }

  get branches(): any[] {
    return this.inventory.filter((item, index, all) => all.findIndex(row => row.id_sucursal === item.id_sucursal) === index)
      .map(item => ({ id_sucursal: item.id_sucursal, nombre: item.sucursal }));
  }
  get branchInventory(): any[] { return this.inventory.filter(item => Number(item.id_sucursal) === Number(this.branchId)); }
  get subtotal(): number { return this.lines.reduce((sum, item) => sum + item.cantidad * Number(item.precio), 0); }
  get total(): number { return Math.max(0, this.subtotal - this.loyaltyDiscount); }
  clearCustomer(): void { this.customerId = 0; this.pointsToRedeem=0;this.loyaltyDiscount=0;this.loyaltyBalance=0; }
  refreshLoyalty(): void {this.pointsToRedeem=0;this.loyaltyDiscount=0;this.loyaltyBalance=0;this.loyaltyError='';if(this.customerId)this.api.get<any>(`/api/loyalty/pos/customer/${this.customerId}`).subscribe({next:r=>this.loyaltyBalance=r.balance,error:()=>this.loyaltyEnabled=false});}
  estimateLoyalty(): void {this.loyaltyDiscount=0;this.loyaltyError='';if(!this.customerId||!this.pointsToRedeem||!this.subtotal)return;this.api.post<any>('/api/loyalty/pos/estimate',{customer_id:this.customerId,amount:this.subtotal,points:Number(this.pointsToRedeem)}).subscribe({next:r=>{this.pointsToRedeem=Number(r.points);this.loyaltyDiscount=Number(r.discount);this.loyaltyBalance=Number(r.balance);},error:e=>{this.loyaltyError=e.error?.detail??'No se pudo estimar el canje.';}});}
  clearLines(): void { this.lines = []; this.inventoryId = 0; this.estimateLoyalty(); }
  clearInvoice(): void { if (!this.invoice) { this.nitCi = ''; this.businessName = ''; } }

  add(): void {
    const item = this.branchInventory.find(row => row.id_inventario === this.inventoryId);
    if (!item || this.quantity < 1 || !Number.isInteger(Number(this.quantity))) return;
    const line = this.lines.find(row => row.id_inventario === item.id_inventario);
    if ((line?.cantidad || 0) + this.quantity > item.stock) { this.message = 'Stock descargado insuficiente; se validará nuevamente al sincronizar.'; return; }
    line ? line.cantidad += this.quantity : this.lines.push({ ...item, cantidad: Number(this.quantity) });
    this.estimateLoyalty();
  }
  remove(id: number): void { this.lines = this.lines.filter(item => item.id_inventario !== id); this.estimateLoyalty(); }

  private valid(): boolean {
    if (this.customerType === 'CLIENTE_REGISTRADO' && !this.customerId) { this.message = 'Seleccione un cliente registrado'; return false; }
    if (this.invoice && (!this.nitCi || !this.businessName)) { this.message = 'Complete NIT/CI y razón social'; return false; }
    if (!this.branchId || this.lines.some(item => Number(item.id_sucursal) !== Number(this.branchId))) { this.message = 'Seleccione una sucursal válida para la venta'; return false; }
    if (this.paymentMethod === 'EFECTIVO' && (this.cashReceived === null || !Number.isFinite(Number(this.cashReceived)) || Number(this.cashReceived) < this.total)) { this.message = 'El efectivo recibido debe cubrir el total calculado'; return false; }
    return true;
  }

  async sell(): Promise<void> {
    if (!this.valid()) return;
    this.busy = true;
    const common = {
      id_cliente: this.customerType === 'CLIENTE_REGISTRADO' ? this.customerId : null,
      nit_ci: this.invoice ? this.nitCi : null, razon_social: this.invoice ? this.businessName : null,
      id_sucursal: this.branchId, importe_recibido: this.cashReceived,
      lineas: this.lines.map(item => ({ id_variante: item.id_variante, cantidad: item.cantidad }))
    };
    if (!navigator.onLine && this.paymentMethod !== 'EFECTIVO') {
      this.busy = false; this.message = 'Las ventas offline solo admiten efectivo.'; return;
    }
    if (!navigator.onLine && this.pointsToRedeem > 0) {
      this.busy = false; this.message = 'El canje de puntos requiere conexión. No se descontaron puntos.'; return;
    }
    if (this.paymentMethod === 'EFECTIVO') {
      try {
        const queued = await this.outbox.queuePosCashSale(common);
        if (queued.status === 'RECHAZADA') {
          this.message = queued.error_message ?? 'El servidor rechazó la venta; revisa el stock o los datos antes de corregirla.';
        } else if (queued.status === 'SINCRONIZADA') {
          this.lines = [];
          const orderId = queued.result?.['id_pedido'];
          this.message = `Venta ${orderId ? `#${orderId} ` : ''}sincronizada y confirmada en efectivo.`;
          void this.loadOptions();
        } else {
          this.lines = [];
          this.message = `Venta guardada como pendiente (${queued.operation_uuid.slice(0, 8)}). El servidor validará precio e inventario al sincronizar.`;
        }
      } catch (error: any) { this.message = error?.message ?? 'No se pudo guardar la venta localmente.'; }
      finally { this.busy = false; }
      return;
    }
    this.api.post<any>('/api/commerce/pos', {
      id_cliente: common.id_cliente, puntos_a_canjear:Number(this.pointsToRedeem||0), tipo_cliente: this.customerType, metodo_pago: this.paymentMethod,
      nit_ci: common.nit_ci, razon_social: common.razon_social, tipo_entrega: 'RECOJO_SUCURSAL',
      id_sucursal_entrega: this.branchId, items: this.lines.map(item => ({ id_inventario: item.id_inventario, cantidad: item.cantidad }))
    }).subscribe({
      next: response => { this.busy = false; this.lines = []; this.message = `Venta #${response.id_pedido} registrada correctamente.`; void this.loadOptions(); },
      error: error => { this.busy = false; this.message = error.error?.detail || 'No fue posible registrar la venta'; }
    });
  }
}
