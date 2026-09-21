import { Component, Input } from '@angular/core';
@Component({selector: 'app-empty-state', standalone: true, template: '<div class="state-panel" role="status"><p>{{ message }}</p></div>'})
export class EmptyStateComponent { @Input() message = 'No hay datos disponibles.'; }
