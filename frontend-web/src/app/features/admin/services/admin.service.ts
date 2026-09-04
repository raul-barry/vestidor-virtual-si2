import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';

export interface DashboardStats {
  usuarios: number;
  productos: number;
  pedidos: number;
  ventas: number;
}

@Injectable({ providedIn: 'root' })
export class AdminService {
  getDashboardStats(): Observable<DashboardStats> {
    return of({ usuarios: 0, productos: 0, pedidos: 0, ventas: 0 });
  }
}
