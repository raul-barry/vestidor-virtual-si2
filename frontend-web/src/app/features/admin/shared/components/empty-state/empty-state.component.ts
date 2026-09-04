import { Component, Input } from '@angular/core';
@Component({ selector: 'app-empty-state', standalone: true, template: '<p class="empty">{{ message }}</p>', styles: ['.empty{color:#64748b;padding:2rem;text-align:center}'] })
export class EmptyStateComponent { @Input() message = 'No hay datos disponibles.'; }
