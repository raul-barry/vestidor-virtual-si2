import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { PlatformAIService } from './platform-ai.service';

describe('PlatformAIService', () => {
  let service: PlatformAIService;
  let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(PlatformAIService);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('loads the safe public configuration and model catalog through the backend', () => {
    service.getConfig().subscribe();
    const config = http.expectOne('http://localhost:8000/api/platform/ai/config');
    expect(config.request.method).toBe('GET'); config.flush({ configured: false });
    service.listModels('draft-secret').subscribe();
    const models = http.expectOne('http://localhost:8000/api/platform/ai/models');
    expect(models.request.method).toBe('POST');
    expect(models.request.body).toEqual({ api_key: 'draft-secret' });
    models.flush([{ id: 'model-1', active: true, experimental: false, capabilities: ['text'] }]);
  });

  it('saves and tests the configuration only through platform API routes', () => {
    service.save({ api_key: 'draft-secret', primary_model: 'model-1', fast_model: 'model-2', vision_model: 'model-3', transcription_model: 'model-4' }).subscribe();
    const save = http.expectOne('http://localhost:8000/api/platform/ai/config');
    expect(save.request.method).toBe('PUT');
    expect(save.request.body.api_key).toBe('draft-secret');
    save.flush({ configured: true, masked_api_key: '••••1234' });
    service.test(undefined, 'model-1').subscribe();
    const test = http.expectOne('http://localhost:8000/api/platform/ai/test');
    expect(test.request.body).toEqual({ model: 'model-1' });
    test.flush({ ok: true, message: 'ok', tested_at: '2026-11-06T10:00:00Z' });
  });
});
