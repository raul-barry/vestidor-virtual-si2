import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';
import { of } from 'rxjs';
import { ProductAdminService } from '../../../services/product-admin.service';
import { CategoryAdminService } from '../../../services/category-admin.service';
import { ProductFormComponent } from './product-form.component';

describe('ProductFormComponent',()=>{
 let component:ProductFormComponent;let fixture:ComponentFixture<ProductFormComponent>;let service:jasmine.SpyObj<ProductAdminService>;
 beforeEach(async()=>{service=jasmine.createSpyObj<ProductAdminService>('ProductAdminService',['create','update','getById','uploadImage','deleteImage']);const categories=jasmine.createSpyObj<CategoryAdminService>('CategoryAdminService',['list']);categories.list.and.returnValue(of([{id_categoria:1,nombre:'Camisas',descripcion:null,estado:'ACTIVO'}]));await TestBed.configureTestingModule({imports:[ProductFormComponent,NoopAnimationsModule],providers:[{provide:ProductAdminService,useValue:service},{provide:CategoryAdminService,useValue:categories},{provide:Router,useValue:jasmine.createSpyObj<Router>('Router',['navigate'])},{provide:ActivatedRoute,useValue:{snapshot:{paramMap:convertToParamMap({})}}},{provide:MatSnackBar,useValue:jasmine.createSpyObj<MatSnackBar>('MatSnackBar',['open'])}]}).compileComponents();fixture=TestBed.createComponent(ProductFormComponent);component=fixture.componentInstance;fixture.detectChanges();});
 it('validates required product fields',()=>{component.save();expect(service.create).not.toHaveBeenCalled();});
 it('creates a valid product',()=>{service.create.and.returnValue(of({id_producto:1,nombre:'Camisa',descripcion:null,precio_base:'250',estado:'ACTIVO',categoria:{id_categoria:1,nombre:'Camisas'}}));component.form.setValue({nombre:'Camisa',descripcion:'',precio_base:250,id_categoria:1});component.save();expect(service.create).toHaveBeenCalled();});
});
