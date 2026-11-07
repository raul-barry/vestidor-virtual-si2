import { Injectable } from '@angular/core';

const TOKEN_KEY = 'vestidor_virtual_token';

@Injectable({ providedIn: 'root' })
export class TokenService {
  setToken(token: string): void {
    localStorage.setItem(TOKEN_KEY, token);
  }

  getToken(): string | null {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token || this.isExpired(token)) {
      if (token) this.clearToken();
      return null;
    }
    return token;
  }

  clearToken(): void {
    localStorage.removeItem(TOKEN_KEY);
  }

  hasToken(): boolean {
    return this.getToken() !== null;
  }

  getClaims(): Record<string, unknown> | null {
    const token = this.getToken();
    if (!token) return null;
    try {
      const encodedPayload = token.split('.')[1];
      if (!encodedPayload) return null;
      const payload = encodedPayload.replace(/-/g, '+').replace(/_/g, '/').padEnd(Math.ceil(encodedPayload.length / 4) * 4, '=');
      return JSON.parse(atob(payload)) as Record<string, unknown>;
    } catch {
      return null;
    }
  }

  getOrganizationId(): number | null {
    const value = this.getClaims()?.['id_organizacion'];
    return typeof value === 'number' && Number.isInteger(value) && value > 0 ? value : null;
  }

  getUserId(): number | null {
    const value = this.getClaims()?.['id_usuario'];
    return typeof value === 'number' && Number.isInteger(value) && value > 0 ? value : null;
  }

  getRole(): string | null {
    const value = this.getClaims()?.['rol'];
    return typeof value === 'string' ? value : null;
  }

  private isExpired(token: string): boolean {
    try {
      const encodedPayload = token.split('.')[1];
      if (!encodedPayload) return true;
      const payload = JSON.parse(atob(encodedPayload.replace(/-/g, '+').replace(/_/g, '/').padEnd(Math.ceil(encodedPayload.length / 4) * 4, '=')));
      return typeof payload.exp === 'number' && payload.exp <= Math.floor(Date.now() / 1000);
    } catch {
      return true;
    }
  }
}
