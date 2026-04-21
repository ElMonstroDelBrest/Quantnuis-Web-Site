import { Routes } from '@angular/router';
import { MainLayoutComponent } from './main-layout.component';
import { inject } from '@angular/core';
import { AuthService } from './services/ec2/auth.service';
import { Router } from '@angular/router';

const authGuard = () => {
  const authService = inject(AuthService);
  const router = inject(Router);
  return authService.isAuthenticated() ? true : router.parseUrl('/login');
};

const adminGuard = () => {
  const authService = inject(AuthService);
  const router = inject(Router);
  if (!authService.isAuthenticated()) {
    return router.parseUrl('/login');
  }
  return authService.isAdmin() ? true : router.parseUrl('/dashboard');
};

export const routes: Routes = [
  // Pages Auth (SANS le MainLayout)
  {
    path: 'login',
    loadComponent: () => import('./pages/login.component').then(m => m.LoginComponent)
  },
  {
    path: 'register',
    loadComponent: () => import('./pages/register.component').then(m => m.RegisterComponent)
  },

  // Pages App (AVEC le MainLayout)
  {
    path: '',
    component: MainLayoutComponent,
    children: [
      {
        path: '',
        loadComponent: () => import('./pages/home.component').then(m => m.HomeComponent)
      },
      {
        path: 'about',
        loadComponent: () => import('./pages/about.component').then(m => m.AboutComponent)
      },
      {
        path: 'methodology',
        loadComponent: () => import('./pages/methodology.component').then(m => m.MethodologyComponent)
      },
      {
        path: 'legal/terms',
        loadComponent: () => import('./pages/legal.component').then(m => m.LegalComponent),
        data: { section: 'terms' }
      },
      {
        path: 'legal/privacy',
        loadComponent: () => import('./pages/legal.component').then(m => m.LegalComponent),
        data: { section: 'privacy' }
      },
      {
        path: 'legal/mentions',
        loadComponent: () => import('./pages/legal.component').then(m => m.LegalComponent),
        data: { section: 'mentions' }
      },
      {
        path: 'dashboard',
        canActivate: [authGuard],
        loadComponent: () => import('./pages/dashboard.component').then(m => m.DashboardComponent)
      },
      {
        path: 'annotation',
        canActivate: [authGuard],
        loadComponent: () => import('./pages/annotation.component').then(m => m.AnnotationComponent)
      },
      {
        path: 'admin',
        canActivate: [adminGuard],
        loadComponent: () => import('./pages/admin.component').then(m => m.AdminComponent)
      },
    ]
  },

  {
    path: '**',
    loadComponent: () => import('./pages/not-found.component').then(m => m.NotFoundComponent)
  }
];
