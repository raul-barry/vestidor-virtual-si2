import { ComponentFixture, TestBed } from '@angular/core/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { AdminSidebarComponent } from './admin-sidebar.component';

describe('AdminSidebarComponent', () => {
  let fixture: ComponentFixture<AdminSidebarComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AdminSidebarComponent, RouterTestingModule, NoopAnimationsModule]
    }).compileComponents();
    fixture = TestBed.createComponent(AdminSidebarComponent);
    fixture.detectChanges();
  });

  it('shows administrative navigation options', () => {
    const content = fixture.nativeElement.textContent;
    expect(content).toContain('Dashboard');
    expect(content).toContain('Productos');
    expect(content).toContain('Inventario');
    expect(content).toContain('Reportes');
  });
});
