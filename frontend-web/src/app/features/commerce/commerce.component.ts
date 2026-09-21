import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { ApiService } from '../../core/services/api.service';

@Component({
  standalone: true, imports: [CommonModule, FormsModule],
  styles: [`main{padding:2rem;max-width:1100px;margin:auto}form{display:flex;flex-wrap:wrap;gap:1rem;padding:1rem 0}label{display:grid;gap:.3rem}input,select,button{padding:.5rem}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:.7rem;border-bottom:1px solid #ddd}`],
  template: `<main class="commerce-page"><h1>{{titles[mode]}}</h1><p role="status">{{message}}</p>
    @if(mode === 'suppliers' || mode === 'collections' || mode === 'cities') {
      <form #masterForm="ngForm" (ngSubmit)="saveMaster()">
        <label>Nombre<input name="nombre" [(ngModel)]="master.nombre" required maxlength="150"></label>
        <label>{{mode === 'suppliers' ? 'Contacto' : 'Descripción'}}<input name="detalle" [(ngModel)]="master.detalle" maxlength="255"></label>
        <label>Estado<select name="estado" [(ngModel)]="master.estado"><option>ACTIVO</option><option>INACTIVO</option></select></label>
        <button [disabled]="masterForm.invalid || busy">{{editId ? 'Guardar cambios' : 'Crear'}}</button>
        <button type="button" (click)="resetMaster()">Nuevo</button>
      </form>
      <div class="table-scroll" role="region" aria-label="Tabla de datos" tabindex="0"><table><tr><th>Nombre</th><th>Detalle</th><th>Estado</th><th>Acciones</th></tr>
        @for(r of rows; track $index) { <tr><td>{{r.nombre}}</td><td>{{r.contacto || r.descripcion}}</td><td>{{r.estado}}</td><td><button (click)="editMaster(r)">Editar</button><button (click)="deleteMaster(r)" [disabled]="busy">Eliminar</button></td></tr> }
      </table></div>
      @if(mode !== 'cities') { <h2>Asociar productos</h2>
      <form #linkForm="ngForm" (ngSubmit)="linkProduct()">
        <label>Producto<select name="producto" [(ngModel)]="productId" (ngModelChange)="selectProduct()" required><option [ngValue]="0">Seleccionar</option>@for(p of products; track p.id_producto){<option [ngValue]="p.id_producto">{{p.nombre}}</option>}</select></label>
        <label>Proveedor<select name="proveedor" [(ngModel)]="links.id_proveedor"><option [ngValue]="null">Sin proveedor</option>@for(s of suppliers; track s.id_proveedor){<option [ngValue]="s.id_proveedor">{{s.nombre}}</option>}</select></label>
        <label>Colección<select name="coleccion" [(ngModel)]="links.id_coleccion"><option [ngValue]="null">Sin colección</option>@for(c of collections; track c.id_coleccion){<option [ngValue]="c.id_coleccion">{{c.nombre}}</option>}</select></label>
        <button [disabled]="!productId || busy">Guardar asociación</button>
      </form>
    }
    }
    @if(mode === 'promotions') {
      <form #promotionForm="ngForm" (ngSubmit)="savePromotion()">
        <label>Nombre<input name="nombre" [(ngModel)]="promotion.nombre" required maxlength="150"></label>
        <label>Producto<select name="producto" [(ngModel)]="promotion.id_producto" required><option [ngValue]="0">Seleccionar</option>@for(p of products; track p.id_producto){<option [ngValue]="p.id_producto">{{p.nombre}}</option>}</select></label>
        <label>Descuento %<input name="descuento" type="number" [(ngModel)]="promotion.descuento" min="0.01" max="100" required></label>
        <label>Desde<input name="inicio" type="date" [(ngModel)]="promotion.inicio" required></label>
        <label>Hasta<input name="fin" type="date" [(ngModel)]="promotion.fin" required></label>
        <label>Estado<select name="estado" [(ngModel)]="promotion.estado"><option>ACTIVO</option><option>INACTIVO</option></select></label>
        <button [disabled]="promotionForm.invalid || !promotion.id_producto || busy">{{editId ? 'Guardar cambios' : 'Crear promoción'}}</button>
        <button type="button" (click)="editId=0">Nueva</button>
      </form>
      <div class="table-scroll" role="region" aria-label="Tabla de datos" tabindex="0"><table><tr><th>Promoción</th><th>Producto</th><th>Descuento</th><th>Vigencia</th><th>Estado</th><th></th></tr>
        @for(r of rows; track r.id_promocion){<tr><td>{{r.nombre}}</td><td>{{productName(r.id_producto)}}</td><td>{{r.descuento}}%</td><td>{{r.inicio}} – {{r.fin}}</td><td>{{r.estado}}</td><td><button (click)="editPromotion(r)">Editar</button></td></tr>}
      </table></div>
    }
    @if(mode === 'pos') {
      <fieldset><legend>Tipo de cliente</legend><label><input type="radio" name="tipoCliente" [(ngModel)]="customerType" value="CLIENTE_REGISTRADO"> Cliente registrado</label><label><input type="radio" name="tipoCliente" [(ngModel)]="customerType" value="CONSUMIDOR_FINAL"> Consumidor final</label></fieldset>
      @if(customerType === 'CONSUMIDOR_FINAL'){<p>Consumidor final: la venta no se asociará a un cliente registrado.</p>}
      <fieldset><legend>Facturación</legend><label><input type="checkbox" [(ngModel)]="requiresInvoice"> Requiere datos de facturación</label>@if(requiresInvoice){<label>NIT / CI<input [(ngModel)]="nitCi" maxlength="30"></label><label>Razón social<input [(ngModel)]="businessName" maxlength="150"></label>}</fieldset>
      <fieldset><legend>Entrega</legend><label><input type="radio" name="entrega" [(ngModel)]="deliveryType" value="RECOJO_SUCURSAL"> Recojo en sucursal</label><label><input type="radio" name="entrega" [(ngModel)]="deliveryType" value="DELIVERY"> Delivery</label>@if(deliveryType === 'RECOJO_SUCURSAL'){<label>Sucursal<select [(ngModel)]="pickupBranchId"><option [ngValue]="0">Seleccionar sucursal</option>@for(b of saleBranches;track b.id_sucursal){<option [ngValue]="b.id_sucursal">{{b.nombre}}</option>}</select></label>}@else{<label>Dirección<input [(ngModel)]="deliveryAddress"></label><label>Referencia<input [(ngModel)]="deliveryReference"></label><label>Teléfono<input [(ngModel)]="deliveryPhone"></label>}</fieldset>
      <p>Venta presencial. QR y tarjeta se registran en modo de demostración.</p>
      <label>Cliente<select [(ngModel)]="customerId"><option [ngValue]="0">Seleccionar cliente</option>@for(c of customers; track c.id_cliente){<option [ngValue]="c.id_cliente">{{c.nombre}}</option>}</select></label>
      <form (ngSubmit)="addLine()"><label>Producto / sucursal<select name="inventario" [(ngModel)]="inventoryId"><option [ngValue]="0">Seleccionar prenda</option>@for(i of inventory; track i.id_inventario){<option [ngValue]="i.id_inventario">{{i.producto}} · {{i.talla}} · {{i.color}} · {{i.sucursal}} · stock {{i.stock}} · Bs {{i.precio}}</option>}</select></label><label>Cantidad<input name="cantidad" type="number" [(ngModel)]="quantity" min="1" required></label><button [disabled]="!inventoryId || quantity < 1 || busy">Agregar</button></form>
      <div class="table-scroll" role="region" aria-label="Tabla de datos" tabindex="0"><table><tr><th>Prenda</th><th>Cantidad</th><th>Subtotal</th><th></th></tr>@for(l of lines; track l.id_inventario){<tr><td>{{l.producto}} · {{l.talla}} · {{l.color}} · {{l.sucursal}}</td><td>{{l.cantidad}}</td><td>Bs {{l.cantidad * l.precio | number:'1.2-2'}}</td><td><button (click)="removeLine(l.id_inventario)" [disabled]="busy">Quitar</button></td></tr>}</table></div>
      <p>Total: Bs {{total | number:'1.2-2'}}</p>
      <label>Método de pago<select [(ngModel)]="paymentMethod"><option>EFECTIVO</option><option>QR</option><option>TARJETA</option></select></label>
      <button (click)="sell()" [disabled]="busy || !lines.length">Confirmar venta y pago</button>
    }
    @if(mode === 'returns') {
      <form #returnForm="ngForm" (ngSubmit)="saveReturn()">
        <label>Venta y variante<select name="detalle" [(ngModel)]="returnData.id_detalle" (ngModelChange)="returnData.id_inventario=0" required><option [ngValue]="0">Seleccionar</option>@for(d of details; track d.id_detalle){<option [ngValue]="d.id_detalle">Pedido #{{d.id_pedido}} · {{d.producto}} · {{d.talla}} · {{d.color}} · {{d.cantidad - d.devuelto}} disponibles para devolver</option>}</select></label>
        <label>Sucursal de recepción<select name="inventario" [(ngModel)]="returnData.id_inventario" required><option [ngValue]="0">Seleccionar</option>@for(i of returnInventory; track i.id_inventario){<option [ngValue]="i.id_inventario">{{i.sucursal}}</option>}</select></label>
        <label>Cantidad<input name="cantidad" type="number" [(ngModel)]="returnData.cantidad" required min="1"></label>
        <label>Motivo<input name="motivo" [(ngModel)]="returnData.motivo" required minlength="3" maxlength="255"></label>
        <button [disabled]="returnForm.invalid || !returnData.id_detalle || !returnData.id_inventario || busy">Registrar devolución</button>
      </form>
      <div class="table-scroll" role="region" aria-label="Tabla de datos" tabindex="0"><table><tr><th>Devolución</th><th>Detalle vendido</th><th>Cantidad</th><th>Estado</th><th>Motivo</th><th>Fecha</th><th></th></tr>@for(r of rows; track r.id_devolucion){<tr><td>#{{r.id_devolucion}}</td><td>#{{r.id_detalle}}</td><td>{{r.cantidad}}</td><td>{{r.estado}}</td><td>{{r.motivo}}</td><td>{{r.fecha | date:'short'}}</td><td>@if(r.estado !== 'COMPLETADA'){<button (click)="setReturnStatus(r,'APROBADA')">Aprobar</button><button (click)="setReturnStatus(r,'RECHAZADA')">Rechazar</button><button (click)="setReturnStatus(r,'COMPLETADA')">Completar</button>}</td></tr>}</table></div>
    }
    @if(mode === 'audit') { <button (click)="load()">Actualizar</button><div class="table-scroll" role="region" aria-label="Tabla de datos" tabindex="0"><table><tr><th>Fecha</th><th>Usuario</th><th>Acción</th></tr>@for(r of rows; track r.nro_bitacora){<tr><td>{{r.fecha_hora | date:'short'}}</td><td>{{r.id_usuario}}</td><td>{{r.accion}}</td></tr>}</table></div> }
  </main>`
})
export class CommerceComponent implements OnInit {
  private api = inject(ApiService); private route = inject(ActivatedRoute);
  mode = ''; titles: Record<string,string> = {cities:'Ciudades',suppliers:'Proveedores',collections:'Colecciones',promotions:'Promociones',pos:'Venta presencial',returns:'Devoluciones',audit:'Bitácora'};
  rows: any[] = []; products: any[] = []; suppliers: any[] = []; collections: any[] = []; customers: any[] = []; inventory: any[] = []; details: any[] = []; lines: any[] = [];
  busy=false; message=''; editId=0; productId=0; customerId=0; inventoryId=0; quantity=1; paymentMethod='EFECTIVO'; customerType='CLIENTE_REGISTRADO'; requiresInvoice=false; nitCi=''; businessName=''; deliveryType='RECOJO_SUCURSAL'; pickupBranchId=0; deliveryAddress=''; deliveryReference=''; deliveryPhone='';
  master={nombre:'',detalle:'',estado:'ACTIVO'};
  links: {id_proveedor:number|null;id_coleccion:number|null}={id_proveedor:null,id_coleccion:null};
  promotion={nombre:'',id_producto:0,descuento:10,inicio:new Date().toISOString().slice(0,10),fin:new Date().toISOString().slice(0,10),estado:'ACTIVO'};
  returnData={id_detalle:0,id_inventario:0,cantidad:1,motivo:''};
  ngOnInit():void { this.route.data.subscribe(data=>{this.mode=data['mode'];this.editId=0;this.message='';this.rows=[];this.load();}); }
  fail=(error:any):void=>{this.busy=false;const detail=error.error?.detail;this.message=typeof detail==='string'?detail:error.error?.message || 'Verifique los datos y vuelva a intentar';};
  get(path:string, callback:(value:any)=>void):void {this.api.get('/api/commerce/'+path).subscribe({next:callback,error:this.fail});}
  load():void {
    if(['suppliers','collections','cities','promotions'].includes(this.mode)) {
      this.get('products',r=>this.products=r);
      if(this.mode==='promotions') this.get('promotions',r=>this.rows=r);
      else if(this.mode==='cities') this.get('masters/cities',r=>this.rows=r);
      else {this.get('masters/suppliers',r=>{this.suppliers=r;if(this.mode==='suppliers')this.rows=r;});this.get('masters/collections',r=>{this.collections=r;if(this.mode==='collections')this.rows=r;});}
    } else if(this.mode==='pos') this.get('pos/options',r=>{this.customers=r.clientes;this.inventory=r.inventario;});
    else if(this.mode==='returns') {this.get('returns',r=>this.rows=r);this.get('returns/options',r=>{this.details=r.detalles;this.inventory=r.inventario;});}
    else if(this.mode==='audit') this.get('audit',r=>this.rows=r);
  }
  write(path:string,body:unknown,put=false,done?: (r:any)=>void):void {
    if(this.busy)return;this.busy=true;this.message='';
    const request=put?this.api.put('/api/commerce/'+path,body):this.api.post('/api/commerce/'+path,body);
    request.subscribe({next:r=>{this.busy=false;this.message='Operación guardada';done?.(r);this.load();},error:this.fail});
  }
  deleteMaster(r:any):void {if(!window.confirm('Eliminar '+r.nombre+'?'))return;this.busy=true;this.api.delete('/api/commerce/masters/'+this.mode+'/'+(r.id_proveedor||r.id_coleccion||r.id_ciudad)).subscribe({next:()=>{this.busy=false;this.message='Registro eliminado';this.load();},error:this.fail});}
  resetMaster():void {this.editId=0;this.master={nombre:'',detalle:'',estado:'ACTIVO'};}
  editMaster(r:any):void {this.editId=r.id_proveedor || r.id_coleccion || r.id_ciudad;this.master={nombre:r.nombre,detalle:r.contacto || r.descripcion || '',estado:r.estado};}
  saveMaster():void {this.write('masters/'+this.mode+(this.editId?'/'+this.editId:''),this.master,!!this.editId,()=>this.resetMaster());}
  selectProduct():void {const p=this.products.find(p=>p.id_producto===this.productId);this.links={id_proveedor:p?.id_proveedor??null,id_coleccion:p?.id_coleccion??null};}
  linkProduct():void {this.write(`products/${this.productId}/links`,this.links,true);}
  productName(id:number):string {return this.products.find(p=>p.id_producto===id)?.nombre || String(id);}
  editPromotion(r:any):void {this.editId=r.id_promocion;this.promotion={...r};}
  savePromotion():void {this.write('promotions'+(this.editId?'/'+this.editId:''),this.promotion,!!this.editId);}
  addLine():void {const i=this.inventory.find(i=>i.id_inventario===this.inventoryId);if(!i || !Number.isInteger(this.quantity) || this.quantity<1)return;const existing=this.lines.find(l=>l.id_inventario===i.id_inventario);if((existing?.cantidad||0)+this.quantity>i.stock){this.message='Stock insuficiente';return;}if(this.lines.length && this.lines[0].id_sucursal!==i.id_sucursal){this.message='Seleccione una sola sucursal por venta';return;}if(existing)existing.cantidad+=this.quantity;else this.lines.push({...i,cantidad:this.quantity});}
  removeLine(id:number):void {this.lines=this.lines.filter(l=>l.id_inventario!==id);}
  get total():number {return this.lines.reduce((sum,l)=>sum+l.cantidad*Number(l.precio),0);}
  get saleBranches():any[]{return this.inventory.filter((i:any,index:number,all:any[])=>all.findIndex(x=>x.id_sucursal===i.id_sucursal)===index).map((i:any)=>({id_sucursal:i.id_sucursal,nombre:i.sucursal}));}
  sell():void {if(this.customerType==='CLIENTE_REGISTRADO'&&!this.customerId){this.message='Seleccione un cliente registrado';return;}if(this.requiresInvoice&&(!this.nitCi||!this.businessName)){this.message='Complete NIT/CI y razón social';return;}if(this.deliveryType==='RECOJO_SUCURSAL'&&!this.pickupBranchId){this.message='Seleccione la sucursal de recojo';return;}if(this.deliveryType==='DELIVERY'&&(!this.deliveryAddress||!this.deliveryPhone)){this.message='Delivery requiere dirección y teléfono';return;}this.write('pos',{id_cliente:this.customerType==='CLIENTE_REGISTRADO'?this.customerId:null,tipo_cliente:this.customerType,metodo_pago:this.paymentMethod,nit_ci:this.requiresInvoice?this.nitCi:null,razon_social:this.requiresInvoice?this.businessName:null,tipo_entrega:this.deliveryType,id_sucursal_entrega:this.deliveryType==='RECOJO_SUCURSAL'?this.pickupBranchId:null,direccion_entrega:this.deliveryType==='DELIVERY'?this.deliveryAddress:null,referencia_entrega:this.deliveryType==='DELIVERY'?this.deliveryReference:null,telefono_entrega:this.deliveryType==='DELIVERY'?this.deliveryPhone:null,items:this.lines.map(l=>({id_inventario:l.id_inventario,cantidad:l.cantidad}))},false,r=>{this.lines=[];this.message=`Venta #${r.id_pedido} registrada. Total Bs ${r.total}`;});}
  get returnInventory():any[] {const detail=this.details.find(d=>d.id_detalle===this.returnData.id_detalle);return this.inventory.filter(i=>i.id_variante===detail?.id_variante);}
  saveReturn():void {this.write('returns',this.returnData,false,()=>{this.returnData={id_detalle:0,id_inventario:0,cantidad:1,motivo:''};});}
  setReturnStatus(row:any,status:string):void {this.write(`returns/${row.id_devolucion}/status`,{estado:status},true);}
}
