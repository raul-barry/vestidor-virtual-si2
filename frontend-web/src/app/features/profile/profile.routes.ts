import { Routes } from '@angular/router';

export const PROFILE_ROUTES: Routes = [
  {
    path: 'view',
    loadComponent: () => import('./pages/profile-view/profile-view.component').then(
      (component) => component.ProfileViewComponent
    )
  },
  {
    path: 'edit',
    loadComponent: () => import('./pages/profile-edit/profile-edit.component').then(
      (component) => component.ProfileEditComponent
    )
  },
  { path: 'preferences', loadComponent: () => import('./pages/preferences/preferences.component').then(c => c.PreferencesComponent) },
  { path: 'body', loadComponent: () => import('./pages/body-profile/body-profile.component').then(c => c.BodyProfileComponent) },
  { path: '', pathMatch: 'full', redirectTo: 'view' }
];
