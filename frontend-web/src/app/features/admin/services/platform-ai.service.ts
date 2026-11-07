import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import { PlatformAIConfig, PlatformAIConfigUpdate, PlatformAIModel } from '../models/platform-ai.model';

@Injectable({ providedIn: 'root' })
export class PlatformAIService {
  private readonly base = '/api/platform/ai';
  constructor(private readonly api: ApiService) {}

  getConfig(): Observable<PlatformAIConfig> { return this.api.get(`${this.base}/config`); }
  listModels(api_key?: string): Observable<PlatformAIModel[]> {
    return this.api.post(`${this.base}/models`, api_key ? { api_key } : {});
  }
  save(config: PlatformAIConfigUpdate): Observable<PlatformAIConfig> {
    return this.api.put(`${this.base}/config`, config);
  }
  test(api_key?: string, model?: string, capability?: string): Observable<{ ok: boolean; message: string; tested_at: string }> {
    return this.api.post(`${this.base}/test`, { ...(api_key ? { api_key } : {}), ...(model ? { model } : {}), ...(capability ? { capability } : {}) });
  }
}
