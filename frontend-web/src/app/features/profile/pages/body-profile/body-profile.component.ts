import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../../../core/services/api.service';

@Component({
  standalone: true,
  imports: [FormsModule, RouterLink],
  template: `
    <main class="page">
      <a routerLink="/profile/view">← Volver al perfil</a>
      <h1>Perfil corporal</h1>
      <p>Las dimensiones se registran en centímetros; el peso es opcional.</p>
      <label class="consent"><input type="checkbox" [(ngModel)]="data.consentimiento"> Autorizo el procesamiento de mis fotografías y medidas corporales para crear mi perfil y utilizar el vestidor virtual.</label>
      <fieldset [disabled]="!data.consentimiento">
        <label>Altura (cm)<input type="number" [(ngModel)]="data.altura_cm"></label>
        <label>Peso (kg)<input type="number" [(ngModel)]="data.peso_kg"></label>
        <label>Pecho (cm)<input type="number" [(ngModel)]="data.pecho_cm"></label>
        <label>Cintura (cm)<input type="number" [(ngModel)]="data.cintura_cm"></label>
        <label>Cadera (cm)<input type="number" [(ngModel)]="data.cadera_cm"></label>
        <label>Ancho de hombros (cm)<input type="number" [(ngModel)]="data.ancho_hombros_cm"></label>
        <label>Largo de pierna (cm)<input type="number" [(ngModel)]="data.largo_pierna_cm"></label>
      </fieldset>
      <section><h2>Fotografías privadas</h2>
        @for (p of positions; track p.key) {
          <label>{{p.label}}<input type="file" accept="image/jpeg,image/png,image/webp" [disabled]="!data.consentimiento" (change)="photo(p.key,$any($event.target).files?.[0])"></label>
          @if (previews[p.key]) { <img [src]="previews[p.key]" [alt]="p.label"><button (click)="deletePhoto(p.key)">Eliminar foto</button> }
        }
      </section>
      <div class="actions"><button (click)="save()" [disabled]="!data.consentimiento">Guardar perfil corporal</button><a routerLink="/experience/fitting" class="try-on-link">Probar mi perfil en el vestidor</a><button (click)="remove()" type="button">Eliminar perfil corporal</button></div>
      <p role="status">{{message}}</p>
    </main>`,
  styles: [`.page{max-width:700px;margin:auto;padding:2rem;display:grid;gap:1rem}fieldset{display:grid;grid-template-columns:repeat(2,1fr);gap:1rem}label{display:grid;gap:.3rem}.consent{padding:1rem;background:#eef5ef}img{max-width:160px}.actions{display:flex;gap:1rem;align-items:center;flex-wrap:wrap}.try-on-link{font-weight:600;color:var(--primary)}@media(max-width:600px){fieldset{grid-template-columns:1fr}}`]
})
export class BodyProfileComponent implements OnInit {
  private readonly api = inject(ApiService);
  data: any = { consentimiento: false, altura_cm: null, peso_kg: null, pecho_cm: null, cintura_cm: null, cadera_cm: null, ancho_hombros_cm: null, largo_pierna_cm: null };
  positions = [{ key: 'frontal', label: 'Foto frontal' }, { key: 'posterior', label: 'Foto posterior' }, { key: 'lateral_izquierda', label: 'Lateral izquierda' }, { key: 'lateral_derecha', label: 'Lateral derecha' }];
  previews: Record<string, string> = {};
  message = '';
  ngOnInit(): void { this.api.get<any>('/api/body-profile').subscribe({ next: value => this.data = value, error: () => undefined }); }
  photo(position: string, file: File): void { if (!file || !this.data.consentimiento) return; this.previews[position] = URL.createObjectURL(file); const form = new FormData(); form.append('file', file); this.api.put(`/api/body-profile/photos/${position}`, form).subscribe({ next: () => this.message = 'Fotografía privada guardada', error: error => this.message = error.error?.detail || 'No fue posible subir' }); }
  deletePhoto(position: string): void { this.api.delete(`/api/body-profile/photos/${position}`).subscribe({ next: () => { delete this.previews[position]; this.message = 'Fotografía eliminada'; } }); }
  save(): void { this.api.put('/api/body-profile', this.data).subscribe({ next: () => this.message = 'Perfil corporal guardado', error: error => this.message = error.error?.detail || 'No fue posible guardar' }); }
  remove(): void { if (!confirm('¿Eliminar medidas y fotografías corporales?')) return; this.api.delete('/api/body-profile').subscribe({ next: () => { this.data = { ...this.data, consentimiento: false }; this.previews = {}; this.message = 'Perfil corporal eliminado'; }, error: () => this.message = 'No fue posible eliminar' }); }
}
