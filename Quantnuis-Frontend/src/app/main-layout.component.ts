import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive, Router, NavigationEnd } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthService } from './services/ec2/auth.service';
import { ThemeService } from './services/theme.service';
import { Observable, Subscription } from 'rxjs';
import { filter } from 'rxjs/operators';
import { FooterComponent } from './components/footer/footer.component';

@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, CommonModule, FooterComponent],
  template: `
    <div class="layout" [class.nav-open]="mobileMenuOpen">

      <!-- ===== MASTHEAD ===== -->
      <header class="masthead" role="banner">
        <div class="masthead-inner">

          <!-- Left: wordmark + affiliation -->
          <div class="masthead-brand">
            <a routerLink="/" class="wordmark" aria-label="Quantnuis — Accueil">Quantnuis</a>
            <span class="affiliation" aria-label="ENSTA Bretagne · Campus de Brest">
              ENSTA Bretagne · Campus de Brest
            </span>
          </div>

          <!-- Right: nav + actions -->
          <nav class="masthead-nav" id="main-nav" role="navigation" aria-label="Navigation principale">
            <a routerLink="/" routerLinkActive="active" [routerLinkActiveOptions]="{exact: true}" (click)="closeMobileMenu()">Démo</a>
            <a routerLink="/methodology" routerLinkActive="active" (click)="closeMobileMenu()">Méthodologie</a>
            <a routerLink="/about" routerLinkActive="active" (click)="closeMobileMenu()">À propos</a>
            <a href="https://github.com/ElMonstroDelBrest/Quantnuis-Web-Site" target="_blank" rel="noopener" class="nav-external">GitHub ↗</a>

            <ng-container *ngIf="currentUser$ | async">
              <a routerLink="/dashboard" routerLinkActive="active" (click)="closeMobileMenu()">Dashboard</a>
              <a routerLink="/annotation" routerLinkActive="active" (click)="closeMobileMenu()">Annotation</a>
              <a *ngIf="(currentUser$ | async)?.is_admin" routerLink="/admin" routerLinkActive="active" (click)="closeMobileMenu()" class="nav-admin">Admin</a>
            </ng-container>
          </nav>

          <!-- Right actions: theme toggle + user -->
          <div class="masthead-actions">
            <button
              type="button"
              class="theme-toggle"
              (click)="themeService.toggle()"
              [attr.aria-label]="themeService.theme() === 'dark' ? 'Passer en mode clair' : 'Passer en mode sombre'"
              [title]="themeService.theme() === 'dark' ? 'Mode clair' : 'Mode sombre'"
            >
              <svg *ngIf="themeService.theme() === 'dark'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <circle cx="12" cy="12" r="4"/>
                <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/>
              </svg>
              <svg *ngIf="themeService.theme() === 'light'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
              </svg>
            </button>

            <ng-container *ngIf="currentUser$ | async as user">
              <div class="user-profile">
                <div class="avatar" aria-hidden="true">{{ user.email?.[0]?.toUpperCase() }}</div>
                <span class="user-name">{{ user.email?.split('@')[0] }}</span>
              </div>
              <button (click)="logout()" class="btn-logout" aria-label="Déconnexion" title="Déconnexion">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                  <polyline points="16 17 21 12 16 7"/>
                  <line x1="21" y1="12" x2="9" y2="12"/>
                </svg>
              </button>
            </ng-container>

            <!-- Hamburger (mobile only) -->
            <button
              class="hamburger"
              (click)="toggleMobileMenu()"
              aria-label="Menu navigation"
              [attr.aria-expanded]="mobileMenuOpen"
              aria-controls="main-nav"
              type="button"
            >
              <span aria-hidden="true"></span>
              <span aria-hidden="true"></span>
              <span aria-hidden="true"></span>
            </button>
          </div>
        </div>

        <!-- Mobile nav dropdown -->
        <div class="mobile-nav" [class.open]="mobileMenuOpen" role="navigation" aria-label="Navigation mobile">
          <a routerLink="/" routerLinkActive="active" [routerLinkActiveOptions]="{exact: true}" (click)="closeMobileMenu()">Démo</a>
          <a routerLink="/methodology" routerLinkActive="active" (click)="closeMobileMenu()">Méthodologie</a>
          <a routerLink="/about" routerLinkActive="active" (click)="closeMobileMenu()">À propos</a>
          <a href="https://github.com/ElMonstroDelBrest/Quantnuis-Web-Site" target="_blank" rel="noopener" (click)="closeMobileMenu()">GitHub ↗</a>
          <ng-container *ngIf="currentUser$ | async">
            <a routerLink="/dashboard" routerLinkActive="active" (click)="closeMobileMenu()">Dashboard</a>
            <a routerLink="/annotation" routerLinkActive="active" (click)="closeMobileMenu()">Annotation</a>
          </ng-container>
        </div>
      </header>

      <!-- Click-outside overlay for mobile menu -->
      <div
        class="mobile-overlay"
        [class.visible]="mobileMenuOpen"
        (click)="closeMobileMenu()"
        aria-hidden="true"
      ></div>

      <!-- Main Content -->
      <main class="content-area">
        <router-outlet />
      </main>

      <app-footer></app-footer>
    </div>
  `,
  styles: [`
    :host { display: block; min-height: 100vh; }

    .layout {
      display: flex;
      flex-direction: column;
      min-height: 100vh;
    }

    /* ===== MASTHEAD ===== */
    .masthead {
      background: var(--bg-secondary);
      border-bottom: 1px solid var(--border-color);
      position: sticky;
      top: 0;
      z-index: 100;
    }

    .masthead-inner {
      display: flex;
      align-items: center;
      gap: 2rem;
      height: 64px;
      max-width: 1200px;
      margin: 0 auto;
      padding: 0 1.5rem;
    }

    /* Brand */
    .masthead-brand {
      display: flex;
      flex-direction: column;
      justify-content: center;
      flex-shrink: 0;
      gap: 0.1rem;
    }

    .wordmark {
      font-family: 'Inter', system-ui, sans-serif;
      font-weight: 700;
      font-size: 1.15rem;
      letter-spacing: -0.015em;
      color: var(--text-primary);
      text-decoration: none;
      line-height: 1.2;
    }
    .wordmark:hover { color: var(--text-primary); }

    .affiliation {
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 0.62rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--text-tertiary);
      line-height: 1;
      white-space: nowrap;
    }

    /* Nav */
    .masthead-nav {
      display: flex;
      align-items: center;
      gap: 0.25rem;
      flex: 1;
    }

    .masthead-nav a {
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--text-secondary);
      text-decoration: none;
      padding: 0.375rem 0.625rem;
      border-radius: var(--radius-sm);
      transition: color 0.15s ease, background 0.15s ease;
    }
    .masthead-nav a:hover { color: var(--text-primary); background: var(--bg-surface); }
    .masthead-nav a.active { color: var(--text-primary); }

    .masthead-nav .nav-external {
      color: var(--text-tertiary);
      font-size: 0.8rem;
    }
    .masthead-nav .nav-external:hover { color: var(--text-secondary); }

    .masthead-nav .nav-admin {
      color: var(--danger-light);
      font-size: 0.8rem;
    }

    /* Actions */
    .masthead-actions {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      flex-shrink: 0;
    }

    .theme-toggle {
      width: 34px; height: 34px;
      display: flex; align-items: center; justify-content: center;
      background: transparent;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      color: var(--text-tertiary);
      cursor: pointer;
      transition: color 0.15s ease, border-color 0.15s ease, background 0.15s ease;
      padding: 0;
    }
    .theme-toggle svg { width: 15px; height: 15px; }
    .theme-toggle:hover {
      color: var(--text-primary);
      border-color: var(--border-color-hover);
      background: var(--bg-surface);
    }

    .user-profile {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.25rem 0.625rem 0.25rem 0.375rem;
      background: var(--bg-surface);
      border-radius: var(--radius-pill);
      border: 1px solid var(--border-color);
    }

    .avatar {
      width: 26px; height: 26px;
      background: var(--accent-dark);
      color: var(--bg-page);
      border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      font-weight: 600; font-size: 0.72rem;
      font-family: 'Inter', system-ui, sans-serif;
    }

    .user-name {
      font-size: 0.8rem;
      font-weight: 500;
      color: var(--text-primary);
      font-family: 'Inter', system-ui, sans-serif;
    }

    .btn-logout {
      width: 34px; height: 34px;
      background: transparent;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      color: var(--text-tertiary);
      cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      transition: color 0.15s ease, border-color 0.15s ease;
    }
    .btn-logout svg { width: 15px; height: 15px; }
    .btn-logout:hover { border-color: rgba(239, 68, 68, 0.3); color: var(--danger); }

    /* Hamburger */
    .hamburger {
      display: none;
      flex-direction: column;
      justify-content: center;
      gap: 5px;
      width: 34px; height: 34px;
      background: transparent;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      cursor: pointer;
      padding: 8px;
    }
    .hamburger:hover { background: var(--bg-surface); }
    .hamburger span {
      display: block;
      width: 100%; height: 2px;
      background: var(--text-secondary);
      border-radius: 1px;
    }

    /* Mobile nav dropdown */
    .mobile-nav {
      display: none;
      flex-direction: column;
      background: var(--bg-secondary);
      border-top: 1px solid var(--border-color);
      padding: 0.5rem 1.5rem 0.75rem;
      gap: 0;
    }
    .mobile-nav.open { display: flex; }

    .mobile-nav a {
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 0.9rem;
      font-weight: 500;
      color: var(--text-secondary);
      text-decoration: none;
      padding: 0.6rem 0;
      border-bottom: 1px solid var(--border-color);
      transition: color 0.15s ease;
    }
    .mobile-nav a:last-child { border-bottom: none; }
    .mobile-nav a:hover { color: var(--text-primary); }
    .mobile-nav a.active { color: var(--text-primary); }

    /* Mobile overlay */
    .mobile-overlay {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.4);
      z-index: 99;
    }
    .mobile-overlay.visible { display: block; }

    /* ===== MAIN CONTENT ===== */
    .content-area {
      flex: 1;
    }

    /* ===== RESPONSIVE ===== */
    @media (max-width: 900px) {
      .masthead-nav { display: none; }
      .hamburger { display: flex; }
      .affiliation { display: none; }
    }

    @media (max-width: 768px) {
      .masthead-inner { height: 56px; padding: 0 1rem; gap: 1rem; }
      .user-name { display: none; }
      .user-profile { padding: 0.25rem 0.375rem; }
    }

    @media (max-width: 480px) {
      .masthead-inner { padding: 0 0.875rem; }
    }
  `]
})
export class MainLayoutComponent implements OnInit, OnDestroy {
  currentUser$: Observable<any>;
  mobileMenuOpen = false;
  themeService = inject(ThemeService);

  private routerSub!: Subscription;

  constructor(
    public authService: AuthService,
    private router: Router
  ) {
    this.currentUser$ = this.authService.currentUser$;
  }

  ngOnInit() {
    this.routerSub = this.router.events.pipe(
      filter((event): event is NavigationEnd => event instanceof NavigationEnd)
    ).subscribe(() => {
      this.closeMobileMenu();
    });
  }

  ngOnDestroy() {
    this.routerSub?.unsubscribe();
  }

  toggleMobileMenu() {
    this.mobileMenuOpen = !this.mobileMenuOpen;
  }

  closeMobileMenu() {
    this.mobileMenuOpen = false;
  }

  logout() {
    this.authService.logout();
  }
}
