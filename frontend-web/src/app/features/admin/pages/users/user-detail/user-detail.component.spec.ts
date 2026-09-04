import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of, throwError } from 'rxjs';
import { UserAdminService } from '../../../services/user-admin.service';
import { UserDetailComponent } from './user-detail.component';
describe('UserDetailComponent',()=>{let fixture:ComponentFixture<UserDetailComponent>;let service:jasmine.SpyObj<UserAdminService>;beforeEach(async()=>{service=jasmine.createSpyObj<UserAdminService>('UserAdminService',['getUserDetail']);await TestBed.configureTestingModule({imports:[UserDetailComponent,NoopAnimationsModule],providers:[{provide:UserAdminService,useValue:service},{provide:ActivatedRoute,useValue:{snapshot:{paramMap:convertToParamMap({id:'1'})}}},{provide:MatSnackBar,useValue:jasmine.createSpyObj<MatSnackBar>('MatSnackBar',['open'])}]}).compileComponents()});it('loads detail',()=>{service.getUserDetail.and.returnValue(of({id_usuario:1,nombres:'Admin',apellidos:'User',correo:'a@b.com',telefono:null,rol:'ADMINISTRADOR',estado:'ACTIVO'}));fixture=TestBed.createComponent(UserDetailComponent);fixture.detectChanges();expect(fixture.nativeElement.textContent).toContain('a@b.com')});it('handles error',()=>{service.getUserDetail.and.returnValue(throwError(()=>new Error()));fixture=TestBed.createComponent(UserDetailComponent);fixture.detectChanges();expect(fixture.componentInstance.error).toBeTrue()})});
