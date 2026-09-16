import { Component } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-error-message',
  standalone: true,
  imports: [MatIconModule],
  template: `<mat-icon color="error">error_outline</mat-icon><p>{{message||'Error'}}</p>`
})
export class ErrorMessageComponent {
  message = '';
}