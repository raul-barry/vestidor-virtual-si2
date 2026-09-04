import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { RouterTestingModule } from '@angular/router/testing';
import { of, throwError } from 'rxjs';
import { ProfileService } from '../../services/profile.service';
import { ProfileViewComponent } from './profile-view.component';

describe('ProfileViewComponent', () => {
  let component: ProfileViewComponent;
  let fixture: ComponentFixture<ProfileViewComponent>;
  let profileService: jasmine.SpyObj<ProfileService>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;

  beforeEach(async () => {
    profileService = jasmine.createSpyObj<ProfileService>('ProfileService', ['getProfile']);
    snackBar = jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']);

    TestBed.configureTestingModule({
      imports: [ProfileViewComponent, NoopAnimationsModule, RouterTestingModule],
      providers: [
        { provide: ProfileService, useValue: profileService },
        { provide: MatSnackBar, useValue: snackBar }
      ]
    }).overrideComponent(ProfileViewComponent, {
      set: { providers: [{ provide: MatSnackBar, useValue: snackBar }] }
    });

    profileService.getProfile.and.returnValue(of({
      id_usuario: 1,
      nombres: 'Carlos',
      apellidos: 'Perez',
      correo: 'cliente@example.com',
      telefono: '70000000'
    }));
    await TestBed.compileComponents();
    fixture = TestBed.createComponent(ProfileViewComponent);
    component = fixture.componentInstance;
  });

  it('loads the authenticated profile', () => {
    fixture.detectChanges();

    expect(profileService.getProfile).toHaveBeenCalled();
    expect(component.profile?.correo).toBe('cliente@example.com');
  });

  it('shows an API error message', () => {
    profileService.getProfile.and.returnValue(throwError(() => new Error('Network error')));
    fixture = TestBed.createComponent(ProfileViewComponent);
    component = fixture.componentInstance;

    fixture.detectChanges();

    expect(snackBar.open).toHaveBeenCalledWith('No fue posible cargar el perfil', 'Cerrar', {
      duration: 5000
    });
  });
});
