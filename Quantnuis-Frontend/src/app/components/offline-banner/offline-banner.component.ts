import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { OfflineService } from '../../services/offline.service';
import { Subscription } from 'rxjs';
import { trigger, transition, style, animate } from '@angular/animations';

@Component({
  selector: 'app-offline-banner',
  standalone: true,
  imports: [CommonModule],
  animations: [
    trigger('slideDown', [
      transition(':enter', [
        style({ transform: 'translateY(-100%)', opacity: 0 }),
        animate('300ms var(--ease-out-expo)',
          style({ transform: 'translateY(0)', opacity: 1 }))
      ]),
      transition(':leave', [
        animate('200ms var(--ease-out-expo)',
          style({ transform: 'translateY(-100%)', opacity: 0 }))
      ])
    ])
  ],
  template: `
    <div class="offline-banner" *ngIf="isOffline" [@slideDown]>
      <div class="banner-content">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <line x1="1" y1="1" x2="23" y2="23"/>
          <path d="M16.72 11.06A10.94 10.94 0 0 1 19 12.55"/>
          <path d="M5 12.55a10.94 10.94 0 0 1 5.17-2.39"/>
          <path d="M10.71 5.05A16 16 0 0 1 22.58 9"/>
          <path d="M1.42 9a15.91 15.91 0 0 1 4.7-2.88"/>
          <path d="M8.53 16.11a6 6 0 0 1 6.95 0"/>
          <line x1="12" y1="20" x2="12.01" y2="20"/>
        </svg>
        <span>Vous êtes hors ligne</span>
        <span class="separator">•</span>
        <span class="hint">Vérifiez votre connexion internet</span>
      </div>
    </div>
  `,
  styles: [`
    .offline-banner {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      z-index: 10000;
      background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
      color: white;
      padding: 0.75rem 1rem;
      box-shadow: var(--shadow-md);
    }

    .banner-content {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 0.75rem;
      font-size: 0.875rem;
      font-weight: 500;
    }

    .banner-content svg {
      width: 18px;
      height: 18px;
      flex-shrink: 0;
    }

    .separator {
      opacity: 0.5;
    }

    .hint {
      opacity: 0.85;
      font-weight: 400;
    }

    @media (max-width: 600px) {
      .banner-content {
        font-size: 0.8rem;
        gap: 0.5rem;
      }

      .hint {
        display: none;
      }

      .separator {
        display: none;
      }
    }
  `]
})
export class OfflineBannerComponent implements OnInit, OnDestroy {
  isOffline = false;
  private subscription?: Subscription;

  constructor(private offlineService: OfflineService) {}

  ngOnInit(): void {
    this.isOffline = this.offlineService.isOffline();

    this.subscription = this.offlineService.getOnlineStatus()
      .subscribe(isOnline => {
        this.isOffline = !isOnline;
      });
  }

  ngOnDestroy(): void {
    this.subscription?.unsubscribe();
  }
}
