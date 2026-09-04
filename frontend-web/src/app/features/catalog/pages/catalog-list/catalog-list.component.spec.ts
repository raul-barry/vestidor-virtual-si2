import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { RouterTestingModule } from '@angular/router/testing';
import { of, throwError } from 'rxjs';
import { AuthService } from '../../../auth/services/auth.service';
import { CatalogService } from '../../services/catalog.service';
import { CatalogListComponent } from './catalog-list.component';

describe('CatalogListComponent', () => {
  let component: CatalogListComponent;
  let fixture: ComponentFixture<CatalogListComponent>;
  let authService: jasmine.SpyObj<AuthService>;
  let catalogService: jasmine.SpyObj<CatalogService>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;

  beforeEach(async () => {
    authService = jasmine.createSpyObj<AuthService>('AuthService', ['clearSession', 'hasSession', 'logout']);
    authService.hasSession.and.returnValue(false);
    authService.logout.and.returnValue(of({ message: 'ok' }));
    catalogService = jasmine.createSpyObj<CatalogService>('CatalogService', ['getProducts', 'searchProducts']);
    snackBar = jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']);

    TestBed.configureTestingModule({
      imports: [CatalogListComponent, NoopAnimationsModule, RouterTestingModule],
      providers: [
        { provide: AuthService, useValue: authService },
        { provide: CatalogService, useValue: catalogService },
        { provide: MatSnackBar, useValue: snackBar }
      ]
    }).overrideComponent(CatalogListComponent, {
      set: { providers: [{ provide: MatSnackBar, useValue: snackBar }] }
    });

    await TestBed.compileComponents();
  });

  it('loads catalog products', () => {
    catalogService.getProducts.and.returnValue(of([{
      id_producto: 1,
      nombre: 'Camisa Oxford',
      descripcion: null,
      precio_base: '250.00',
      estado: 'ACTIVO',
      categoria: { id_categoria: 1, nombre: 'Camisas' },
      variantes: []
    }]));
    fixture = TestBed.createComponent(CatalogListComponent);
    component = fixture.componentInstance;

    fixture.detectChanges();

    expect(catalogService.getProducts).toHaveBeenCalled();
    expect(component.products).toHaveSize(1);
  });

  it('shows an error when the API fails', () => {
    catalogService.getProducts.and.returnValue(throwError(() => new Error('Network error')));
    fixture = TestBed.createComponent(CatalogListComponent);
    component = fixture.componentInstance;

    fixture.detectChanges();

    expect(snackBar.open).toHaveBeenCalledWith('No fue posible cargar el catálogo', 'Cerrar', {
      duration: 5000
    });
  });

  it('keeps an empty list when a search has no results', () => {
    catalogService.getProducts.and.returnValue(of([]));
    catalogService.searchProducts.and.returnValue(of([]));
    fixture = TestBed.createComponent(CatalogListComponent);
    component = fixture.componentInstance;

    fixture.detectChanges();
    component.onFiltersChange({ nombre: 'inexistente' });

    expect(component.products).toEqual([]);
  });

  it('searches products when filters are provided', () => {
    catalogService.getProducts.and.returnValue(of([]));
    catalogService.searchProducts.and.returnValue(of([]));
    fixture = TestBed.createComponent(CatalogListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    component.onFiltersChange({ categoria: 'Camisas', talla: 'M' });

    expect(catalogService.searchProducts).toHaveBeenCalledWith({ categoria: 'Camisas', talla: 'M' });
  });

  it('reloads the complete catalog when filters are cleared', () => {
    catalogService.getProducts.and.returnValue(of([]));
    fixture = TestBed.createComponent(CatalogListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    component.onFiltersChange({});

    expect(catalogService.getProducts).toHaveBeenCalledTimes(2);
  });
});
