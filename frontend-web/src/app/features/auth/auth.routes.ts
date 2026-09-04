import { Routes } from '@angular/router';

export const AUTH_ROUTES: Routes = [
  {
    path: 'login',
    loadComponent: () => import('./pages/login/login.component').then((component) => component.LoginComponent)
  },
  {
    path: 'register',
    loadComponent: () => import('./pages/register/register.component').then((component) => component.RegisterComponent)
  },
  {
    path: 'password-reset',
    loadComponent: () => import('./pages/password-reset-request/password-reset-request.component').then(
      (component) => component.PasswordResetRequestComponent
    )
  },
  {
    path: 'password-reset/confirm',
    loadComponent: () => import('./pages/password-reset-confirm/password-reset-confirm.component').then(
      (component) => component.PasswordResetConfirmComponent
    )
  },
  { path: '', pathMatch: 'full', redirectTo: 'login' }
];
