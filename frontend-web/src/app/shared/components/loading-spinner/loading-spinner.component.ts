import { Component } from '@angular/core';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
@Component({selector: 'app-loading-spinner', standalone: true, imports: [MatProgressSpinnerModule], template: '<div class="state-panel" role="status"><mat-spinner diameter="36" aria-label="Cargando"/><p>Cargando información…</p></div>'})
export class LoadingSpinnerComponent {}
