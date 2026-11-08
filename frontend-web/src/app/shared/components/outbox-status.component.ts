import { DatePipe, JsonPipe } from '@angular/common';
import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { Subscription, filter } from 'rxjs';
import { OutboxSummary, OutboxSyncService } from '../../core/services/outbox-sync.service';

@Component({
  selector: 'app-outbox-status', standalone: true, imports: [DatePipe, JsonPipe],
  template: `
    <details class="sync-center">
      <summary aria-label="Abrir centro de sincronización">
        <span class="connection-dot" [class.offline]="!summary.online"></span>
        <span>{{ summary.online ? 'Con conexión' : 'Sin conexión' }}</span>
        <span class="count">Pendientes {{ summary.pending }}</span>
        <span class="count success">Sincronizadas {{ summary.synchronized }}</span>
        <span class="count error">Rechazadas {{ summary.rejected }}</span>
      </summary>
      <section class="history" aria-label="Historial de sincronización">
        <header><strong>Centro de sincronización</strong><span>Enviando {{summary.sending}} · Reintento {{summary.retryable}}</span></header>
        @if (summary.lastSync) { <p class="last-sync">Última sincronización: {{ summary.lastSync | date:'short' }}</p> }
        @for (operation of summary.operations ?? []; track operation.operation_uuid) {
          <article class="operation">
            <div><strong>{{operation.operation_type}}</strong><span>{{operation.created_at | date:'short'}}</span></div>
            <p class="state">{{operation.status}}</p>
            @if (operation.error_message) { <p class="reason" role="alert">{{operation.error_category}}: {{operation.error_message}}</p> }
            @if (operation.status === 'SINCRONIZADA' && operation.result) {
              <details class="confirmation"><summary>Ver confirmación del servidor</summary><pre>{{operation.result | json}}</pre></details>
            }
            @if (operation.status === 'ERROR_REINTENTABLE') { <button type="button" (click)="retry(operation.operation_uuid)">Reintentar</button> }
          </article>
        } @empty { <p>No hay operaciones en el historial.</p> }
      </section>
    </details>
  `,
  styles: [`.sync-center{position:relative;z-index:20;background:#f4f1ef;color:#342b31;font-size:.82rem}.sync-center>summary{display:flex;align-items:center;gap:.65rem;flex-wrap:wrap;padding:.45rem 1rem;cursor:pointer;list-style:none}.sync-center>summary::-webkit-details-marker{display:none}.connection-dot{width:.55rem;height:.55rem;border-radius:50%;background:#168252}.connection-dot.offline{background:#b45532}.count{border-radius:1rem;background:#e4e9e5;padding:.15rem .55rem}.count.success{color:#176c44}.count.error{color:#9c321f}.history{position:absolute;right:1rem;top:100%;width:min(36rem,calc(100vw - 2rem));max-height:min(70vh,38rem);overflow:auto;padding:1rem;background:#fff;border:1px solid #d8dfda;border-radius:.75rem;box-shadow:0 12px 32px #18231d33}.history header,.operation>div{display:flex;justify-content:space-between;gap:.75rem;align-items:center}.history header span,.operation>div span,.last-sync{color:#59645d;font-size:.78rem}.operation{padding:.7rem 0;border-top:1px solid #e5e9e6}.operation p{margin:.35rem 0}.state{font-size:.78rem}.reason{color:#9c321f}.confirmation pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f6f7f6;padding:.5rem;border-radius:.4rem}.operation button{border:0;border-radius:.35rem;padding:.4rem .7rem;background:#126b58;color:white;cursor:pointer}@media(max-width:600px){.history{right:.5rem;width:calc(100vw - 1rem)}.sync-center>summary{gap:.4rem;padding:.45rem .6rem}}`]
})
export class OutboxStatusComponent implements OnInit, OnDestroy {
  private readonly sync = inject(OutboxSyncService);
  private readonly router = inject(Router);
  private readonly subscriptions = new Subscription();
  summary: OutboxSummary = {
    pending: 0, sending: 0, synchronized: 0, rejected: 0, retryable: 0,
    lastSync: null, online: navigator.onLine, errors: [], operations: []
  };

  ngOnInit(): void {
    this.subscriptions.add(this.sync.summary$.subscribe(value => this.summary = value));
    this.subscriptions.add(this.router.events.pipe(filter(event => event instanceof NavigationEnd)).subscribe(() => {
      void this.sync.refresh();
    }));
  }
  ngOnDestroy(): void { this.subscriptions.unsubscribe(); }
  retry(operationUuid: string): void { void this.sync.retryOperation(operationUuid); }
}
