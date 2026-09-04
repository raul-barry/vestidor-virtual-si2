import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of, throwError } from 'rxjs';
import { OrderAdminService } from '../../../services/order-admin.service';
import { OrderDetailComponent } from './order-detail.component';
describe('OrderDetailComponent',()=>{let fixture:ComponentFixture<OrderDetailComponent>;let service:jasmine.SpyObj<OrderAdminService>;beforeEach(async()=>{service=jasmine.createSpyObj<OrderAdminService>('OrderAdminService',['getOrderDetail']);await TestBed.configureTestingModule({imports:[OrderDetailComponent,NoopAnimationsModule],providers:[{provide:OrderAdminService,useValue:service},{provide:ActivatedRoute,useValue:{snapshot:{paramMap:convertToParamMap({id:'1'})}}},{provide:MatSnackBar,useValue:jasmine.createSpyObj<MatSnackBar>('MatSnackBar',['open'])}]}).compileComponents()});it('loads detail',()=>{service.getOrderDetail.and.returnValue(of({id_pedido:1,cliente:'Carlos',fecha:'2026-09-02',estado:'PENDIENTE',total:'500',detalles:[],pago:null}));fixture=TestBed.createComponent(OrderDetailComponent);fixture.detectChanges();expect(fixture.nativeElement.textContent).toContain('Carlos')});it('handles error',()=>{service.getOrderDetail.and.returnValue(throwError(()=>new Error()));fixture=TestBed.createComponent(OrderDetailComponent);fixture.detectChanges();expect(fixture.componentInstance.error).toBeTrue()})});
