import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../../core/services/api.service';

type Refund = {
  id: number; payment_id: number; order_id: number; amount: string; currency: string;
  method: string; state: string; reason: string; provider_reference?: string;
  evidence_reference?: string; simulated: boolean; error_message?: string;
};
type Adjustment = { id: number; exchange_id: number; amount: string; currency: string; state: string; provider?: string; provider_reference?: string; simulated: boolean };

@Component({
  selector: 'app-financial-reconciliation', standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <section class="page">
      <h1>Conciliación de pagos y devoluciones</h1>
      <p>Estado financiero de tu organización. El importe de devolución lo calcula el servidor.</p>
      <p *ngIf="error" role="alert">{{ error }}</p>
      <button type="button" (click)="load()" [disabled]="loading">Actualizar</button>
      <p *ngIf="notice" role="status">{{ notice }}</p>
      <h2>Pagos pendientes o que requieren revisión</h2>
      <table><thead><tr><th>Pedido</th><th>Método</th><th>Importe</th><th>Estado</th><th>Proveedor</th><th>Referencia</th><th>Acción</th></tr></thead>
        <tbody><tr *ngFor="let p of payments"><td>{{p['id_pedido']}}</td><td>{{p['metodo_pago']}}</td><td>{{p['monto']}} {{p['currency']}}</td><td>{{p['estado']}}</td><td>{{p['simulated'] ? 'Simulado' : (p['proveedor'] || '—')}}</td><td>{{p['referencia_externa'] || '—'}}</td><td><ng-container *ngIf="canResolveSimulation(p)"><button type="button" (click)="resolveSimulation(p, true)" [disabled]="loading">Aprobar simulación</button><button type="button" (click)="resolveSimulation(p, false)" [disabled]="loading">Rechazar simulación</button></ng-container></td></tr></tbody>
      </table>
      <h2>Historial de pagos</h2>
      <table><thead><tr><th>Pedido</th><th>Método</th><th>Importe</th><th>Estado</th><th>Proveedor</th><th>Referencia</th></tr></thead>
        <tbody><tr *ngFor="let p of paymentHistory"><td>{{p['id_pedido']}}</td><td>{{p['metodo_pago']}}</td><td>{{p['monto']}} {{p['currency']}}</td><td>{{p['estado']}}</td><td>{{p['simulated'] ? 'Simulado' : (p['proveedor'] || '—')}}</td><td>{{p['referencia_externa'] || '—'}}</td></tr></tbody>
      </table>
      <h2>Solicitar devolución</h2>
      <form (ngSubmit)="requestRefund()">
        <label>Pago <input name="payment" type="number" min="1" [(ngModel)]="form.payment_id" required></label>
        <label>Cambio CU29 <input name="exchange" type="number" min="1" [(ngModel)]="form.exchange_id"></label>
        <label>Devolución física <input name="return" type="number" min="1" [(ngModel)]="form.return_id"></label>
        <label>Canal <select name="method" [(ngModel)]="form.method"><option value="MEDIO_ORIGINAL">Medio original</option><option value="EFECTIVO">Efectivo</option><option value="TRANSFERENCIA">Transferencia documentada</option></select></label>
        <label>Motivo <input name="reason" maxlength="255" [(ngModel)]="form.reason" required></label>
        <label *ngIf="form.method !== 'MEDIO_ORIGINAL'">Comprobante <input name="evidence" maxlength="255" [(ngModel)]="form.evidence_reference"></label>
        <button type="submit" [disabled]="loading">Registrar solicitud</button>
      </form>
      <h2>Devoluciones</h2>
      <table><thead><tr><th>Pedido</th><th>Pago</th><th>Importe</th><th>Canal</th><th>Estado</th><th>Referencia</th><th>Acción</th></tr></thead>
        <tbody><tr *ngFor="let r of refunds"><td>{{r.order_id}}</td><td>{{r.payment_id}}</td><td>{{r.amount}} {{r.currency}}</td><td>{{r.method}}<span *ngIf="r.simulated"> · SIMULADA</span></td><td>{{r.state}}</td><td>{{r.provider_reference || r.evidence_reference || '—'}}</td><td><form *ngIf="r.method !== 'MEDIO_ORIGINAL' && r.state !== 'DEVOLUCION_COMPLETADA'" (ngSubmit)="complete(r)"><input name="evidence-{{r.id}}" [(ngModel)]="evidence[r.id]" placeholder="Referencia de entrega" required><button type="submit">Confirmar con comprobante</button></form></td></tr></tbody>
      </table>
      <h2>Diferencias de precio de cambios CU29</h2>
      <table><thead><tr><th>Cambio</th><th>Importe</th><th>Estado</th><th>Proveedor</th><th>Referencia</th></tr></thead>
        <tbody><tr *ngFor="let a of adjustments"><td>{{a.exchange_id}}</td><td>{{a.amount}} {{a.currency}}</td><td>{{a.state}}</td><td>{{a.simulated ? 'Simulado' : (a.provider || '—')}}</td><td>{{a.provider_reference || '—'}}</td></tr></tbody>
      </table>
    </section>`,
  styles: [`.page{padding:1.5rem;max-width:1100px;margin:auto} form{display:flex;flex-wrap:wrap;gap:1rem;margin:1rem 0 2rem}label{display:grid;gap:.35rem}input,select,button{padding:.55rem}table{width:100%;border-collapse:collapse;margin:1rem 0 2rem}th,td{text-align:left;border-bottom:1px solid #ddd;padding:.6rem}`]
})
export class FinancialReconciliationComponent implements OnInit {
  private readonly api = inject(ApiService);
  loading = false;
  error = '';
  notice = '';
  payments: Array<Record<string, any>> = [];
  paymentHistory: Array<Record<string, any>> = [];
  refunds: Refund[] = [];
  adjustments: Adjustment[] = [];
  evidence: Record<number, string> = {};
  form: { payment_id: number | null; exchange_id: number | null; return_id: number | null; method: string; reason: string; evidence_reference: string } = {
    payment_id: null, exchange_id: null, return_id: null, method: 'MEDIO_ORIGINAL', reason: '', evidence_reference: ''
  };

  ngOnInit(): void { this.load(); }
  canResolveSimulation(payment: Record<string, any>): boolean {
    return payment['simulated'] === true && ['PENDIENTE', 'PROCESANDO'].includes(payment['estado']);
  }
  load(): void {
    this.loading = true; this.error = '';
    this.api.get<{ payments: Array<Record<string, any>>; payment_history: Array<Record<string, any>>; refunds: Refund[]; adjustments: Adjustment[] }>('/api/payments/reconciliation').subscribe({
      next: result => { this.payments = result.payments; this.paymentHistory = result.payment_history ?? []; this.refunds = result.refunds; this.adjustments = result.adjustments ?? []; this.loading = false; },
      error: err => { this.error = err?.error?.detail ?? 'No se pudieron consultar las operaciones financieras.'; this.loading = false; }
    });
  }
  resolveSimulation(payment: Record<string, any>, approved: boolean): void {
    if (!this.canResolveSimulation(payment) || this.loading) return;
    const decision = approved ? 'aprobar' : 'rechazar';
    if (!window.confirm(`¿Confirmas ${decision} el pago simulado del pedido #${payment['id_pedido']}?`)) return;
    this.loading = true; this.error = ''; this.notice = '';
    this.api.put(`/api/payments/reconciliation/${payment['id_pago']}/simulate`, { approved }).subscribe({
      next: () => { this.notice = approved ? 'Pago simulado aprobado.' : 'Pago simulado rechazado.'; this.load(); },
      error: err => { this.error = err?.error?.detail ?? 'No se pudo resolver el pago simulado.'; this.loading = false; }
    });
  }
  requestRefund(): void {
    if (!this.form.payment_id || !this.form.reason.trim() || (!!this.form.exchange_id === !!this.form.return_id)) {
      this.error = 'Indica un pago, exactamente un cambio o devolución, y un motivo.'; return;
    }
    this.loading = true; this.error = '';
    this.api.post('/api/payments/refunds', { ...this.form, operation_uuid: crypto.randomUUID() }).subscribe({
      next: () => { this.form = { payment_id: null, exchange_id: null, return_id: null, method: 'MEDIO_ORIGINAL', reason: '', evidence_reference: '' }; this.load(); },
      error: err => { this.error = err?.error?.detail ?? 'No se pudo registrar la devolución.'; this.loading = false; }
    });
  }
  complete(refund: Refund): void {
    const reference = this.evidence[refund.id]?.trim();
    if (!reference) { this.error = 'Añade una referencia de comprobante.'; return; }
    this.loading = true;
    this.api.post(`/api/payments/refunds/${refund.id}/evidence`, { evidence_reference: reference }).subscribe({
      next: () => this.load(),
      error: err => { this.error = err?.error?.detail ?? 'No se pudo confirmar la devolución.'; this.loading = false; }
    });
  }
}
