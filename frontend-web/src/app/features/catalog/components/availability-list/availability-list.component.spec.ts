import { ComponentFixture, TestBed } from '@angular/core/testing';
import { AvailabilityListComponent } from './availability-list.component';

describe('AvailabilityListComponent', () => {
  let fixture: ComponentFixture<AvailabilityListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AvailabilityListComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(AvailabilityListComponent);
    fixture.componentInstance.availability = [{
      id_sucursal: 1,
      nombre_sucursal: 'Sucursal Central',
      direccion: 'Av. Principal 100',
      stock_disponible: 5
    }];
    fixture.detectChanges();
  });

  it('renders branch availability', () => {
    expect(fixture.nativeElement.textContent).toContain('Sucursal Central');
    expect(fixture.nativeElement.textContent).toContain('Av. Principal 100');
    expect(fixture.nativeElement.textContent).toContain('5 disponibles');
  });
});
