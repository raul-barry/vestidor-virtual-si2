import { Component } from '@angular/core';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

@Component({
  selector: 'app-loading-spinner',
  standalone: true,
  imports: [MatProgressSpinnerModule],
  template: `<mat-progress-spinner mode="indeterminate"></mat-progress-spinner>`
})
export class LoadingSpinnerComponent {}