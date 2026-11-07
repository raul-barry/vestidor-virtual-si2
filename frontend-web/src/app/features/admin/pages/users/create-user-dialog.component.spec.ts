import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialogRef } from '@angular/material/dialog';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of, throwError } from 'rxjs';
import { BranchAdminService } from '../../services/branch-admin.service';
import { RoleAdminService } from '../../services/role-admin.service';
import { CreateUserDialogComponent } from './create-user-dialog.component';

describe('CreateUserDialogComponent', () => {
  let fixture: ComponentFixture<CreateUserDialogComponent>;
  let roleService: jasmine.SpyObj<RoleAdminService>;
  let branchService: jasmine.SpyObj<BranchAdminService>;
  let dialogRef: jasmine.SpyObj<MatDialogRef<CreateUserDialogComponent>>;

  const roles = [
    { id_rol: 2, nombre: 'CLIENTE', descripcion: null, estado: 'ACTIVO', protegido: true, permisos: [] },
    { id_rol: 3, nombre: 'ENCARGADO_SUCURSAL', descripcion: null, estado: 'ACTIVO', protegido: true, permisos: [] },
    { id_rol: 5, nombre: 'ADMINISTRADOR_PLATAFORMA', descripcion: null, estado: 'ACTIVO', protegido: true, permisos: [] }
  ];
  const branches = [{ id_sucursal: 12, nombre: 'Sucursal Centro', direccion: 'Centro', ciudad: 'La Paz', estado: 'ACTIVA' }];

  beforeEach(async () => {
    roleService = jasmine.createSpyObj<RoleAdminService>('RoleAdminService', ['listAssignable']);
    branchService = jasmine.createSpyObj<BranchAdminService>('BranchAdminService', ['list']);
    dialogRef = jasmine.createSpyObj<MatDialogRef<CreateUserDialogComponent>>('MatDialogRef', ['close']);
    roleService.listAssignable.and.returnValue(of(roles));
    branchService.list.and.returnValue(of(branches));
    await TestBed.configureTestingModule({
      imports: [CreateUserDialogComponent, NoopAnimationsModule],
      providers: [
        { provide: RoleAdminService, useValue: roleService },
        { provide: BranchAdminService, useValue: branchService },
        { provide: MatDialogRef, useValue: dialogRef }
      ]
    }).compileComponents();
  });

  function createFixture(): void {
    fixture = TestBed.createComponent(CreateUserDialogComponent);
    fixture.detectChanges();
  }

  it('loads active business roles, omits platform role, and assigns branch role to a tenant branch', () => {
    createFixture();
    const component = fixture.componentInstance;
    expect(component.roles.map(role => role.nombre)).toEqual(['CLIENTE', 'ENCARGADO_SUCURSAL']);

    component.form.patchValue({ nombres: 'Ana', apellidos: 'Paz', correo: 'ana@example.test', password: 'Seguro123!' });
    component.form.controls.rol.setValue('ENCARGADO_SUCURSAL');
    component.roleChanged();
    component.form.controls.id_sucursal.setValue(12);

    expect(branchService.list).toHaveBeenCalled();
    expect(component.canSave).toBeTrue();
    component.save();
    expect(dialogRef.close).toHaveBeenCalledWith(jasmine.objectContaining({
      rol: 'ENCARGADO_SUCURSAL', id_sucursal: 12
    }));
  });

  it('does not allow a staff user without a branch and reports role load failures', () => {
    createFixture();
    const component = fixture.componentInstance;
    component.form.controls.rol.setValue('ENCARGADO_SUCURSAL');
    component.roleChanged();
    expect(component.canSave).toBeFalse();

    fixture.destroy();
    roleService.listAssignable.and.returnValue(throwError(() => new Error('offline')));
    createFixture();
    expect(fixture.componentInstance.rolesError).toBeTruthy();
    expect(fixture.componentInstance.canSave).toBeFalse();
  });
});
