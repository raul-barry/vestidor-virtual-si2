import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA } from '@angular/material/dialog';
import { of } from 'rxjs';
import { InventoryAdminService } from '../../services/inventory-admin.service';
import { InventoryHistoryDialogComponent } from './inventory-history-dialog.component';

describe('InventoryHistoryDialogComponent', () => {
  let fixture: ComponentFixture<InventoryHistoryDialogComponent>;
  let service: jasmine.SpyObj<InventoryAdminService>;

  beforeEach(async () => {
    service = jasmine.createSpyObj<InventoryAdminService>('InventoryAdminService', ['getMovements']);
    service.getMovements.and.returnValue(of([{
      tipo: 'ENTRADA', cantidad: 4, stock_anterior: 2, stock_nuevo: 6,
      motivo: 'Reposición por proveedor', usuario: 'Administradora', fecha: '2026-11-06T12:00:00Z'
    }]));

    await TestBed.configureTestingModule({
      imports: [InventoryHistoryDialogComponent],
      providers: [
        { provide: MAT_DIALOG_DATA, useValue: { id: 17 } },
        { provide: InventoryAdminService, useValue: service }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(InventoryHistoryDialogComponent);
    fixture.detectChanges();
  });

  it('loads and displays the stored movement reason', () => {
    expect(service.getMovements).toHaveBeenCalledWith(17);
    expect(fixture.nativeElement.textContent).toContain('Reposición por proveedor');
  });
});
