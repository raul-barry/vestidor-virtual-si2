import { TestBed } from '@angular/core/testing';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of, throwError } from 'rxjs';
import { BranchListComponent } from './branch-list.component';
import { BranchAdminService } from '../../services/branch-admin.service';

describe('BranchListComponent', () => {
  let service: jasmine.SpyObj<BranchAdminService>;
  let dialog: jasmine.SpyObj<MatDialog>;
  let snack: jasmine.SpyObj<MatSnackBar>;

  beforeEach(async () => {
    service = jasmine.createSpyObj<BranchAdminService>('BranchAdminService', ['list', 'create', 'update', 'toggleStatus', 'delete']);
    service.list.and.returnValue(of([]));
    dialog = jasmine.createSpyObj<MatDialog>('MatDialog', ['open']);
    snack = jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']);
    await TestBed.configureTestingModule({
      imports: [BranchListComponent],
      providers: [
        { provide: BranchAdminService, useValue: service },
        { provide: MatDialog, useValue: dialog },
        { provide: MatSnackBar, useValue: snack },
      ],
    }).compileComponents();
  });

  function openCreateForm() {
    dialog.open.and.returnValue({ afterClosed: () => of({ nombre: 'Sucursal nueva', direccion: 'Calle 1', ciudad: 'La Paz' }) } as never);
    const fixture = TestBed.createComponent(BranchListComponent);
    fixture.detectChanges();
    fixture.componentInstance.openForm();
    return fixture;
  }

  it('explains the current plan and dynamic branch limit when the server rejects creation at capacity', () => {
    service.create.and.returnValue(throwError(() => ({ error: { detail: {
      code: 'PLAN_LIMIT_REACHED', resource: 'sucursales_activas', plan_nombre: 'Plan Estilo', limit: 2, current: 2,
    } } })));

    openCreateForm();

    expect(snack.open).toHaveBeenCalledWith(
      'No se pudo crear la sucursal. Tu plan Plan Estilo permite un máximo de 2 sucursales y ya alcanzaste ese límite. Actualiza tu plan para agregar más sucursales.',
      'Cerrar', { duration: 5000 },
    );
  });

  it('keeps the generic message for errors unrelated to commercial limits', () => {
    service.create.and.returnValue(throwError(() => ({ status: 500 })));

    openCreateForm();

    expect(snack.open).toHaveBeenCalledWith('No se pudo guardar', 'Cerrar', { duration: 5000 });
  });

  it('creates normally when the service accepts the branch', () => {
    service.create.and.returnValue(of({ id_sucursal: 7, nombre: 'Sucursal nueva', direccion: 'Calle 1', ciudad: 'La Paz', estado: 'ACTIVA' }));

    openCreateForm();

    expect(service.create).toHaveBeenCalledWith({ nombre: 'Sucursal nueva', direccion: 'Calle 1', ciudad: 'La Paz' });
    expect(snack.open).not.toHaveBeenCalled();
    expect(service.list).toHaveBeenCalledTimes(2);
  });
});
