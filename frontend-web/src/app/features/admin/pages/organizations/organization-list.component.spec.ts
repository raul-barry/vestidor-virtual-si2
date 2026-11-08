import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of } from 'rxjs';
import { OrganizationListComponent } from './organization-list.component';
import { OrganizationAdminService } from '../../services/organization-admin.service';
import { OrganizationAdmin } from '../../models/organization-admin.model';

describe('OrganizationListComponent detail navigation', () => {
  let fixture: ComponentFixture<OrganizationListComponent>;
  let router: jasmine.SpyObj<Router>;
  let snack: jasmine.SpyObj<MatSnackBar>;

  const organizations: OrganizationAdmin[] = [
    { id_organizacion: 1, nombre: 'Elegance Boutique', razon_social: null, nit: null, correo_contacto: null,
      telefono_contacto: null, direccion: null, logo_url: null, slug: 'elegance-boutique', estado: 'ACTIVA',
      fecha_creacion: null, fecha_actualizacion: null },
    { id_organizacion: 2, nombre: 'FashionStore', razon_social: null, nit: null, correo_contacto: null,
      telefono_contacto: null, direccion: null, logo_url: null, slug: 'fashionstore', estado: 'ACTIVA',
      fecha_creacion: null, fecha_actualizacion: null },
    { id_organizacion: 3, nombre: 'UrbanVogue', razon_social: null, nit: null, correo_contacto: null,
      telefono_contacto: null, direccion: null, logo_url: null, slug: 'urbanvogue', estado: 'ACTIVA',
      fecha_creacion: null, fecha_actualizacion: null }
  ];

  beforeEach(async () => {
    router = jasmine.createSpyObj<Router>('Router', ['navigate']);
    router.navigate.and.resolveTo(true);
    snack = jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']);
    const service = jasmine.createSpyObj<OrganizationAdminService>('OrganizationAdminService', ['list']);
    service.list.and.returnValue(of(organizations));

    await TestBed.configureTestingModule({
      imports: [OrganizationListComponent, NoopAnimationsModule],
      providers: [
        { provide: OrganizationAdminService, useValue: service },
        { provide: Router, useValue: router },
        { provide: MatDialog, useValue: jasmine.createSpyObj<MatDialog>('MatDialog', ['open']) },
        { provide: MatSnackBar, useValue: snack }
      ]
    }).compileComponents();
    fixture = TestBed.createComponent(OrganizationListComponent);
    fixture.detectChanges();
  });

  it('opens the requested organization row for each listed company', async () => {
    for (const organization of organizations) {
      fixture.componentInstance.openDetail(organization);
      await fixture.whenStable();
    }

    expect(router.navigate.calls.allArgs()).toEqual([
      [['/platform/organizations', 1]],
      [['/platform/organizations', 2]],
      [['/platform/organizations', 3]]
    ]);
  });

  it('rejects invalid identifiers before attempting navigation', () => {
    fixture.componentInstance.openDetail({ ...organizations[0], id_organizacion: 0 });
    expect(router.navigate).not.toHaveBeenCalled();

  });
});
