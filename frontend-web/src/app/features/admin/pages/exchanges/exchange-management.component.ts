import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { ApiService } from '../../../../core/services/api.service';
import { OutboxSyncService } from '../../../../core/services/outbox-sync.service';

@Component({
  selector: 'app-exchange-management', standalone: true, imports: [CommonModule, FormsModule],
  template: `<section class="exchange-page">
    <header><div><p>OPERACIONES DE SUCURSAL</p><h1>Cambios de prendas</h1></div><button type="button" (click)="refresh()">Actualizar</button></header>
    @if (offline) { <p class="notice" role="status">Modo offline. Se muestran solicitudes descargadas; los cambios físicos quedarán en Outbox hasta recuperar conexión.</p> }
    <section aria-label="Solicitudes de cambio"><h2>Solicitudes e historial</h2>
      @if (!rows.length) { <p>No hay cambios registrados o descargados.</p> }
      @for (row of rows; track row.id ?? row.local_operation_uuid) {
        <article class="exchange-card">
          <div class="row-head"><h3>Cambio #{{row.id ?? row.local_operation_uuid}}</h3><span>{{row.state}}</span></div>
          <p>Pedido #{{row.original_order_id}} · {{row.original_product}} {{row.original_size}} / {{row.original_color}}</p>
          <p>Variante solicitada: {{row.replacement_product ?? 'Pendiente'}} {{row.replacement_size ?? ''}} / {{row.replacement_color ?? ''}} · sucursal {{row.branch_name ?? row.branch_id}}</p>
          <p>Inspección: {{row.inspection_state}} · diferencia: {{row.economic_difference ?? 'pendiente'}} · {{row.financial_state}}</p>
          @if (row.reconciliation_note) { <p class="notice">{{row.reconciliation_note}}</p> }
          @if (!offline && ['SOLICITADO','PENDIENTE_INSPECCION','PENDIENTE_DISPONIBILIDAD'].includes(row.state)) {
            <div class="controls"><label><input type="checkbox" [(ngModel)]="good[row.id]"> Buen estado</label><label><input type="checkbox" [(ngModel)]="tag[row.id]"> Conserva etiqueta</label>
              <button type="button" (click)="inspect(row,true)" [disabled]="busy">Aprobar inspección y recibir</button>
              <button type="button" (click)="inspect(row,false)" [disabled]="busy">Rechazar con motivo</button>
            </div>
            @if (options[row.id]; as option) {
              <div class="controls"><label>Variante sustituta <select [(ngModel)]="replacement[row.id]"><option [ngValue]="null">Seleccionar</option>@for(v of option.variantes;track v.id_variante){<option [ngValue]="v.id_variante">{{v.producto}} · {{v.talla}} · {{v.color}}</option>}</select></label>
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
          @if (!offline && ['APROBADO','PENDIENTE_DEVOLUCION'].includes(row.state) && !row.physical_replacement_delivered) { <button type="button" (click)="deliver(row)" [disabled]="busy">Registrar entrega sustituta</button> }
          @if (row.sync_status) { <p>Estado local de sincronización: {{row.sync_status}} {{row.sync_message ?? ''}}</p> }
        </article>
      }
    </section>
    <section aria-label="Incidencias de inventario"><h2>Incidencias de conciliación</h2>
      @for (incident of incidents; track incident.id) { <article class="incident-card"><strong>Incidencia #{{incident.id}} · {{incident.state}}</strong><p>Cambio #{{incident.exchange_id}} · sucursal {{incident.branch_id}} · variante {{incident.variant_id}} · salida física {{incident.quantity}}</p><p>{{incident.reason}}</p>
        @if (incident.state === 'INCIDENCIA_CONCILIACION' && !offline) { <label>Stock real <input type="number" min="0" [(ngModel)]="actualStock[incident.id]"></label><label>Motivo del ajuste <input [(ngModel)]="adjustmentReason[incident.id]"></label><button type="button" (click)="reconcile(incident)" [disabled]="busy">Conciliar con ajuste autorizado</button> }
      </article> }
    </section>
  </section>`,
  styles: [`.exchange-page{max-width:72rem;margin:auto;padding:2rem}header,.row-head,.controls{display:flex;gap:1rem;align-items:center;justify-content:space-between;flex-wrap:wrap}.exchange-card,.incident-card{border:1px solid #d8ded9;border-radius:12px;padding:1rem;margin:1rem 0}.controls{justify-content:flex-start;margin:.8rem 0}label{display:flex;gap:.4rem;align-items:center}.notice{padding:.8rem;background:#fff2cc;border-radius:8px}`]
})
export class ExchangeManagementComponent implements OnInit {
  private readonly api = inject(ApiService);
  private readonly outbox = inject(OutboxSyncService);
  rows: any[] = []; incidents: any[] = []; options: Record<number, any> = {};
  good: Record<number, boolean> = {}; tag: Record<number, boolean> = {};
  replacement: Record<number, number | null> = {}; replacementBranch: Record<number, number | null> = {};
  actualStock: Record<number, number> = {}; adjustmentReason: Record<number, string> = {};
  offline = !navigator.onLine; busy = false;
  ngOnInit(): void { void this.refresh(); window.addEventListener('online', this.connectionChanged); window.addEventListener('offline', this.connectionChanged); }
  private connectionChanged = (): void => { this.offline = !navigator.onLine; void this.refresh(); };
  async refresh(): Promise<void> {
    this.offline = !navigator.onLine;
    if (!this.offline) {
      try {
        this.rows = await firstValueFrom(this.api.get<any[]>('/api/admin/exchanges'));
        this.incidents = await firstValueFrom(this.api.get<any[]>('/api/admin/exchanges/incidents'));
        await this.outbox.cacheExchanges(this.rows);
        return;
      } catch { this.offline = true; }
    }
    this.rows = await this.outbox.cachedExchanges();
  }
  async loadOptions(row: any): Promise<void> { this.busy = true; try { this.options[row.id] = await firstValueFrom(this.api.get<any>(`/api/admin/exchanges/${row.id}/options`)); } finally { this.busy = false; } }
  async inspect(row: any, approved: boolean): Promise<void> {
    this.busy = true;
    try {
      const result = await firstValueFrom(this.api.post<any>(`/api/admin/exchanges/${row.id}/inspection`, {
        aprobado: approved, buen_estado: !!this.good[row.id], etiqueta_original: !!this.tag[row.id],
        motivo_rechazo: approved ? null : 'La prenda no cumple las condiciones para el cambio',
        id_variante_sustituta: this.replacement[row.id] ?? row.replacement_variant_id ?? null,
        id_sucursal_sustituta: this.replacementBranch[row.id] ?? row.branch_id
      }));
      this.replaceRow(result);
    } finally { this.busy = false; }
  }
  async chooseReplacement(row: any): Promise<void> {
    const variant = this.replacement[row.id], branch = this.replacementBranch[row.id];
    if (!variant || !branch) return;
    this.busy = true;
    try { this.replaceRow(await firstValueFrom(this.api.put<any>(`/api/admin/exchanges/${row.id}/replacement`, {id_variante_sustituta: variant, id_sucursal_sustituta: branch}))); }
    finally { this.busy = false; }
  }
  async deliver(row: any): Promise<void> { this.busy = true; try { this.replaceRow(await firstValueFrom(this.api.post<any>(`/api/admin/exchanges/${row.id}/deliver`, {}))); } finally { this.busy = false; } }
  async recordPhysicalOffline(row: any): Promise<void> {
    await this.outbox.queuePhysicalExchange(row, { id_detalle: row.original_detail_id,
      id_sucursal: row.branch_id, id_variante_sustituta: row.replacement_variant_id,
      prenda_recibida: true, prenda_entregada: true, buen_estado: !!this.good[row.id],
      etiqueta_original: !!this.tag[row.id], motivo: 'Cambio presencial registrado sin conexión' });
    await this.refresh();
  }
  async reconcile(row: any): Promise<void> {
    const stock = this.actualStock[row.id]; const reason = this.adjustmentReason[row.id]?.trim();
    if (!Number.isInteger(stock) || stock < 0 || !reason) return;
    this.busy = true;
    try { await firstValueFrom(this.api.post(`/api/admin/exchanges/incidents/${row.id}/reconcile`, {stock_real: stock, motivo: reason})); await this.refresh(); }
    finally { this.busy = false; }
  }
  private replaceRow(row: any): void { this.rows = this.rows.map(value => value.id === row.id ? row : value); void this.outbox.cacheExchanges(this.rows); }
}
