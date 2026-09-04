import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import { Usuario } from '../../../shared/models/usuario.model';

export interface ProfileUpdateRequest {
  nombres: string;
  apellidos: string;
  telefono: string;
}

@Injectable({ providedIn: 'root' })
export class ProfileService {
  constructor(private readonly api: ApiService) {}

  getProfile(): Observable<Usuario> {
    return this.api.get<Usuario>('/api/users/profile');
  }

  updateProfile(request: ProfileUpdateRequest): Observable<Usuario> {
    return this.api.put<Usuario>('/api/users/profile', request);
  }
}
