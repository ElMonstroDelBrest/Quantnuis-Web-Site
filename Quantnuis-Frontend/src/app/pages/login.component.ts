import { Component, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../services/ec2/auth.service';
import { NotificationService } from '../services/notification.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  template: `
    <div class="auth-page">
      <div class="auth-container">
        <div class="auth-card">
          <div class="auth-header">
            <div class="auth-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/>
                <polyline points="10 17 15 12 10 7"/>
                <line x1="15" y1="12" x2="3" y2="12"/>
              </svg>
            </div>
            <h2>Connexion</h2>
            <p>Accédez à votre tableau de bord</p>
          </div>

          <form [formGroup]="loginForm" (ngSubmit)="onSubmit()">
            <div class="form-group">
              <label for="email">Email</label>
              <div class="input-wrapper">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
                  <polyline points="22,6 12,13 2,6"/>
                </svg>
                <input type="email" id="email" formControlName="email" placeholder="exemple@email.com">
              </div>
            </div>

            <div class="form-group">
              <label for="password">Mot de passe</label>
              <div class="input-wrapper">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                  <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                </svg>
                <input [type]="showPassword ? 'text' : 'password'" id="password" formControlName="password" placeholder="Votre mot de passe">
                <button type="button" class="toggle-password" (click)="togglePassword()" tabindex="-1">
                  <svg *ngIf="!showPassword" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                    <circle cx="12" cy="12" r="3"/>
                  </svg>
                  <svg *ngIf="showPassword" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                    <line x1="1" y1="1" x2="23" y2="23"/>
                  </svg>
                </button>
              </div>
            </div>

            <div class="error-message" *ngIf="error">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8" x2="12" y2="12"/>
                <line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
              {{ error }}
            </div>

            <button type="submit" class="btn-submit" [disabled]="loginForm.invalid || isLoading">
              <span *ngIf="!isLoading">Se connecter</span>
              <span *ngIf="isLoading" class="loading">
                <span class="spinner"></span>
                Connexion...
              </span>
            </button>
          </form>

          <div class="auth-footer">
            <p>Pas encore de compte ? <a routerLink="/register">S'inscrire</a></p>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .auth-page {
      min-height: calc(100vh - 72px);
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 2rem;
    }

    .auth-container {
      width: 100%;
      max-width: 420px;
    }

    .auth-card {
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-xl);
      padding: 2.5rem;
      position: relative;
    }

    .auth-header {
      text-align: center;
      margin-bottom: 2rem;
      position: relative;
      z-index: 1;
    }

    .auth-icon {
      width: 64px;
      height: 64px;
      background: var(--accent-dark);
      border-radius: var(--radius-xl);
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 1.5rem;
      transition: all 0.3s var(--ease-out-expo);
      cursor: pointer;
    }

    .auth-icon svg {
      width: 28px;
      height: 28px;
      color: var(--bg-page);
    }

    .auth-header h2 {
      font-size: 1.75rem;
      font-weight: 600;
      color: var(--text-primary);
      margin-bottom: 0.5rem;
    }

    .auth-header p {
      color: var(--text-secondary);
      font-size: 0.95rem;
    }

    .form-group {
      margin-bottom: 1.5rem;
      position: relative;
      z-index: 1;
    }

    label {
      display: block;
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--text-secondary);
      margin-bottom: 0.5rem;
    }

    .input-wrapper {
      position: relative;
    }

    .input-wrapper svg {
      position: absolute;
      left: 1rem;
      top: 50%;
      transform: translateY(-50%);
      width: 18px;
      height: 18px;
      color: var(--text-tertiary);
      pointer-events: none;
      transition: color 0.2s ease;
    }

    .input-wrapper:focus-within svg {
      color: var(--accent);
      transform: translateY(-50%);
    }

    .input-wrapper input {
      width: 100%;
      padding: 0.875rem 2.75rem 0.875rem 3rem;
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      color: var(--text-primary);
      font-size: 0.95rem;
      transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }

    .input-wrapper input[type="email"] {
      padding-right: 1rem;
    }

    .input-wrapper input::placeholder {
      color: var(--text-tertiary);
    }

    .input-wrapper input:focus {
      outline: none;
      border-color: var(--accent);
      box-shadow: 0 0 0 3px var(--accent-glow);
    }

    .toggle-password {
      position: absolute;
      right: 0.75rem;
      top: 50%;
      transform: translateY(-50%);
      background: none;
      border: none;
      padding: 0.25rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .toggle-password svg {
      position: static;
      transform: none;
      width: 18px;
      height: 18px;
      color: var(--text-tertiary);
      transition: color 0.2s ease;
    }

    .toggle-password:hover svg {
      color: var(--text-secondary);
    }

    .forgot-password {
      text-align: right;
      margin-top: 0.5rem;
    }

    .forgot-link {
      font-size: 0.8rem;
      color: var(--text-tertiary);
      text-decoration: none;
      transition: color 0.2s ease;
    }

    .forgot-link:hover {
      color: var(--accent-light);
    }

    .error-message {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.875rem 1rem;
      background: rgba(239, 68, 68, 0.1);
      border: 1px solid rgba(239, 68, 68, 0.3);
      border-radius: var(--radius-md);
      color: var(--danger-lighter);
      font-size: 0.875rem;
      margin-bottom: 1.5rem;
      position: relative;
      z-index: 1;
    }

    .error-message svg {
      width: 18px;
      height: 18px;
      flex-shrink: 0;
    }

    .btn-submit {
      width: 100%;
      padding: 1rem;
      background: var(--accent);
      border: none;
      border-radius: var(--radius-md);
      color: var(--bg-page);
      font-size: 1rem;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.2s ease;
      position: relative;
      z-index: 1;
      font-family: inherit;
    }

    .btn-submit:hover:not(:disabled) {
      background: var(--accent-hover);
    }

    .btn-submit:disabled {
      opacity: 0.55;
      cursor: not-allowed;
    }

    .loading {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
    }

    .spinner {
      width: 16px;
      height: 16px;
      border: 2px solid var(--border-color-hover);
      border-top-color: var(--bg-page);
      border-radius: 50%;
      animation: spin 1s linear infinite;
    }

    .auth-footer {
      margin-top: 2rem;
      text-align: center;
      padding-top: 1.5rem;
      border-top: 1px solid var(--border-color);
      position: relative;
      z-index: 1;
    }

    .auth-footer p {
      color: var(--text-secondary);
      font-size: 0.9rem;
    }

    .auth-footer a {
      color: var(--accent);
      font-weight: 500;
      text-decoration: none;
      transition: color 0.15s ease;
    }

    .auth-footer a:hover {
      color: var(--accent-hover);
    }

    /* Responsive */
    @media (max-width: 600px) {
      .auth-page {
        padding: 1rem;
        min-height: calc(100vh - 64px);
      }

      .auth-card {
        padding: 1.75rem;
        border-radius: var(--radius-xl);
      }

      .auth-icon {
        width: 56px;
        height: 56px;
        border-radius: var(--radius-lg);
        margin-bottom: 1.25rem;
      }

      .auth-icon svg {
        width: 24px;
        height: 24px;
      }

      .auth-header {
        margin-bottom: 1.5rem;
      }

      .auth-header h2 {
        font-size: 1.5rem;
      }

      .auth-header p {
        font-size: 0.875rem;
      }

      .form-group {
        margin-bottom: 1.25rem;
      }

      label {
        font-size: 0.8rem;
      }

      .input-wrapper input {
        padding: 0.75rem 0.875rem 0.75rem 2.75rem;
        font-size: 0.9rem;
        border-radius: 10px;
      }

      .btn-submit {
        padding: 0.875rem;
        font-size: 0.9rem;
        border-radius: 10px;
      }

      .auth-footer {
        margin-top: 1.5rem;
        padding-top: 1.25rem;
      }

      .auth-footer p {
        font-size: 0.85rem;
      }
    }

    @media (max-width: 400px) {
      .auth-card {
        padding: 1.5rem;
      }
    }
  `]
})
export class LoginComponent {
  loginForm: FormGroup;
  isLoading = false;
  error = '';
  showPassword = false;

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private router: Router,
    private cdr: ChangeDetectorRef,
    private notificationService: NotificationService
  ) {
    this.loginForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', Validators.required]
    });
  }

  togglePassword() {
    this.showPassword = !this.showPassword;
  }

  onSubmit() {
    if (this.loginForm.valid) {
      this.isLoading = true;
      this.error = '';
      
      this.authService.login(this.loginForm.value).subscribe({
        next: () => {
          this.notificationService.success('Connexion réussie', 'Bienvenue sur Quantnuis !');
          this.router.navigate(['/dashboard']);
        },
        error: (err: any) => {
          this.isLoading = false;
          if (err.status === 401) {
            this.error = "Email ou mot de passe incorrect.";
          } else if (err.status === 0) {
            this.error = "Impossible de contacter le serveur.";
          } else {
            this.error = err.error?.detail || "Une erreur est survenue.";
          }
          this.cdr.detectChanges();
        }
      });
    }
  }
}
