import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CurrencyPipe, DatePipe } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { Order } from '../../../../shared/models/order.model';

@Component({
  selector: 'app-order-card',
  standalone: true,
  imports: [CurrencyPipe, DatePipe, MatButtonModule, MatCardModule],
  templateUrl: './order-card.component.html',
  styleUrl: './order-card.component.scss'
})
export class OrderCardComponent {
  @Input({ required: true }) order!: Order;
  @Output() readonly viewDetail = new EventEmitter<number>();
}
