import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import { Cart } from '../../../shared/models/cart.model';

@Injectable({ providedIn: 'root' })
export class CartService {
  constructor(private readonly api: ApiService) {}

  getCart(): Observable<Cart> {
    return this.api.get<Cart>('/api/cart');
  }

  addItem(id_variante: number, cantidad: number): Observable<Cart> {
    return this.api.post<Cart>('/api/cart/items', { id_variante, cantidad });
  }

  updateQuantity(id_detalle: number, cantidad: number): Observable<Cart> {
    return this.api.put<Cart>(`/api/cart/items/${id_detalle}`, { cantidad });
  }

  removeItem(id_detalle: number): Observable<Cart> {
    return this.api.delete<Cart>(`/api/cart/items/${id_detalle}`);
  }
}
