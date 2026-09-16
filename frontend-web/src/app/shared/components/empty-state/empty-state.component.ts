import { Component, Input } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-empty-state',
  standalone: true,
  imports: [MatIconModule],
  template: `<mat-icon>sentiment_dissatisfied</mat-icon><p>{{message||'Sin datos'}}</p>`
})
export class EmptyStateComponent {
  @Input() message = '';
}