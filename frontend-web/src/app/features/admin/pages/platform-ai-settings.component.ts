import { CommonModule, DatePipe } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DEFAULT_PLATFORM_AI_CAPABILITIES, PLATFORM_AI_CAPABILITIES, PlatformAIConfig, PlatformAIModel } from '../models/platform-ai.model';
import { PlatformAIService } from '../services/platform-ai.service';

@Component({
  standalone: true,
  imports: [CommonModule, FormsModule, DatePipe],
  template: `
    <main class="ai-page">
      <p class="eyebrow">ADMINISTRACIÓN SaaS</p>
      <h1>Inteligencia artificial</h1>
      <p class="intro">Configuración global de Groq. La clave solo se envía al backend y nunca se devuelve al navegador.</p>
      @if (loading) { <p role="status">Cargando configuración…</p> }
      @else {
        <section class="panel">
          <h2>Proveedor Groq</h2>
          @if (config?.configured) { <p class="configured">Clave configurada: <code>{{config?.masked_api_key}}</code></p> }
          @else { <p class="notice">Aún no hay una API Key guardada.</p> }
          <label>API Key de Groq
            <input type="password" autocomplete="new-password" [(ngModel)]="apiKey" placeholder="Pega una clave nueva para guardarla o probarla" />
          </label>
          <p class="hint">La clave temporal permanece solo en memoria mientras esta pantalla está abierta. Si el backend tiene GROQ_API_KEY configurada, puedes dejar este campo vacío. Para guardar una clave cifrada en PostgreSQL también debe estar configurada AI_CONFIG_ENCRYPTION_KEY.</p>
          <div class="actions">
            <button type="button" [disabled]="busy" (click)="loadModels()">{{loadingModels ? 'Consultando…' : 'Consultar modelos disponibles'}}</button>
            <button type="button" class="secondary" [disabled]="busy || !primaryModel" (click)="testConnection()">Probar conexión</button>
          </div>
          <div class="model-grid">
            <label>Modelo principal
              <select [(ngModel)]="primaryModel"><option value="">Selecciona un modelo</option>@for (model of textModels; track model.id) { <option [value]="model.id">{{model.id}}</option> }</select>
            </label>
            <label>Modelo rápido
              <select [(ngModel)]="fastModel"><option value="">Selecciona un modelo</option>@for (model of textModels; track model.id) { <option [value]="model.id">{{model.id}}</option> }</select>
            </label>
            <label>Modelo de visión <span class="experimental">Experimental</span>
              <select [(ngModel)]="visionModel"><option value="">Selecciona un modelo</option>@for (model of visionModels; track model.id) { <option [value]="model.id">{{model.id}}{{model.experimental ? ' · Experimental' : ''}}</option> }</select>
            </label>
            <label>Modelo de transcripción
              <select [(ngModel)]="transcriptionModel"><option value="">Selecciona un modelo</option>@for (model of transcriptionModels; track model.id) { <option [value]="model.id">{{model.id}}</option> }</select>
            </label>
          </div>
          <p class="hint">Los modelos experimentales no se eligen automáticamente para solicitudes de producción.</p>
          <section class="assignments" aria-label="Asignación de modelos">
            <div class="section-heading"><div><h3>Asignación de modelos</h3><p class="hint">Cada capacidad se valida con el tipo de entrada compatible.</p></div>
              <button type="button" class="secondary" [disabled]="busy" (click)="restoreDefaults()">Restaurar valores predeterminados</button></div>
            @for (capability of capabilities; track capability.key) {
              <div class="assignment-row">
                <div><strong>{{capability.label}}</strong><small>{{capability.key}} · {{capability.type === 'text' ? 'Texto' : capability.type === 'vision' ? 'Visión' : 'Transcripción'}}</small></div>
                <select [attr.aria-label]="'Modelo para ' + capability.label" [(ngModel)]="capabilityModels[capability.key]">
                  <option value="">Selecciona un modelo</option>
                  @for (model of modelsFor(capability.type); track model.id) {
                    <option [value]="model.id">{{model.id}}{{model.experimental ? ' · Experimental (preview)' : ''}}</option>
                  }
                </select>
                <button type="button" class="secondary" [disabled]="busy || !capabilityModels[capability.key]" (click)="testCapability(capability.key)">
                  {{testingCapability === capability.key ? 'Probando…' : 'Probar modelo'}}
                </button>
                @if (models.length && !isAvailable(capabilityModels[capability.key])) { <small class="unavailable">Modelo no disponible en el catálogo actual</small> }
                @if (capabilityTestStatus[capability.key]) { <small role="status">{{capabilityTestStatus[capability.key]}}</small> }
              </div>
            }
          </section>
          <div class="actions"><button type="button" [disabled]="busy || !models.length" (click)="save()">{{saving ? 'Guardando…' : 'Guardar configuración'}}</button></div>
          @if (message) { <p class="success" role="status">{{message}}</p> }
          @if (error) { <p class="error" role="alert">{{error}}</p> }
        </section>
        <section class="panel status">
          <h2>Estado</h2>
          <p>Configuración: <strong>{{config?.configured ? 'Clave guardada' : 'Sin configurar'}}</strong></p>
          <p>Última prueba: <strong>{{config?.last_test_status || 'Sin probar'}}</strong>
            @if (config?.last_test_at) { · {{config?.last_test_at | date:'medium'}} }</p>
        </section>
        <section class="panel capabilities">
          <h2>Integraciones actuales</h2>
          <ul>
            <li>Reportes y recomendaciones: Groq usa métricas calculadas por el backend.</li>
            <li>Probador virtual: Gemini se conserva porque Groq no sustituye la generación/edición de imágenes.</li>
            <li>Entrada y salida de voz de reportes: reconocimiento y síntesis del navegador; no se envía audio a Groq.</li>
            <li>Los modelos de visión y transcripción quedan disponibles como configuración experimental; no se conectan a flujos existentes hasta tener un caso compatible.</li>
          </ul>
        </section>
      }
    </main>
  `,
  styles: [`
    .ai-page{max-width:980px;margin:auto;padding:2rem;color:var(--ink)}.eyebrow{font-size:.75rem;letter-spacing:.14em;color:var(--primary);font-weight:700}.intro,.hint{color:var(--muted)}
    .panel{padding:1.4rem;margin:1rem 0;border:1px solid var(--border);border-radius:16px;background:var(--surface)}h2{margin-top:0}label{display:grid;gap:.45rem;font-weight:600;margin:1rem 0}input,select{font:inherit;padding:.8rem;border:1px solid var(--border);border-radius:9px;background:var(--surface);color:var(--ink)}
    .model-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.4rem 1rem}.actions{display:flex;gap:.75rem;flex-wrap:wrap;margin:1rem 0}button{border:0;border-radius:9px;padding:.75rem 1rem;background:var(--primary);color:white;font:inherit;cursor:pointer}button.secondary{background:var(--ink)}button:disabled{opacity:.55;cursor:not-allowed}.experimental{color:#9a5700;font-size:.8rem}.success{color:#116d4d}.error{color:#a32626}.notice{color:#775300}.configured code{letter-spacing:.08em}.assignments{margin-top:1.6rem;border-top:1px solid var(--border);padding-top:1rem}.section-heading,.assignment-row{display:flex;align-items:center;gap:1rem;justify-content:space-between}.section-heading{flex-wrap:wrap}.assignment-row{padding:.7rem 0;border-bottom:1px solid var(--border)}.assignment-row>div{display:grid;gap:.2rem;min-width:190px}.assignment-row small{color:var(--muted)}.assignment-row select{flex:1;min-width:170px}
    @media(max-width:650px){.model-grid{grid-template-columns:1fr}.ai-page{padding:1rem}}
  `],
})
export class PlatformAISettingsComponent implements OnInit {
  private readonly service = inject(PlatformAIService);
  loading = true;
  loadingModels = false;
  saving = false;
  busy = false;
  config: PlatformAIConfig | null = null;
  models: PlatformAIModel[] = [];
  apiKey = '';
  primaryModel = '';
  fastModel = '';
  visionModel = '';
  transcriptionModel = '';
  capabilityModels: Record<string, string> = { ...DEFAULT_PLATFORM_AI_CAPABILITIES };
  readonly capabilities = PLATFORM_AI_CAPABILITIES;
  capabilityTestStatus: Record<string, string> = {};
  testingCapability = '';
  message = '';
  error = '';
  get textModels(): PlatformAIModel[] { return this.models.filter(model => model.capabilities.includes('text')); }
  get visionModels(): PlatformAIModel[] { return this.models.filter(model => model.capabilities.includes('vision')); }
  get transcriptionModels(): PlatformAIModel[] { return this.models.filter(model => model.capabilities.includes('transcription')); }
  modelsFor(type: string): PlatformAIModel[] { return this.models.filter(model => model.capabilities.includes(type)); }
  isAvailable(modelId: string): boolean { return this.models.some(model => model.id === modelId && model.active); }

  ngOnInit(): void {
    this.service.getConfig().subscribe({
      next: config => {
        this.config = config;
        this.primaryModel = config.primary_model;
        this.fastModel = config.fast_model;
        this.visionModel = config.vision_model;
        this.transcriptionModel = config.transcription_model;
        this.capabilityModels = { ...DEFAULT_PLATFORM_AI_CAPABILITIES, ...(config.capability_models ?? {}) };
        this.loading = false;
        if (config.configured) this.loadModels();
      },
      error: () => { this.loading = false; this.error = 'No fue posible cargar la configuración de IA.'; },
    });
  }

  loadModels(): void {
    this.busy = this.loadingModels = true;
    this.error = '';
    this.service.listModels(this.apiKey.trim() || undefined).subscribe({
      next: models => { this.models = models.filter(model => model.active); this.busy = this.loadingModels = false; },
      error: error => { this.busy = this.loadingModels = false; this.error = this.detail(error, 'No fue posible consultar los modelos de Groq.'); },
    });
  }

  testConnection(): void {
    this.busy = true;
    this.error = this.message = '';
    this.service.test(this.apiKey.trim() || undefined, this.primaryModel, 'complex_reasoning').subscribe({
      next: result => { this.config = this.config ? { ...this.config, last_test_status: 'EXITOSO', last_test_at: result.tested_at } : this.config; this.busy = false; this.message = result.message; },
      error: error => { this.busy = false; this.error = this.detail(error, 'La prueba de conexión con Groq falló.'); this.refreshStatus(); },
    });
  }

  testCapability(capability: string): void {
    this.busy = true;
    this.testingCapability = capability;
    this.error = '';
    this.service.test(this.apiKey.trim() || undefined, this.capabilityModels[capability], capability).subscribe({
      next: result => { this.capabilityTestStatus[capability] = `Disponible · ${new Date(result.tested_at).toLocaleTimeString()}`; this.busy = false; this.testingCapability = ''; },
      error: error => { this.capabilityTestStatus[capability] = 'Error de prueba'; this.busy = false; this.testingCapability = ''; this.error = this.detail(error, 'La prueba del modelo falló.'); },
    });
  }

  restoreDefaults(): void {
    this.primaryModel = 'openai/gpt-oss-120b';
    this.fastModel = 'openai/gpt-oss-20b';
    this.visionModel = 'qwen/qwen3.8-27b';
    this.transcriptionModel = 'whisper-large-v3-turbo';
    this.capabilityModels = { ...DEFAULT_PLATFORM_AI_CAPABILITIES };
    this.capabilityTestStatus = {};
    this.save();
  }

  save(): void {
    this.busy = this.saving = true;
    this.error = this.message = '';
    this.service.save({
      ...(this.apiKey.trim() ? { api_key: this.apiKey.trim() } : {}),
      primary_model: this.primaryModel, fast_model: this.fastModel,
      vision_model: this.visionModel, transcription_model: this.transcriptionModel,
      capability_models: { ...this.capabilityModels },
    }).subscribe({
      next: config => { this.config = config; this.apiKey = ''; this.busy = this.saving = false; this.message = 'Configuración guardada de forma segura.'; },
      error: error => { this.busy = this.saving = false; this.error = this.detail(error, 'No fue posible guardar la configuración.'); },
    });
  }

  private refreshStatus(): void { this.service.getConfig().subscribe(config => this.config = config); }
  private detail(error: { error?: { detail?: unknown } }, fallback: string): string {
    return typeof error.error?.detail === 'string' ? error.error.detail : fallback;
  }
}
