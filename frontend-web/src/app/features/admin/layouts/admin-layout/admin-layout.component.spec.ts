import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { RouterOutlet } from '@angular/router';
import { RouterTestingModule } from '@angular/router/testing';
import { of } from 'rxjs';
import { AuthService } from '../../../auth/services/auth.service';
import { AdminHeaderComponent } from '../../components/admin-header/admin-header.component';
import { AdminSidebarComponent } from '../../components/admin-sidebar/admin-sidebar.component';
import { AdminLayoutComponent } from './admin-layout.component';

describe('AdminLayoutComponent', () => {
  let fixture: ComponentFixture<AdminLayoutComponent>;

  beforeEach(async () => {
    const authService = jasmine.createSpyObj<AuthService>('AuthService', ['logout']);
    authService.logout.and.returnValue(of({ message: 'ok' }));
    await TestBed.configureTestingModule({
      imports: [AdminLayoutComponent, NoopAnimationsModule, RouterTestingModule],
      providers: [{ provide: AuthService, useValue: authService }]
    }).compileComponents();
    fixture = TestBed.createComponent(AdminLayoutComponent);
    fixture.detectChanges();
  });

  it('renders header, sidebar and content outlet', () => {
    expect(fixture.debugElement.query(By.directive(AdminHeaderComponent))).not.toBeNull();
    expect(fixture.debugElement.query(By.directive(AdminSidebarComponent))).not.toBeNull();
    expect(fixture.debugElement.query(By.directive(RouterOutlet))).not.toBeNull();
  });
});
