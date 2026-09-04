import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ProductAdminService } from '../../../services/product-admin.service';
import { ProductListComponent } from './product-list.component';
describe('ProductListComponent',()=>{let fixture:ComponentFixture<ProductListComponent>; beforeEach(async()=>{const service=jasmine.createSpyObj<ProductAdminService>('ProductAdminService',['list','disable']);service.list.and.returnValue(of([]));await TestBed.configureTestingModule({imports:[ProductListComponent,NoopAnimationsModule],providers:[{provide:ProductAdminService,useValue:service}]}).compileComponents();fixture=TestBed.createComponent(ProductListComponent);fixture.detectChanges()});it('loads product table state',()=>expect(fixture.nativeElement.textContent).toContain('Productos'));});
