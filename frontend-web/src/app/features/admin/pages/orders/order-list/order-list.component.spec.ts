import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Router } from '@angular/router';
import { of } from 'rxjs';
import { OrderAdminService } from '../../../services/order-admin.service';
import { OrderListComponent } from './order-list.component';
describe('OrderListComponent',()=>{let fixture:ComponentFixture<OrderListComponent>;beforeEach(async()=>{const service=jasmine.createSpyObj<OrderAdminService>('OrderAdminService',['getOrders','updateStatus']);service.getOrders.and.returnValue(of([]));await TestBed.configureTestingModule({imports:[OrderListComponent,NoopAnimationsModule],providers:[{provide:OrderAdminService,useValue:service},{provide:Router,useValue:jasmine.createSpyObj<Router>('Router',['navigate'])}]}).compileComponents();fixture=TestBed.createComponent(OrderListComponent);fixture.detectChanges()});it('loads orders page',()=>expect(fixture.nativeElement.textContent).toContain('Pedidos'));});
