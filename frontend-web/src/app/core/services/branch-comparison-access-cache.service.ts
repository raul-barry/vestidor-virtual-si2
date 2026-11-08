import { Injectable } from '@angular/core';
import { TokenService } from './token.service';

@Injectable({ providedIn: 'root' })
export class BranchComparisonAccessCache {
  constructor(private readonly tokens: TokenService) {}

  read(): boolean | null {
    const key = this.key();
    if (!key) return null;
    const value = localStorage.getItem(key);
    return value === null ? null : value === 'true';
  }

  write(allowed: boolean): void {
    const key = this.key();
    if (key) localStorage.setItem(key, String(allowed));
  }

  private key(): string | null {
    const organizationId = this.tokens.getOrganizationId();
    const userId = this.tokens.getUserId();
    return organizationId && userId ? `fashionstore:branch-comparison:${organizationId}:${userId}` : null;
  }
}
