import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
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
});
