import { Component } from '@angular/core';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
@Component({ selector: 'app-loading-spinner', standalone: true, imports: [MatProgressSpinnerModule], template: '<div class="spinner"><mat-spinner diameter="36" /></div>', styles: ['.spinner{display:flex;justify-content:center;padding:2rem}'] })
export class LoadingSpinnerComponent {}
