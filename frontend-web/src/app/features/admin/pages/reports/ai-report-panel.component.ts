import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';
import { AiReportRequest, AiReportType, AiReportResponse, ReportBranch, ReportFeatures } from '../../models/report.model';
import { AdminReportService } from '../../services/admin-report.service';

interface SpeechRecognitionResultLike {
  readonly transcript: string;
}

interface SpeechRecognitionLike {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((event: { results: ArrayLike<ArrayLike<SpeechRecognitionResultLike>> }) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  start(): void;
}

interface SpeechWindow extends Window {
  SpeechRecognition?: new () => SpeechRecognitionLike;
  webkitSpeechRecognition?: new () => SpeechRecognitionLike;
}

@Component({
  selector: 'app-ai-report-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './ai-report-panel.component.html',
  styleUrl: './ai-report-panel.component.scss',
})
export class AiReportPanelComponent implements OnInit {
  private readonly reports = inject(AdminReportService);

  readonly reportTypes: Array<{ value: AiReportType; label: string }> = [
    { value: 'ventas', label: 'Ventas' },
    { value: 'productos', label: 'Productos y categorías' },
    { value: 'sucursales', label: 'Rendimiento de sucursales' },
    { value: 'inventario', label: 'Inventario y reservas' },
    { value: 'tendencias', label: 'Tendencias de ventas' },
  ];
  readonly today = new Date().toISOString().slice(0, 10);
  dateFrom = this.defaultStartDate();
  dateTo = this.today;
  selectedType: AiReportType = 'ventas';
  selectedBranch = '';
  question = '';
  branches: ReportBranch[] = [];
  features: ReportFeatures | null = null;
  result: AiReportResponse | null = null;
  isLoading = true;
  isGenerating = false;
  isListening = false;
  exportingFormat: 'pdf' | 'xlsx' | null = null;
  private lastRequest: AiReportRequest | null = null;
  error = '';

  ngOnInit(): void {
    forkJoin({ features: this.reports.getFeatures(), branches: this.reports.getBranches() })
      .subscribe({
        next: ({ features, branches }) => {
          this.features = features;
          this.branches = branches;
          this.isLoading = false;
        },
        error: (error: { error?: { detail?: unknown } }) => {
          this.isLoading = false;
          this.error = this.messageFrom(error, 'No fue posible cargar las capacidades de reportes.');
        },
      });
  }

  generate(channel: 'texto' | 'voz' = 'texto'): void {
    if (this.isGenerating || !this.features?.reportes_ia) return;
    if (channel === 'voz' && !this.features.reportes_voz) {
      this.error = 'Los reportes por voz no están incluidos en el plan actual.';
      return;
    }
    if (this.selectedType === 'sucursales' && !this.features.comparacion_sucursales) {
      this.error = 'La comparación de sucursales no está incluida en el plan actual.';
      return;
    }
    this.error = '';
    this.isGenerating = true;
    this.result = null;
    const request: AiReportRequest = {
      tipo: this.selectedType,
      fecha_inicio: this.dateFrom || undefined,
      fecha_fin: this.dateTo || undefined,
      id_sucursal: this.selectedBranch ? Number(this.selectedBranch) : undefined,
      consulta: this.question.trim(),
      canal: channel,
    };
    this.lastRequest = request;
    this.reports.generateAiReport(request).subscribe({
      next: (result) => {
        this.result = result;
        this.isGenerating = false;
      },
      error: (error: { error?: { detail?: unknown } }) => {
        this.error = this.messageFrom(error, 'No fue posible generar el reporte.');
        this.isGenerating = false;
      },
    });
  }

  exportReport(format: 'pdf' | 'xlsx'): void {
    if (!this.lastRequest || !this.result || this.exportingFormat
      || !this.features?.exportacion_pdf_excel) return;
    this.error = '';
    this.exportingFormat = format;
    this.reports.exportAiReport(this.lastRequest, format).subscribe({
      next: (file) => {
        const url = URL.createObjectURL(file);
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = `fashionstore-${this.lastRequest?.tipo}-${this.result?.periodo.desde}-${this.result?.periodo.hasta}.${format}`;
        anchor.click();
        window.setTimeout(() => URL.revokeObjectURL(url), 1000);
        this.exportingFormat = null;
      },
      error: () => {
        this.error = `No fue posible generar el archivo ${format.toUpperCase()}. Intenta nuevamente.`;
        this.exportingFormat = null;
      },
    });
  }

  startVoiceReport(): void {
    if (!this.features?.reportes_voz || this.isGenerating || this.isListening) return;
    const speechWindow = window as SpeechWindow;
    const Recognition = speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition;
    if (!Recognition) {
      this.error = 'Este navegador no ofrece reconocimiento de voz. Puedes escribir la consulta.';
      return;
    }
    const recognition = new Recognition();
    recognition.lang = 'es-BO';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    this.error = '';
    this.isListening = true;
    recognition.onresult = (event) => {
      const transcript = event.results[0]?.[0]?.transcript?.trim();
      if (!transcript) {
        this.error = 'No se reconoció una consulta. Intenta nuevamente.';
        return;
      }
      this.question = transcript;
      this.generate('voz');
    };
    recognition.onerror = (event) => {
      this.error = event.error === 'not-allowed'
        ? 'El navegador no autorizó el micrófono.'
        : 'No fue posible reconocer la consulta de voz.';
      this.isListening = false;
    };
    recognition.onend = () => { this.isListening = false; };
    try {
      recognition.start();
    } catch {
      this.isListening = false;
      this.error = 'No fue posible iniciar el micrófono.';
    }
  }

  speakResult(): void {
    if (!this.result || !('speechSynthesis' in window)) return;
    const speech = new SpeechSynthesisUtterance([
      ...this.result.observaciones_ia,
      ...this.result.recomendaciones_ia,
    ].join('. '));
    speech.lang = 'es-BO';
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(speech);
  }

  private defaultStartDate(): string {
    const start = new Date();
    start.setDate(start.getDate() - 29);
    return start.toISOString().slice(0, 10);
  }

  private messageFrom(error: { error?: { detail?: unknown } }, fallback: string): string {
    const detail = error.error?.detail;
    return typeof detail === 'string' ? detail : fallback;
  }
}
