import { Component, inject } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { TokenService } from '../../../core/services/token.service';

@Component({
  standalone: true, imports: [CommonModule, DatePipe, RouterLink],
  template: `<main><p class="eyebrow">CUENTA Y ACCESO</p><h1>Seguridad</h1>
    <section><h2>Sesión actual</h2><dl><dt>Rol</dt><dd>{{role || 'No disponible'}}</dd><dt>Organización</dt><dd>{{role === 'ADMINISTRADOR_PLATAFORMA' ? 'Cuenta global de plataforma' : organizationId ?? 'No disponible'}}</dd><dt>Usuario</dt><dd>{{userId ?? 'No disponible'}}</dd><dt>Vencimiento del token</dt><dd>{{expiresAt ? (expiresAt | date:'medium') : 'No disponible'}}</dd></dl><p>La página muestra datos declarados en la sesión local. No reemplaza la validación del servidor.</p></section>
    @if(role === 'ADMINISTRADOR'){<section><h2>Controles disponibles</h2><p>Gestiona los usuarios y sus roles empresariales en tu organización.</p><a routerLink="/admin/users">Administrar usuarios</a><p>Consulta la actividad registrada de tu organización.</p><a routerLink="/admin/audit">Ver bitácora</a></section>}
    @else if(role === 'ADMINISTRADOR_PLATAFORMA'){<section><h2>Administración global</h2><p>La plataforma no expone una consola global de sesiones o eventos de seguridad. Las funciones de roles, organizaciones y suscripciones están disponibles aquí:</p><a routerLink="/platform/roles">Roles y permisos</a> · <a routerLink="/platform/organizations">Organizaciones</a></section>}
    @else {<section><h2>Permisos</h2><p>Tu rol no tiene acceso a administración de usuarios ni a registros de auditoría empresarial.</p></section>}
  </main>`,
  styles: [`main{max-width:900px;margin:auto;padding:2rem;color:var(--ink)}section{padding:1.25rem;margin:1rem 0;border:1px solid var(--border);border-radius:14px;background:var(--surface)}dl{display:grid;grid-template-columns:220px 1fr;gap:.5rem}dt{font-weight:700}.eyebrow{font-size:.75rem;letter-spacing:.14em;color:var(--primary);font-weight:700}`]
})
export class SecurityOverviewComponent {
  private readonly tokens = inject(TokenService);
  private readonly claims = this.tokens.getClaims();
  readonly role = this.tokens.getRole();
  readonly organizationId = this.tokens.getOrganizationId();
  readonly userId = this.tokens.getUserId();
  readonly expiresAt = typeof this.claims?.['exp'] === 'number' ? new Date(Number(this.claims['exp']) * 1000) : null;
}
