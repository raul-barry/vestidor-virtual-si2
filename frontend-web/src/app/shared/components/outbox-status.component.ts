import { DatePipe } from '@angular/common';
import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { Subscription, filter } from 'rxjs';
import { OutboxSummary, OutboxSyncService } from '../../core/services/outbox-sync.service';

@Component({
  selector: 'app-outbox-status', standalone: true, imports: [DatePipe],
  template: `
    <section class="outbox-status" aria-live="polite" aria-label="Estado de sincronización">
      <span>{{ summary.online ? 'Con conexión' : 'Sin conexión' }}</span>
      <span>Pendientes: {{ summary.pending }}</span>
      <span>Enviando: {{ summary.sending }}</span>
      <span>Sincronizadas: {{ summary.synchronized }}</span>
      <span>Rechazadas: {{ summary.rejected }}</span>
      <span>Reintento: {{ summary.retryable }}</span>
      @if (summary.lastSync) { <span>Última sincronización: {{ summary.lastSync | date:'short' }}</span> }
      @for (error of summary.errors; track error.operation_uuid) {
        <details><summary>{{ error.status }} · {{ error.operation_type }}</summary><p>{{ error.error_category }}: {{ error.error_message }}</p></details>
      }
    </section>
  `,
  styles: [`.outbox-status{display:flex;gap:.75rem;align-items:center;flex-wrap:wrap;padding:.5rem 1rem;font-size:.8rem;background:#f4f1ef;color:#342b31}.outbox-status details{width:100%}.outbox-status p{margin:.25rem 0}`]
})
export class OutboxStatusComponent implements OnInit, OnDestroy {
  private readonly sync = inject(OutboxSyncService);
  private readonly router = inject(Router);
  private readonly subscriptions = new Subscription();
  summary: OutboxSummary = { pending: 0, sending: 0, synchronized: 0, rejected: 0, retryable: 0, lastSync: null, online: navigator.onLine, errors: [] };

  ngOnInit(): void {
    this.subscriptions.add(this.sync.summary$.subscribe(value => this.summary = value));
    this.subscriptions.add(this.router.events.pipe(filter(event => event instanceof NavigationEnd)).subscribe(() => {
      void this.sync.refresh();
      void this.sync.syncPending();
    }));
  }
  ngOnDestroy(): void { this.subscriptions.unsubscribe(); }
}
