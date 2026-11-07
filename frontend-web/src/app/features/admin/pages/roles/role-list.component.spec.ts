import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of, throwError } from 'rxjs';
import { RoleAdminService } from '../../services/role-admin.service';
import { RoleListComponent } from './role-list.component';

describe('RoleListComponent', () => {
  let fixture: ComponentFixture<RoleListComponent>;
  let service: jasmine.SpyObj<RoleAdminService>;

  beforeEach(async () => {
    service = jasmine.createSpyObj<RoleAdminService>('RoleAdminService', ['list', 'permissions', 'create', 'update', 'toggle']);
    service.list.and.returnValue(of([{ id_rol: 1, nombre: 'CLIENTE', descripcion: null, estado: 'ACTIVO', protegido: true, permisos: [] }]));
    service.permissions.and.returnValue(of([]));
    await TestBed.configureTestingModule({
      imports: [RoleListComponent, NoopAnimationsModule],
      providers: [
        { provide: RoleAdminService, useValue: service },
        { provide: MatDialog, useValue: jasmine.createSpyObj<MatDialog>('MatDialog', ['open']) },
        { provide: MatSnackBar, useValue: jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']) }
      ]
    }).compileComponents();
  });

  it('loads and displays roles on the platform role management page', () => {
    fixture = TestBed.createComponent(RoleListComponent);
    fixture.detectChanges();
    expect(fixture.componentInstance.loading).toBeFalse();
    expect(fixture.nativeElement.textContent).toContain('Roles y permisos');
    expect(fixture.nativeElement.textContent).toContain('CLIENTE');
  });

  it('shows a retryable error when the platform role catalog cannot be loaded', () => {
    service.list.and.returnValue(throwError(() => new Error('forbidden')));
    fixture = TestBed.createComponent(RoleListComponent);
    fixture.detectChanges();
    expect(fixture.componentInstance.error).toContain('No fue posible');
    expect(fixture.nativeElement.textContent).toContain('Reintentar');
  });
});
