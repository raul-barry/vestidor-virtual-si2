import { TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { ApiService } from '../../../../core/services/api.service';
import { LoyaltyAdminComponent } from './loyalty-admin.component';

describe('LoyaltyAdminComponent', () => {
  let api: jasmine.SpyObj<ApiService>;
  beforeEach(async () => {
    api = jasmine.createSpyObj<ApiService>('ApiService', ['get', 'put']);
    api.get.and.callFake((path: string) => of(path.endsWith('/program')
      ? {program:{active:false,name:'Club',points_per_currency:'1',currency_per_point:'0.01',minimum_redeem_points:10,max_discount_percent:'20',expiration_days:null},tiers:[]}
      : {customers:[],ledger:[],metrics:{customers:0,earned:0,redeemed:0,expired:0}}) as any);
    api.put.and.returnValue(of({}) as any);
    await TestBed.configureTestingModule({imports:[LoyaltyAdminComponent],providers:[{provide:ApiService,useValue:api}]}).compileComponents();
  });
  it('loads the tenant loyalty program and ledger summary', () => {
    const fixture=TestBed.createComponent(LoyaltyAdminComponent);fixture.detectChanges();
    expect(api.get).toHaveBeenCalledWith('/api/loyalty/program');
    expect(api.get).toHaveBeenCalledWith('/api/loyalty/admin/summary');
    expect(fixture.nativeElement.textContent).toContain('Fidelización');
    expect(fixture.nativeElement.textContent).toContain('Saldo');
  });
  it('saves configuration without supplying organization identifiers', () => {
    const fixture=TestBed.createComponent(LoyaltyAdminComponent);fixture.detectChanges();
    fixture.componentInstance.form.active=true;fixture.componentInstance.save();
    expect(api.put).toHaveBeenCalledWith('/api/loyalty/program', jasmine.objectContaining({active:true}));
    expect('organization_id' in (api.put.calls.mostRecent().args[1] as object)).toBeFalse();
  });

  it('turns FastAPI validation errors into Spanish messages when saving the program', () => {
    const fixture=TestBed.createComponent(LoyaltyAdminComponent);fixture.detectChanges();
    api.put.and.returnValue(throwError(() => ({status:422,error:{detail:[
      {loc:['body','points_per_currency'],msg:'Input should be greater than 0'}
    ]}})) as any);
    fixture.componentInstance.save();
    expect(fixture.componentInstance.error).toBe('El campo puntos por cada boliviano debe ser mayor que cero.');
    expect(fixture.nativeElement.textContent).not.toContain('[object Object]');
  });

  it('handles nested server messages when saving levels', () => {
    const fixture=TestBed.createComponent(LoyaltyAdminComponent);fixture.detectChanges();
    api.put.and.returnValue(throwError(() => ({status:409,error:{detail:{code:'LEVEL_CONFLICT',message:'El código del nivel ya existe.'}}})) as any);
    fixture.componentInstance.saveTiers();
    expect(fixture.componentInstance.error).toBe('El código del nivel ya existe.');
    expect(fixture.componentInstance.error).not.toMatch(/\[object Object\]|undefined|null/);
  });

  it('uses a Spanish fallback when the server error has no usable message', () => {
    const fixture=TestBed.createComponent(LoyaltyAdminComponent);fixture.detectChanges();
    api.put.and.returnValue(throwError(() => ({status:500,error:{detail:{code:'INTERNAL'}}})) as any);
    fixture.componentInstance.save();
    expect(fixture.componentInstance.error).toBe('No se pudo guardar el programa de fidelización.');
  });
});
