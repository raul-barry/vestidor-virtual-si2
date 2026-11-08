import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { ApiService } from '../../../../core/services/api.service';
import { OutboxSyncService } from '../../../../core/services/outbox-sync.service';
import { TokenService } from '../../../../core/services/token.service';

@Component({
  selector: 'app-exchange-management', standalone: true, imports: [CommonModule, FormsModule],
  template: `<section class="exchange-page">
    <header><div><p>OPERACIONES DE SUCURSAL</p><h1>Cambios de prendas</h1></div><button type="button" (click)="refresh()" [disabled]="busy">Actualizar</button></header>
    @if (offline) { <p class="notice" role="status">Modo offline. Se muestran solicitudes descargadas; los cambios físicos quedarán en Outbox hasta recuperar conexión.</p> }
    @if (loadError) { <p class="error" role="alert">{{loadError}}</p> }
    <section class="lookup" aria-label="Buscar venta para cambio">
      <h2>Registrar cambio en sucursal</h2>
      <p>Busca el código de una venta confirmada. Puedes usar el número del pedido, #número o PED-número.</p>
      <form (ngSubmit)="findSale()"><label>Código de venta <input name="saleCode" [(ngModel)]="saleCode" required autocomplete="off" placeholder="PED-123"></label>
        <button type="submit" [disabled]="busy || offline || !saleCode.trim()">{{lookupBusy ? 'Buscando…' : 'Buscar venta'}}</button></form>
      @if (lookupError) { <p class="error" role="alert">{{lookupError}}</p> }
      @if (sale; as found) {
        <article class="sale-card">
          <h3>{{found.codigo}} · {{found.fecha_confirmacion | date:'medium'}}</h3>
          <p>Estado: {{found.estado}} · pago: {{found.estado_pago}}</p>
          @if (!found.elegible) { <p class="error" role="alert">{{found.motivo_no_elegible || 'Esta venta no admite cambios.'}}</p> }
          @if (found.elegible && !found.detalles.length) { <p class="notice">La venta no tiene detalles disponibles en esta sucursal.</p> }
          @for (line of found.detalles; track line.id_detalle) {
            <article class="sale-line"><h4>{{line.producto}} · {{line.talla}} / {{line.color}}</h4>
              <p>Compradas: {{line.cantidad_comprada}} · Disponibles para cambio: {{line.cantidad_disponible_para_cambio}} · Sucursal: {{line.sucursal}}</p>
              @if (found.elegible && line.cantidad_disponible_para_cambio > 0) {
                <div class="controls">
                  <label>Cantidad <input type="number" min="1" [max]="line.cantidad_disponible_para_cambio" [(ngModel)]="exchangeQuantity[line.id_detalle]" name="quantity-{{line.id_detalle}}"></label>
                  <label>Variante nueva <select [(ngModel)]="replacement[line.id_detalle]" name="replacement-{{line.id_detalle}}"><option [ngValue]="null">Seleccionar variante</option>
                    @for (variant of line.variantes_sustitutas; track variant.id_variante) { <option [ngValue]="variant.id_variante" [disabled]="variant.stock_disponible < (exchangeQuantity[line.id_detalle] || 1)">{{variant.producto}} · {{variant.talla}} · {{variant.color}} · stock {{variant.stock_disponible}}</option> }
                  </select></label>
                  <label>Motivo <input [(ngModel)]="reason[line.id_detalle]" name="reason-{{line.id_detalle}}" maxlength="255" required placeholder="Talla o color"></label>
                  <button type="button" (click)="registerChange(line)" [disabled]="busy || !validLine(line)">{{busy ? 'Registrando…' : 'Confirmar cambio'}}</button>
                </div>
              } @else if (found.elegible) { <p>La cantidad comprada ya fue cambiada.</p> }
            </article>
          }
        </article>
      }
      @if (receipt; as proof) {
        <article class="receipt" aria-label="Comprobante del cambio">
          <h3>Comprobante de cambio #{{proof.id}}</h3><p>Venta {{proof.original_order_id}} · {{proof.requested_at | date:'medium'}}</p>
          <p>{{proof.original_product}} {{proof.original_size}} / {{proof.original_color}} → {{proof.replacement_product}} {{proof.replacement_size}} / {{proof.replacement_color}}</p>
          <p>Cantidad: {{proof.quantity}} · Sucursal: {{proof.branch_name}} · Estado: {{proof.state}}</p><p>Motivo: {{proof.reason}}</p>
          <button type="button" (click)="printReceipt()">Imprimir comprobante</button>
        </article>
      }
      @if (successMessage) { <p class="success" role="status">{{successMessage}}</p> }
    </section>
    <section aria-label="Solicitudes de cambio"><h2>Solicitudes e historial</h2>
      @if (!rows.length) { <p>No hay cambios registrados o descargados.</p> }
      @for (row of rows; track row.id ?? row.local_operation_uuid) {
        <article class="exchange-card">
          <div class="row-head"><h3>Cambio #{{row.id ?? row.local_operation_uuid}}</h3><span>{{row.state}}</span></div>
          <p>Fecha: {{row.requested_at | date:'medium'}} · Cantidad: {{row.quantity}} · Responsable: {{row.employee_id ?? 'Pendiente de asignación'}}</p>
          <p>Pedido #{{row.original_order_id}} · {{row.original_product}} {{row.original_size}} / {{row.original_color}}</p>
          <p>Variante solicitada: {{row.replacement_product ?? 'Pendiente'}} {{row.replacement_size ?? ''}} / {{row.replacement_color ?? ''}} · sucursal {{row.branch_name ?? row.branch_id}}</p>
          <p>Motivo: {{row.reason}}</p>
          <p>Inspección: {{row.inspection_state}} · diferencia: {{row.economic_difference ?? 'pendiente'}} · {{row.financial_state}}</p>
          @if (row.reconciliation_note) { <p class="notice">{{row.reconciliation_note}}</p> }
          @if (!offline && canManageRequests && ['SOLICITADO','PENDIENTE_INSPECCION','PENDIENTE_DISPONIBILIDAD'].includes(row.state)) {
            <div class="controls"><label><input type="checkbox" [(ngModel)]="good[row.id]"> Buen estado</label><label><input type="checkbox" [(ngModel)]="tag[row.id]"> Conserva etiqueta</label>
              <button type="button" (click)="inspect(row,true)" [disabled]="busy">Aprobar inspección y recibir</button>
              <button type="button" (click)="inspect(row,false)" [disabled]="busy">Rechazar con motivo</button>
            </div>
            @if (options[row.id]; as option) {
              <div class="controls"><label>Variante sustituta <select [(ngModel)]="replacementExisting[row.id]"><option [ngValue]="null">Seleccionar</option>@for(v of option.variantes;track v.id_variante){<option [ngValue]="v.id_variante">{{v.producto}} · {{v.talla}} · {{v.color}}</option>}</select></label>
                <label>Sucursal entrega <select [(ngModel)]="replacementBranch[row.id]"><option [ngValue]="null">Seleccionar</option>@for(b of option.sucursales;track b.id_sucursal){<option [ngValue]="b.id_sucursal">{{b.nombre}}</option>}</select></label>
                <button type="button" (click)="chooseReplacement(row)" [disabled]="busy">Guardar sustituto</button>
              </div>
            } @else { <button type="button" (click)="loadOptions(row)" [disabled]="busy || offline">Ver variantes y sucursales</button> }
          }
          @if (offline && row.state === 'SOLICITADO') {
            <div class="controls"><label><input type="checkbox" [(ngModel)]="good[row.id]"> Inspeccionada en buen estado</label><label><input type="checkbox" [(ngModel)]="tag[row.id]"> Etiqueta original presente</label>
              <button type="button" (click)="recordPhysicalOffline(row)" [disabled]="!good[row.id] || !tag[row.id] || !row.replacement_variant_id">Registrar recepción y entrega física</button>
            </div>
          }
          @if (!offline && canManageRequests && ['APROBADO','PENDIENTE_DEVOLUCION'].includes(row.state) && !row.physical_replacement_delivered) { <button type="button" (click)="deliver(row)" [disabled]="busy">Registrar entrega sustituta</button> }
          @if (row.sync_status) { <p>Estado local de sincronización: {{row.sync_status}} {{row.sync_message ?? ''}}</p> }
        </article>
      }
    </section>
    <section aria-label="Incidencias de inventario"><h2>Incidencias de conciliación</h2>
      @if (!incidents.length) { <p>No hay incidencias de inventario pendientes.</p> }
      @for (incident of incidents; track incident.id) { <article class="incident-card"><strong>Incidencia #{{incident.id}} · {{incident.state}}</strong><p>Cambio #{{incident.exchange_id}} · sucursal {{incident.branch_id}} · variante {{incident.variant_id}} · salida física {{incident.quantity}}</p><p>{{incident.reason}}</p>
        @if (incident.state === 'INCIDENCIA_CONCILIACION' && !offline && isAdmin) { <label>Stock real <input type="number" min="0" [(ngModel)]="actualStock[incident.id]"></label><label>Motivo del ajuste <input [(ngModel)]="adjustmentReason[incident.id]"></label><button type="button" (click)="reconcile(incident)" [disabled]="busy">Conciliar con ajuste autorizado</button> }
      </article> }
    </section>
  </section>`,
  styles: [`.exchange-page{max-width:72rem;margin:auto;padding:2rem}header,.row-head,.controls,form{display:flex;gap:1rem;align-items:center;justify-content:space-between;flex-wrap:wrap}.lookup,.exchange-card,.incident-card,.sale-card,.sale-line,.receipt{border:1px solid #d8ded9;border-radius:12px;padding:1rem;margin:1rem 0}.controls{justify-content:flex-start;margin:.8rem 0}label{display:flex;gap:.4rem;align-items:center}input,select{padding:.55rem;border:1px solid #aab7b0;border-radius:6px}.notice{padding:.8rem;background:#fff2cc;border-radius:8px}.error{padding:.8rem;background:#fce8e6;color:#8b1d16;border-radius:8px}.success{padding:.8rem;background:#e3f5eb;color:#145c37;border-radius:8px}@media print{body *{visibility:hidden}.receipt,.receipt *{visibility:visible}.receipt{position:absolute;inset:0;border:0}}`]
})
export class ExchangeManagementComponent implements OnInit {
  private readonly api = inject(ApiService);
  private readonly outbox = inject(OutboxSyncService);
  private readonly token = inject(TokenService);
  rows: any[] = []; incidents: any[] = []; options: Record<number, any> = {};
  good: Record<number, boolean> = {}; tag: Record<number, boolean> = {};
  replacementExisting: Record<number, number | null> = {}; replacementBranch: Record<number, number | null> = {};
  actualStock: Record<number, number> = {}; adjustmentReason: Record<number, string> = {};
  saleCode = ''; sale: any = null; receipt: any = null; lookupError = ''; loadError = ''; successMessage = '';
  replacement: Record<number, number | null> = {}; exchangeQuantity: Record<number, number> = {};
  reason: Record<number, string> = {}; offline = !navigator.onLine; busy = false; lookupBusy = false;
  get isAdmin(): boolean { return this.token.getRole() === 'ADMINISTRADOR'; }
  get canManageRequests(): boolean { return this.token.getRole() !== 'CAJERO'; }
  ngOnInit(): void { void this.refresh(); window.addEventListener('online', this.connectionChanged); window.addEventListener('offline', this.connectionChanged); }
  private connectionChanged = (): void => { this.offline = !navigator.onLine; void this.refresh(); };
  async refresh(): Promise<void> {
    this.offline = !navigator.onLine;
    if (!this.offline) {
      try {
        this.rows = await firstValueFrom(this.api.get<any[]>('/api/admin/exchanges'));
        this.incidents = await firstValueFrom(this.api.get<any[]>('/api/admin/exchanges/incidents'));
        await this.outbox.cacheExchanges(this.rows); this.loadError = ''; return;
      } catch { this.offline = true; this.loadError = 'No se pudo actualizar el historial desde el servidor.'; }
    }
    this.rows = await this.outbox.cachedExchanges(); this.incidents = [];
  }
  async findSale(): Promise<void> {
    const code = this.saleCode.trim(); if (!code || this.offline || this.lookupBusy) return;
    this.lookupBusy = true; this.lookupError = ''; this.sale = null; this.receipt = null; this.successMessage = '';
    try { this.sale = await firstValueFrom(this.api.get<any>(`/api/admin/exchanges/sales/${encodeURIComponent(code)}`)); }
    catch (error: any) { this.lookupError = error?.error?.detail || 'No se pudo consultar la venta. Intenta nuevamente.'; }
    finally { this.lookupBusy = false; }
  }
  validLine(line: any): boolean {
    const quantity = Number(this.exchangeQuantity[line.id_detalle] ?? 1);
    return Number.isInteger(quantity) && quantity > 0 && quantity <= line.cantidad_disponible_para_cambio
      && !!this.replacement[line.id_detalle] && !!this.reason[line.id_detalle]?.trim();
  }
  async registerChange(line: any): Promise<void> {
    if (!this.sale?.elegible || !this.validLine(line) || this.busy) return;
    this.busy = true; this.lookupError = ''; this.successMessage = '';
    try {
      this.receipt = await firstValueFrom(this.api.post<any>('/api/admin/exchanges/register', {
        operation_uuid: crypto.randomUUID(), id_detalle: line.id_detalle,
        id_variante_sustituta: this.replacement[line.id_detalle],
        cantidad: Number(this.exchangeQuantity[line.id_detalle] ?? 1), motivo: this.reason[line.id_detalle].trim()
      }));
      this.successMessage = `Cambio #${this.receipt.id} registrado y guardado.`;
      const saleCode = this.saleCode.trim().toUpperCase().replace(/^PED-|^#/, '');
      this.sale = await firstValueFrom(this.api.get<any>(`/api/admin/exchanges/sales/${encodeURIComponent(saleCode)}`));
      await this.refresh();
    } catch (error: any) { this.lookupError = error?.error?.detail || 'No se pudo registrar el cambio.'; }
    finally { this.busy = false; }
  }
  printReceipt(): void { window.print(); }
  async loadOptions(row: any): Promise<void> { this.busy = true; try { this.options[row.id] = await firstValueFrom(this.api.get<any>(`/api/admin/exchanges/${row.id}/options`)); } finally { this.busy = false; } }
  async inspect(row: any, approved: boolean): Promise<void> {
    this.busy = true;
    try {
      const result = await firstValueFrom(this.api.post<any>(`/api/admin/exchanges/${row.id}/inspection`, {
        aprobado: approved, buen_estado: !!this.good[row.id], etiqueta_original: !!this.tag[row.id],
        motivo_rechazo: approved ? null : 'La prenda no cumple las condiciones para el cambio',
        id_variante_sustituta: this.replacementExisting[row.id] ?? row.replacement_variant_id ?? null,
        id_sucursal_sustituta: this.replacementBranch[row.id] ?? row.branch_id
      })); this.replaceRow(result);
    } finally { this.busy = false; }
  }
  async chooseReplacement(row: any): Promise<void> {
    const variant = this.replacementExisting[row.id], branch = this.replacementBranch[row.id]; if (!variant || !branch) return;
    this.busy = true;
    try { this.replaceRow(await firstValueFrom(this.api.put<any>(`/api/admin/exchanges/${row.id}/replacement`, {id_variante_sustituta: variant, id_sucursal_sustituta: branch}))); }
    finally { this.busy = false; }
  }
  async deliver(row: any): Promise<void> { this.busy = true; try { this.replaceRow(await firstValueFrom(this.api.post<any>(`/api/admin/exchanges/${row.id}/deliver`, {}))); } finally { this.busy = false; } }
  async recordPhysicalOffline(row: any): Promise<void> {
    await this.outbox.queuePhysicalExchange(row, { id_detalle: row.original_detail_id,
      id_sucursal: row.branch_id, id_variante_sustituta: row.replacement_variant_id,
      prenda_recibida: true, prenda_entregada: true, buen_estado: !!this.good[row.id],
      etiqueta_original: !!this.tag[row.id], motivo: 'Cambio presencial registrado sin conexión' }); await this.refresh();
  }
  async reconcile(row: any): Promise<void> {
    const stock = this.actualStock[row.id]; const reason = this.adjustmentReason[row.id]?.trim();
    if (!Number.isInteger(stock) || stock < 0 || !reason) return;
    this.busy = true; try { await firstValueFrom(this.api.post(`/api/admin/exchanges/incidents/${row.id}/reconcile`, {stock_real: stock, motivo: reason})); await this.refresh(); }
    finally { this.busy = false; }
  }
  private replaceRow(row: any): void { this.rows = this.rows.map(value => value.id === row.id ? row : value); void this.outbox.cacheExchanges(this.rows); }
}
