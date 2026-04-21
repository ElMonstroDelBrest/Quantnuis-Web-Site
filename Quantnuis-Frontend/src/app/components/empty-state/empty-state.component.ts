import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

export type EmptyStateType = 'no-data' | 'no-results' | 'error' | 'success' | 'audio';

@Component({
  selector: 'app-empty-state',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="empty-state" [class]="'empty-state-' + type">
      <div class="illustration">
        <ng-container [ngSwitch]="type">
          <!-- No Data -->
          <svg *ngSwitchCase="'no-data'" viewBox="0 0 120 120" fill="none" aria-hidden="true">
            <circle cx="60" cy="60" r="50" fill="url(#grad1)" opacity="0.1"/>
            <path d="M40 50h40M40 60h30M40 70h35" stroke="currentColor" stroke-width="3" stroke-linecap="round" opacity="0.3"/>
            <circle cx="80" cy="75" r="15" fill="url(#grad1)" opacity="0.2"/>
            <path d="M75 75l10 10M90 80l5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <defs>
              <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#6366f1"/>
                <stop offset="100%" stop-color="#8b5cf6"/>
              </linearGradient>
            </defs>
          </svg>

          <!-- Audio/Analysis -->
          <svg *ngSwitchCase="'audio'" viewBox="0 0 120 120" fill="none" aria-hidden="true">
            <circle cx="60" cy="60" r="50" fill="url(#grad2)" opacity="0.1"/>
            <rect x="35" y="45" width="8" height="30" rx="4" fill="currentColor" opacity="0.2"/>
            <rect x="48" y="35" width="8" height="50" rx="4" fill="currentColor" opacity="0.3"/>
            <rect x="61" y="40" width="8" height="40" rx="4" fill="url(#grad2)" opacity="0.5"/>
            <rect x="74" y="50" width="8" height="20" rx="4" fill="currentColor" opacity="0.2"/>
            <circle cx="60" cy="90" r="8" fill="url(#grad2)" opacity="0.3"/>
            <path d="M56 90l4 4 8-8" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <defs>
              <linearGradient id="grad2" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#6366f1"/>
                <stop offset="100%" stop-color="#8b5cf6"/>
              </linearGradient>
            </defs>
          </svg>

          <!-- No Results -->
          <svg *ngSwitchCase="'no-results'" viewBox="0 0 120 120" fill="none" aria-hidden="true">
            <circle cx="60" cy="60" r="50" fill="url(#grad3)" opacity="0.1"/>
            <circle cx="55" cy="55" r="20" stroke="currentColor" stroke-width="3" opacity="0.3"/>
            <path d="M70 70l15 15" stroke="currentColor" stroke-width="3" stroke-linecap="round" opacity="0.3"/>
            <path d="M48 55h14M55 48v14" stroke="currentColor" stroke-width="2" stroke-linecap="round" opacity="0.2"/>
            <defs>
              <linearGradient id="grad3" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#f59e0b"/>
                <stop offset="100%" stop-color="#d97706"/>
              </linearGradient>
            </defs>
          </svg>

          <!-- Error -->
          <svg *ngSwitchCase="'error'" viewBox="0 0 120 120" fill="none" aria-hidden="true">
            <circle cx="60" cy="60" r="50" fill="#ef4444" opacity="0.1"/>
            <circle cx="60" cy="60" r="30" stroke="#ef4444" stroke-width="3" opacity="0.3"/>
            <path d="M50 50l20 20M70 50l-20 20" stroke="#ef4444" stroke-width="3" stroke-linecap="round"/>
          </svg>

          <!-- Success -->
          <svg *ngSwitchCase="'success'" viewBox="0 0 120 120" fill="none" aria-hidden="true">
            <circle cx="60" cy="60" r="50" fill="#10b981" opacity="0.1"/>
            <circle cx="60" cy="60" r="30" stroke="#10b981" stroke-width="3" opacity="0.3"/>
            <path d="M45 60l10 10 20-20" stroke="#10b981" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </ng-container>
      </div>

      <div class="content">
        <h3 class="title">{{ title }}</h3>
        <p class="message">{{ message }}</p>
      </div>

      <div class="actions" *ngIf="actionLabel">
        <a *ngIf="actionLink" [routerLink]="actionLink" class="btn-action">
          {{ actionLabel }}
        </a>
        <button *ngIf="!actionLink" class="btn-action" (click)="onAction()">
          {{ actionLabel }}
        </button>
      </div>
    </div>
  `,
  styles: [`
    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 3rem 2rem;
      text-align: center;
    }

    .illustration {
      width: 120px;
      height: 120px;
      margin-bottom: 1.5rem;
      color: var(--accent);
      animation: float 3s ease-in-out infinite;
    }

    .illustration svg {
      width: 100%;
      height: 100%;
    }

    .content {
      max-width: 320px;
    }

    .title {
      font-size: 1.25rem;
      font-weight: 600;
      color: white;
      margin-bottom: 0.5rem;
    }

    .message {
      font-size: 0.9rem;
      color: rgba(255, 255, 255, 0.5);
      line-height: 1.5;
    }

    .actions {
      margin-top: 1.5rem;
    }

    .btn-action {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.75rem 1.5rem;
      background: var(--accent-dark);
      color: white;
      font-weight: 600;
      font-size: 0.9rem;
      border: none;
      border-radius: 10px;
      cursor: pointer;
      text-decoration: none;
      transition: all 0.3s var(--ease-out-expo);
      box-shadow: var(--shadow-btn);
    }

    .btn-action:hover {
      transform: translateY(-2px);
      box-shadow: var(--shadow-btn-hover);
    }

    .empty-state-error .illustration {
      color: var(--danger);
    }

    .empty-state-success .illustration {
      color: var(--success);
    }

    .empty-state-no-results .illustration {
      color: var(--warning);
    }

    @media (max-width: 600px) {
      .empty-state {
        padding: 2rem 1rem;
      }

      .illustration {
        width: 100px;
        height: 100px;
      }

      .title {
        font-size: 1.1rem;
      }

      .message {
        font-size: 0.85rem;
      }
    }
  `]
})
export class EmptyStateComponent {
  @Input() type: EmptyStateType = 'no-data';
  @Input() title = 'Aucune donnée';
  @Input() message = 'Il n\'y a rien à afficher pour le moment.';
  @Input() actionLabel?: string;
  @Input() actionLink?: string;
  @Input() actionCallback?: () => void;

  onAction(): void {
    this.actionCallback?.();
  }
}
