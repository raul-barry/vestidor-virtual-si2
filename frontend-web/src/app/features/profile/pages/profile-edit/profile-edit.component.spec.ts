import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Router } from '@angular/router';
import { of } from 'rxjs';
import { ProfileService } from '../../services/profile.service';
import { ProfileEditComponent } from './profile-edit.component';

describe('ProfileEditComponent', () => {
  let component: ProfileEditComponent;
  let fixture: ComponentFixture<ProfileEditComponent>;
  let profileService: jasmine.SpyObj<ProfileService>;
  let router: jasmine.SpyObj<Router>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;

  beforeEach(async () => {
    profileService = jasmine.createSpyObj<ProfileService>('ProfileService', ['getProfile', 'updateProfile']);
    router = jasmine.createSpyObj<Router>('Router', ['navigate']);
    snackBar = jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']);
    profileService.getProfile.and.returnValue(of({
      id_usuario: 1,
      nombres: 'Carlos',
      apellidos: 'Perez',
      correo: 'cliente@example.com',
      telefono: '70000000'
    }));

    TestBed.configureTestingModule({
      imports: [ProfileEditComponent, NoopAnimationsModule],
      providers: [
        { provide: ProfileService, useValue: profileService },
        { provide: Router, useValue: router },
        { provide: MatSnackBar, useValue: snackBar }
      ]
    }).overrideComponent(ProfileEditComponent, {
      set: { providers: [{ provide: MatSnackBar, useValue: snackBar }] }
    });

    await TestBed.compileComponents();
    fixture = TestBed.createComponent(ProfileEditComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('updates the editable profile fields', () => {
    profileService.updateProfile.and.returnValue(of({
      id_usuario: 1,
      nombres: 'Carlos Alberto',
      apellidos: 'Perez',
      correo: 'cliente@example.com',
      telefono: '79999999'
    }));
    component.profileForm.setValue({
      nombres: 'Carlos Alberto',
      apellidos: 'Perez',
      telefono: '79999999'
    });

    component.submit();

    expect(profileService.updateProfile).toHaveBeenCalledWith({
      nombres: 'Carlos Alberto',
      apellidos: 'Perez',
      telefono: '79999999'
    });
    expect(router.navigate).toHaveBeenCalledWith(['/profile/view']);
  });

  it('does not expose protected fields in the form', () => {
    expect(component.profileForm.contains('correo')).toBeFalse();
    expect(component.profileForm.contains('rol')).toBeFalse();
  });
});
