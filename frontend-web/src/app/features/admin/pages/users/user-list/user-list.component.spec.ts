import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Router } from '@angular/router';
import { of } from 'rxjs';
import { UserAdminService } from '../../../services/user-admin.service';
import { UserListComponent } from './user-list.component';
describe('UserListComponent',()=>{let fixture:ComponentFixture<UserListComponent>;beforeEach(async()=>{const service=jasmine.createSpyObj<UserAdminService>('UserAdminService',['getUsers','updateStatus','updateRole']);service.getUsers.and.returnValue(of([]));await TestBed.configureTestingModule({imports:[UserListComponent,NoopAnimationsModule],providers:[{provide:UserAdminService,useValue:service},{provide:Router,useValue:jasmine.createSpyObj<Router>('Router',['navigate'])}]}).compileComponents();fixture=TestBed.createComponent(UserListComponent);fixture.detectChanges()});it('loads users page',()=>expect(fixture.nativeElement.textContent).toContain('Usuarios'));});
