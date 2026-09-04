import { Component, Input } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { DisponibilidadSucursal } from '../../../../shared/models/producto.model';

@Component({
  selector: 'app-availability-list',
  standalone: true,
  imports: [MatCardModule],
  templateUrl: './availability-list.component.html',
  styleUrl: './availability-list.component.scss'
})
export class AvailabilityListComponent {
  @Input({ required: true }) availability: DisponibilidadSucursal[] = [];
}
