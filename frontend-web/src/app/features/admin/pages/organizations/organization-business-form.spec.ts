import { FormBuilder, NonNullableFormBuilder } from '@angular/forms';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Router } from '@angular/router';
import { TestBed } from '@angular/core/testing';
import { OrganizationListComponent } from './organization-list.component';
import { OrganizationDetailComponent } from './organization-detail.component';
import { OrganizationAdminService } from '../../services/organization-admin.service';
import { OrganizationUsageService } from '../../services/organization-usage.service';
import { OrganizationActivityService } from '../../services/organization-activity.service';
import { ActivatedRoute } from '@angular/router';
import { of } from 'rxjs';

describe('organization business profile forms', () => {
  let list: OrganizationListComponent;
  let detail: OrganizationDetailComponent;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [
      { provide: NonNullableFormBuilder, useFactory: () => new FormBuilder().nonNullable },
      { provide: OrganizationAdminService, useValue: {} },
      { provide: OrganizationUsageService, useValue: {} },
      { provide: OrganizationActivityService, useValue: { list: () => of({ items: [], total: 0, limit: 25, offset: 0 }) } },
      { provide: MatDialog, useValue: {} },
      { provide: MatSnackBar, useValue: {} },
      { provide: Router, useValue: {} },
      { provide: ActivatedRoute, useValue: { snapshot: { paramMap: { get: () => '1' } } } }
    ] });
    list = TestBed.runInInjectionContext(() => new OrganizationListComponent());
    detail = TestBed.runInInjectionContext(() => new OrganizationDetailComponent());
  });

  it('accepts valid registration data and rejects invalid contact and logo formats', () => {
    list.form.patchValue({ nombre: 'Casa Estilo', slug: 'casa-estilo', nit: '123456789', correo_contacto: 'info@example.test', telefono_contacto: '+591 70000000', logo_url: 'https://cdn.example.test/logo.png' });
    expect(list.form.valid).toBeTrue();
    list.form.controls.correo_contacto.setValue('not-an-email');
    expect(list.form.controls.correo_contacto.invalid).toBeTrue();
    list.form.controls.correo_contacto.setValue('info@example.test');
    list.form.controls.logo_url.setValue('javascript:alert(1)');
    expect(list.form.controls.logo_url.invalid).toBeTrue();
  });

  it('validates fields when editing an organization profile', () => {
    detail.profileForm.patchValue({ nombre: 'Casa Estilo', slug: 'casa-estilo', correo_contacto: 'info@example.test', nit: '123456789' });
    expect(detail.profileForm.valid).toBeTrue();
    detail.profileForm.controls.nit.setValue('!');
    expect(detail.profileForm.controls.nit.invalid).toBeTrue();
    detail.profileForm.controls.slug.setValue('Invalid Slug');
    expect(detail.profileForm.controls.slug.invalid).toBeTrue();
  });
});
