import { Component, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../services/ec2/auth.service';
import { NotificationService } from '../services/notification.service';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  template: `
    <div class="auth-page">
      <div class="auth-container">
        <div class="auth-card">
          <div class="auth-header">
            <div class="auth-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                <circle cx="8.5" cy="7" r="4"/>
                <line x1="20" y1="8" x2="20" y2="14"/>
                <line x1="23" y1="11" x2="17" y2="11"/>
              </svg>
            </div>
            <h2>Créer un compte</h2>
            <p>Rejoignez Quantnuis pour suivre vos analyses</p>
          </div>

          <form [formGroup]="registerForm" (ngSubmit)="onSubmit()">
            <div class="form-group">
              <label for="email">Email</label>
              <div class="input-wrapper">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
                  <polyline points="22,6 12,13 2,6"/>
                </svg>
                <input type="email" id="email" formControlName="email" placeholder="exemple@email.com">
              </div>
              <div class="field-error" *ngIf="registerForm.get('email')?.touched && registerForm.get('email')?.invalid">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <circle cx="12" cy="12" r="10"/>
                  <line x1="15" y1="9" x2="9" y2="15"/>
                  <line x1="9" y1="9" x2="15" y2="15"/>
                </svg>
                Email valide requis
              </div>
            </div>

            <div class="form-group">
              <label for="password">Mot de passe</label>
              <div class="input-wrapper">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                  <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                </svg>
                <input [type]="showPassword ? 'text' : 'password'" id="password" formControlName="password" placeholder="Min. 8 car., maj, min, chiffre, special">
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
              <div class="field-error" *ngIf="registerForm.get('password')?.touched && registerForm.get('password')?.invalid">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <circle cx="12" cy="12" r="10"/>
                  <line x1="15" y1="9" x2="9" y2="15"/>
                  <line x1="9" y1="9" x2="15" y2="15"/>
                </svg>
                8 car. min avec majuscule, minuscule, chiffre et special (@$!%*?&)
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

            <button type="submit" class="btn-submit" [disabled]="registerForm.invalid || isLoading">
              <span *ngIf="!isLoading">Créer mon compte</span>
              <span *ngIf="isLoading" class="loading">
                <span class="spinner"></span>
                Création...
              </span>
            </button>
          </form>

          <div class="auth-footer">
            <p>Déjà un compte ? <a routerLink="/login">Se connecter</a></p>
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
      animation: fadeInUp 0.5s var(--ease-out-expo);
      position: relative;
    }

    .auth-header {
      text-align: center;
      margin-bottom: 2rem;
      position: relative;
      z-index: 1;
    }

    .auth-icon {
      width: 56px;
      height: 56px;
      background: var(--accent-dark);
      border-radius: var(--radius-lg);
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 1.5rem;
    }

    .auth-icon svg {
      width: 24px;
      height: 24px;
      color: var(--bg-page);
    }

    .auth-header h2 {
      font-size: 1.6rem;
      font-weight: 600;
      color: var(--text-primary);
      margin-bottom: 0.5rem;
    }

    .auth-header p {
      color: var(--text-secondary);
      font-size: 0.925rem;
    }

    .form-group {
      margin-bottom: 1.5rem;
      position: relative;
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
      width: 16px;
      height: 16px;
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
      padding: 0.875rem 2.75rem 0.875rem 2.75rem;
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
      width: 16px;
      height: 16px;
      color: var(--text-tertiary);
      transition: color 0.2s ease;
    }

    .toggle-password:hover svg {
      color: var(--text-secondary);
    }

    .input-wrapper input::placeholder {
      color: var(--text-tertiary);
    }

    .input-wrapper input:focus {
      outline: none;
      border-color: var(--accent);
      box-shadow: 0 0 0 3px var(--accent-glow);
    }

    .field-error {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      margin-top: 0.5rem;
      font-size: 0.8rem;
      color: var(--danger-lighter);
      animation: fadeInUp 0.3s ease-out;
    }

    .field-error svg {
      width: 14px;
      height: 14px;
    }

    .error-message {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.875rem 1rem;
      background: var(--danger-glow);
      border: 1px solid var(--danger-glow);
      border-radius: var(--radius-md);
      color: var(--danger);
      font-size: 0.875rem;
      margin-bottom: 1.5rem;
      animation: shakeX 0.5s ease-out;
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

    /* Reduced motion */
    @media (prefers-reduced-motion: reduce) {
      .auth-card {
        animation: none;
      }
      .error-message,
      .field-error {
        animation: none;
      }
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
export class RegisterComponent {
  registerForm: FormGroup;
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
    this.registerForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [
        Validators.required,
        Validators.minLength(8),
        Validators.pattern(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/)
      ]]
    });
  }

  togglePassword() {
    this.showPassword = !this.showPassword;
  }

  onSubmit() {
    if (this.registerForm.valid) {
      this.isLoading = true;
      this.error = '';

      this.authService.register(this.registerForm.value).subscribe({
        next: () => {
          this.notificationService.success('Compte créé !', 'Bienvenue sur Quantnuis !');
          this.authService.login(this.registerForm.value).subscribe(() => {
            this.router.navigate(['/dashboard']);
          });
        },
        error: (err: any) => {
          this.isLoading = false;
          if (err.status === 400) {
            const detail = err.error?.detail;
            if (detail === "Email already registered") {
              this.error = "Cet email est déjà utilisé.";
            } else {
              this.error = detail || "Données invalides.";
            }
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
