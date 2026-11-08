import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../../core/services/api.service';
import { loyaltyErrorMessage } from '../../../loyalty/loyalty-error-message';

@Component({
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `<main class="loyalty"><header><div><p class="eyebrow">RELACIÓN CON CLIENTES</p><h1>Fidelización</h1><p>Configura las reglas de puntos de esta organización y consulta su actividad.</p></div><button (click)="load()" [disabled]="busy">Actualizar</button></header>
    @if(error){<p class="error" role="alert">{{error}}</p>} @if(message){<p class="notice" role="status">{{message}}</p>}
    @if(busy && !program){<p>Cargando programa…</p>} @else {
      <section class="card"><h2>Programa por empresa</h2><label class="switch"><input type="checkbox" [(ngModel)]="form.active"> Programa activo</label>
        <label>Nombre<input [(ngModel)]="form.name" maxlength="120"></label><div class="grid">
          <label>Puntos por Bs<input type="number" min="0.0001" step="0.1" [(ngModel)]="form.points_per_currency"></label>
          <label>Valor de cada punto (Bs)<input type="number" min="0.0001" step="0.01" [(ngModel)]="form.currency_per_point"></label>
          <label>Mínimo para canjear<input type="number" min="0" [(ngModel)]="form.minimum_redeem_points"></label>
          <label>Descuento máximo (%)<input type="number" min="0" max="100" [(ngModel)]="form.max_discount_percent"></label>
          <label>Vencimiento (días; vacío = no vence)<input type="number" min="1" [(ngModel)]="form.expiration_days"></label>
        </div><button class="primary" (click)="save()" [disabled]="busy">Guardar programa</button>
      </section>
      <section class="card"><h2>Niveles</h2><p class="muted">Los niveles se determinan por el saldo actual de puntos.</p>@for(t of tiers;track t.code;let i=$index){<div class="tier"><label>Código<input [(ngModel)]="t.code"></label><label>Nombre<input [(ngModel)]="t.name"></label><label>Puntos mínimos<input type="number" min="0" [(ngModel)]="t.minimum_points"></label><button (click)="tiers.splice(i,1)">Quitar</button></div>}<button (click)="tiers.push({code:'NUEVO',name:'Nuevo nivel',minimum_points:0})">Añadir nivel</button><button class="primary" (click)="saveTiers()" [disabled]="busy">Guardar niveles</button></section>
      <section class="metrics"><article><span>Clientes inscritos</span><strong>{{summary?.metrics?.customers ?? 0}}</strong></article><article><span>Puntos acumulados (últimos 500 movimientos)</span><strong>{{summary?.metrics?.earned ?? 0}}</strong></article><article><span>Puntos canjeados</span><strong>{{summary?.metrics?.redeemed ?? 0}}</strong></article><article><span>Puntos vencidos</span><strong>{{summary?.metrics?.expired ?? 0}}</strong></article></section>
      <section class="card"><h2>Clientes y saldos</h2><div class="scroll"><table><thead><tr><th>Cliente</th><th>Correo</th><th>Saldo</th><th>Acumulados</th><th>Canjeados</th></tr></thead><tbody>@for(c of summary?.customers ?? [];track c.customer_id){<tr><td>{{c.name}}</td><td>{{c.email}}</td><td>{{c.balance}}</td><td>{{c.earned_total}}</td><td>{{c.redeemed_total}}</td></tr>}</tbody></table></div>
      <h2>Movimientos recientes</h2><div class="scroll"><table><thead><tr><th>Fecha</th><th>Cliente</th><th>Pedido</th><th>Tipo</th><th>Puntos</th><th>Monto Bs</th></tr></thead><tbody>@for(x of summary?.ledger ?? [];track x.id){<tr><td>{{x.created_at | date:'short'}}</td><td>{{customerName(x.account_id)}}</td><td>{{x.order_id ?? '—'}}</td><td>{{x.kind}}</td><td>{{x.points}}</td><td>{{x.amount}}</td></tr>}</tbody></table></div></section>
    }</main>`,
  styles: [`:host{display:block;background:#f5f4ef;min-height:100vh;color:#183b32}.loyalty{max-width:1120px;margin:auto;padding:clamp(1rem,4vw,3rem)}header{display:flex;justify-content:space-between;align-items:center;gap:1rem;margin-bottom:1.5rem}.eyebrow{letter-spacing:.12em;color:#64766f;font-size:.75rem;font-weight:700}h1{font-size:2rem;margin:.25rem 0}h2{margin-top:0}button{border:1px solid #cbd7d1;border-radius:9px;padding:.7rem 1rem;background:white;color:#174b3d;cursor:pointer}button.primary{background:#007e6f;color:white;border-color:#007e6f;margin-top:1rem}.card{background:white;border:1px solid #dae3de;border-radius:16px;padding:1.25rem;margin:1rem 0;box-shadow:0 5px 20px #173c3210}.card>label,.grid label,.tier label{display:grid;gap:.35rem;color:#45554e}.switch{display:flex!important;align-items:center;margin:.75rem 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:1rem;margin-top:1rem}input{padding:.65rem;border:1px solid #cbd7d1;border-radius:8px;font:inherit}.tier{display:grid;grid-template-columns:1fr 1fr 1fr auto;align-items:end;gap:.75rem;margin:.75rem 0}.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:.75rem}.metrics article{display:grid;gap:.4rem;background:#e7f1eb;border-radius:13px;padding:1rem}.metrics strong{font-size:1.6rem}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;min-width:600px}th,td{text-align:left;border-bottom:1px solid #e5ebe7;padding:.65rem}.error{color:#a22;background:#fff0ef;padding:.75rem}.notice{background:#e7f1eb;padding:.75rem}.muted{color:#64766f}@media(max-width:620px){header{align-items:flex-start;flex-direction:column}.tier{grid-template-columns:1fr 1fr}.loyalty{padding:1rem}}`]
})
export class LoyaltyAdminComponent implements OnInit {
  private readonly api = inject(ApiService);
  busy = false; error = ''; message = ''; program: any = null; summary: any = null;
  form: any = {active:false,name:'FashionStore Rewards',points_per_currency:1,currency_per_point:0.01,minimum_redeem_points:100,max_discount_percent:20,expiration_days:null};
  tiers: any[] = [];
  ngOnInit(): void { this.load(); }
  load(): void {
    this.busy=true;this.error='';
    this.api.get<any>('/api/loyalty/program').subscribe({next:r=>{this.program=r.program;this.tiers=r.tiers??[];if(r.program)this.form={...r.program};this.api.get<any>('/api/loyalty/admin/summary').subscribe({next:s=>{this.summary=s;this.busy=false;},error:e=>{this.fail(e, 'No se pudo cargar el resumen de fidelizaci\u00f3n.');}});},error:e=>this.fail(e, 'No se pudo cargar la configuraci\u00f3n del programa de fidelizaci\u00f3n.')});
  }
  save(): void {this.busy=true;this.error='';this.api.put<any>('/api/loyalty/program',{...this.form,expiration_days:this.form.expiration_days||null}).subscribe({next:()=>{this.message='Programa actualizado.';this.load();},error:e=>this.fail(e, 'No se pudo guardar el programa de fidelizaci\u00f3n.')});}
  saveTiers(): void {this.busy=true;this.api.put<any>('/api/loyalty/tiers',{tiers:this.tiers.map(t=>({...t,minimum_points:Number(t.minimum_points)}))}).subscribe({next:r=>{this.tiers=r;this.busy=false;this.message='Niveles actualizados.';},error:e=>this.fail(e, 'No se pudieron guardar los niveles de fidelizaci\u00f3n.')});}
  customerName(accountId:number):string{return this.summary?.customers?.find((x:any)=>x.customer_id===accountId)?.name??`Cuenta ${accountId}`;}
  private fail(error:unknown, fallback = 'No se pudo completar la operaci\u00f3n de fidelizaci\u00f3n.'):void{this.busy=false;this.error=loyaltyErrorMessage(error, fallback);}
}
