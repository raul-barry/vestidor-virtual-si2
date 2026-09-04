import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of } from 'rxjs';
import { VariantAdminService } from '../../../services/variant-admin.service';
import { VariantListComponent } from './variant-list.component';
describe('VariantListComponent',()=>{let fixture:ComponentFixture<VariantListComponent>;beforeEach(async()=>{const service=jasmine.createSpyObj<VariantAdminService>('VariantAdminService',['list','disable']);service.list.and.returnValue(of([]));await TestBed.configureTestingModule({imports:[VariantListComponent,NoopAnimationsModule],providers:[{provide:VariantAdminService,useValue:service}]}).compileComponents();fixture=TestBed.createComponent(VariantListComponent);fixture.detectChanges()});it('renders variants page',()=>expect(fixture.nativeElement.textContent).toContain('Variantes'));});
