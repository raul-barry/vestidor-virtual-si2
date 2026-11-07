import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { PlatformAIService } from '../services/platform-ai.service';
import { PlatformAISettingsComponent } from './platform-ai-settings.component';

describe('PlatformAISettingsComponent', () => {
  let fixture: ComponentFixture<PlatformAISettingsComponent>;
  let service: jasmine.SpyObj<PlatformAIService>;
  const config = {
    configured: true, masked_api_key: '••••1234', primary_model: 'main', fast_model: 'fast',
    vision_model: 'vision', transcription_model: 'whisper', experimental_models: ['vision'], capability_models: {},
    last_test_status: null, last_test_at: null,
  };
  beforeEach(async () => {
    service = jasmine.createSpyObj<PlatformAIService>('PlatformAIService', ['getConfig', 'listModels', 'save', 'test']);
    service.getConfig.and.returnValue(of(config));
    service.listModels.and.returnValue(of([
      { id: 'main', active: true, experimental: false, capabilities: ['text'] }, { id: 'fast', active: true, experimental: false, capabilities: ['text'] },
      { id: 'vision', active: true, experimental: true, capabilities: ['text', 'vision'] }, { id: 'whisper', active: true, experimental: false, capabilities: ['transcription'] },
    ]));
    service.save.and.returnValue(of(config));
    service.test.and.returnValue(of({ ok: true, message: 'Conexión verificada', tested_at: '2026-11-06T10:00:00Z' }));
    await TestBed.configureTestingModule({ imports: [PlatformAISettingsComponent], providers: [{ provide: PlatformAIService, useValue: service }] }).compileComponents();
  });

  it('shows masked config, editable model selectors and known provider boundaries', () => {
    fixture = TestBed.createComponent(PlatformAISettingsComponent);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Inteligencia artificial');
    expect(fixture.nativeElement.textContent).toContain('••••1234');
    expect(fixture.nativeElement.textContent).toContain('Experimental');
    expect(fixture.nativeElement.textContent).toContain('Gemini se conserva');
    expect(service.listModels).toHaveBeenCalled();
  });

  it('clears the API key from component memory after save', () => {
    fixture = TestBed.createComponent(PlatformAISettingsComponent);
    fixture.detectChanges();
    fixture.componentInstance.apiKey = 'gsk-temp';
    fixture.componentInstance.save();
    expect(service.save).toHaveBeenCalledWith(jasmine.objectContaining({ api_key: 'gsk-temp' }));
    expect(fixture.componentInstance.apiKey).toBe('');
  });

  it('shows the eight configurable capabilities and restores default assignments', () => {
    fixture = TestBed.createComponent(PlatformAISettingsComponent);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Asignación de modelos');
    expect(fixture.nativeElement.textContent).toContain('Asistente UML');
    fixture.componentInstance.capabilityModels['general_chat'] = 'custom';
    fixture.componentInstance.restoreDefaults();
    expect(fixture.componentInstance.capabilityModels['general_chat']).toBe('openai/gpt-oss-20b');
  });
});
