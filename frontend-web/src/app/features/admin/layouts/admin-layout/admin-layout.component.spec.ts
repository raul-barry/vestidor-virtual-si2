import { TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { provideRouter, RouterOutlet } from '@angular/router';
import { AdminLayoutComponent } from './admin-layout.component';
describe('AdminLayoutComponent', () => {
  it('keeps the nested route outlet without duplicating navigation', async () => {
    await TestBed.configureTestingModule({imports: [AdminLayoutComponent], providers: [provideRouter([])]}).compileComponents();
    const fixture = TestBed.createComponent(AdminLayoutComponent);
    fixture.detectChanges();
    expect(fixture.debugElement.query(By.directive(RouterOutlet))).not.toBeNull();
    expect(fixture.nativeElement.querySelector('nav')).toBeNull();
  });
});
