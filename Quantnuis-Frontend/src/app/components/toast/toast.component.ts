import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NotificationService, Notification } from '../../services/notification.service';
import { Subscription } from 'rxjs';
import { trigger, transition, style, animate, query, stagger } from '@angular/animations';

@Component({
  selector: 'app-toast',
  standalone: true,
  imports: [CommonModule],
  animations: [
    trigger('toastAnimation', [
      transition(':enter', [
        style({ opacity: 0, transform: 'translateX(100%) scale(0.95)' }),
        animate('300ms var(--ease-out-expo)',
          style({ opacity: 1, transform: 'translateX(0) scale(1)' }))
      ]),
      transition(':leave', [
        animate('200ms var(--ease-out-expo)',
          style({ opacity: 0, transform: 'translateX(100%) scale(0.95)' }))
      ])
    ])
  ],
  template: `
    <div class="toast-container" role="status" aria-live="polite">
      <div
        *ngFor="let notification of notifications; trackBy: trackById"
        class="toast"
        [class.toast-success]="notification.type === 'success'"
        [class.toast-error]="notification.type === 'error'"
        [class.toast-warning]="notification.type === 'warning'"
        [class.toast-info]="notification.type === 'info'"
        [@toastAnimation]
      >
        <div class="toast-icon">
          <ng-container [ngSwitch]="notification.type">
            <svg *ngSwitchCase="'success'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
              <polyline points="22 4 12 14.01 9 11.01"/>
            </svg>
            <svg *ngSwitchCase="'error'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <circle cx="12" cy="12" r="10"/>
              <line x1="15" y1="9" x2="9" y2="15"/>
              <line x1="9" y1="9" x2="15" y2="15"/>
            </svg>
            <svg *ngSwitchCase="'warning'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
              <line x1="12" y1="9" x2="12" y2="13"/>
              <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            <svg *ngSwitchCase="'info'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="16" x2="12" y2="12"/>
              <line x1="12" y1="8" x2="12.01" y2="8"/>
            </svg>
          </ng-container>
        </div>

        <div class="toast-content">
          <div class="toast-title">{{ notification.title }}</div>
          <div class="toast-message" *ngIf="notification.message">{{ notification.message }}</div>
        </div>

        <button
          *ngIf="notification.action"
          class="toast-action"
          (click)="onAction(notification)"
        >
          {{ notification.action.label }}
        </button>

        <button class="toast-close" (click)="dismiss(notification.id)" aria-label="Fermer la notification">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
    </div>
  `,
  styles: [`
    .toast-container {
      position: fixed;
      top: 1rem;
      right: 1rem;
      z-index: 9999;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
      max-width: 420px;
      width: calc(100vw - 2rem);
      pointer-events: none;
    }

    .toast {
      display: flex;
      align-items: flex-start;
      gap: 0.875rem;
      padding: 1rem 1.25rem;
      background: rgba(15, 15, 35, 0.95);
      backdrop-filter: blur(20px);
      border-radius: var(--radius-md);
      border: 1px solid rgba(255, 255, 255, 0.1);
      box-shadow: var(--shadow-lg);
      pointer-events: auto;
    }

    .toast-success {
      border-left: 3px solid var(--success);
    }

    .toast-success .toast-icon {
      color: var(--success);
      background: rgba(16, 185, 129, 0.1);
    }

    .toast-error {
      border-left: 3px solid #ef4444;
    }

    .toast-error .toast-icon {
      color: var(--danger);
      background: rgba(239, 68, 68, 0.1);
    }

    .toast-warning {
      border-left: 3px solid #f59e0b;
    }

    .toast-warning .toast-icon {
      color: var(--warning);
      background: rgba(245, 158, 11, 0.1);
    }

    .toast-info {
      border-left: 3px solid #6366f1;
    }

    .toast-info .toast-icon {
      color: var(--accent);
      background: rgba(99, 102, 241, 0.1);
    }

    .toast-icon {
      flex-shrink: 0;
      width: 36px;
      height: 36px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .toast-icon svg {
      width: 20px;
      height: 20px;
    }

    .toast-content {
      flex: 1;
      min-width: 0;
    }

    .toast-title {
      font-weight: 600;
      font-size: 0.9rem;
      color: white;
      line-height: 1.4;
    }

    .toast-message {
      font-size: 0.8rem;
      color: rgba(255, 255, 255, 0.6);
      margin-top: 0.25rem;
      line-height: 1.5;
    }

    .toast-action {
      flex-shrink: 0;
      padding: 0.5rem 1rem;
      background: rgba(99, 102, 241, 0.2);
      border: 1px solid rgba(99, 102, 241, 0.3);
      border-radius: 8px;
      color: var(--accent-light);
      font-size: 0.8rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }

    .toast-action:hover {
      background: rgba(99, 102, 241, 0.3);
      border-color: rgba(99, 102, 241, 0.5);
    }

    .toast-close {
      flex-shrink: 0;
      width: 28px;
      height: 28px;
      background: transparent;
      border: none;
      border-radius: 6px;
      color: rgba(255, 255, 255, 0.4);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s;
      margin: -0.25rem -0.5rem -0.25rem 0;
    }

    .toast-close:hover {
      background: rgba(255, 255, 255, 0.1);
      color: rgba(255, 255, 255, 0.8);
    }

    .toast-close svg {
      width: 16px;
      height: 16px;
    }

    @media (max-width: 480px) {
      .toast-container {
        top: auto;
        bottom: 1rem;
        left: 1rem;
        right: 1rem;
        max-width: none;
        width: auto;
      }

      .toast {
        padding: 0.875rem 1rem;
      }
    }
  `]
})
export class ToastComponent implements OnInit, OnDestroy {
  notifications: Notification[] = [];
  private subscription?: Subscription;

  constructor(private notificationService: NotificationService) {}

  ngOnInit(): void {
    this.subscription = this.notificationService.getNotifications()
      .subscribe(notifications => {
        this.notifications = notifications;
      });
  }

  ngOnDestroy(): void {
    this.subscription?.unsubscribe();
  }

  dismiss(id: string): void {
    this.notificationService.dismiss(id);
  }

  onAction(notification: Notification): void {
    notification.action?.callback();
    this.dismiss(notification.id);
  }

  trackById(index: number, notification: Notification): string {
    return notification.id;
  }
}
