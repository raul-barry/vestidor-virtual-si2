import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of } from 'rxjs';
import { InventoryAdminService } from '../../../services/inventory-admin.service';
import { InventoryListComponent } from './inventory-list.component';
describe('InventoryListComponent',()=>{let fixture:ComponentFixture<InventoryListComponent>;beforeEach(async()=>{const service=jasmine.createSpyObj<InventoryAdminService>('InventoryAdminService',['getInventory']);service.getInventory.and.returnValue(of([]));await TestBed.configureTestingModule({imports:[InventoryListComponent,NoopAnimationsModule],providers:[{provide:InventoryAdminService,useValue:service}]}).compileComponents();fixture=TestBed.createComponent(InventoryListComponent);fixture.detectChanges()});it('loads inventory page',()=>expect(fixture.nativeElement.textContent).toContain('Inventario'));});
