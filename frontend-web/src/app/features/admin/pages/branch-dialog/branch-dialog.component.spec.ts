import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { BranchDialogComponent } from './branch-dialog.component';
import { AdminBranch } from '../../models/branch-admin.model';

describe('BranchDialogComponent title', () => {
  let fixture: ComponentFixture<BranchDialogComponent>;
  let data: AdminBranch | null;

  beforeEach(async () => {
    data = null;
    await TestBed.configureTestingModule({
      imports: [BranchDialogComponent, NoopAnimationsModule],
      providers: [
        { provide: MAT_DIALOG_DATA, useFactory: () => data },
        { provide: MatDialogRef, useValue: jasmine.createSpyObj<MatDialogRef<BranchDialogComponent>>('MatDialogRef', ['close']) }
      ]
    }).compileComponents();
  });

  function renderDialog(): string {
    fixture = TestBed.createComponent(BranchDialogComponent);
    fixture.detectChanges();
    return fixture.nativeElement.querySelector('[mat-dialog-title]').textContent.trim();
  }

  it('shows Crear sucursal when no branch data is provided', () => {
    expect(renderDialog()).toBe('Crear sucursal');
  });

  it('shows Editar sucursal when editing an existing branch', () => {
    data = { id_sucursal: 17, nombre: 'Centro', direccion: 'Av. Central', ciudad: 'La Paz', estado: 'ACTIVA' };
    expect(renderDialog()).toBe('Editar sucursal');
  });
});
