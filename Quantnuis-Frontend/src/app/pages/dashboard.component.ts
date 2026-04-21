import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuthService } from '../services/ec2/auth.service';
import { DashboardService, DashboardData } from '../services/dashboard.service';
import { AudioReviewService, AudioReview, AudioReviewStats, ReviewPageData } from '../services/audio-review.service';
import { RouterLink } from '@angular/router';
import { Observable, BehaviorSubject, switchMap, catchError, of, tap, combineLatest } from 'rxjs';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="dashboard">
      <!-- Hero Header -->
      <header class="dash-header">
        <div class="header-content">
          <h1>Tableau de <span class="gradient-text">bord</span></h1>
          <p class="welcome" *ngIf="user$ | async as user">
            Bienvenue, <span class="user-name">{{ user.email?.split('@')[0] }}</span>
          </p>
        </div>
        <button class="btn-refresh" (click)="refreshStats()">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M23 4v6h-6M1 20v-6h6"/>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
          </svg>
          Rafraichir
        </button>
      </header>

      <!-- Error Alert -->
      <div *ngIf="error$ | async as error" class="alert-error">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        {{ error }}
      </div>

      <!-- Main Content -->
      <ng-container *ngIf="data$ | async as data; else loading">
        <!-- Stats Cards - only when analyses exist -->
        <div class="stats-grid" *ngIf="data.stats.total_analyses > 0">
          <div class="stat-card">
            <div class="stat-card-glow"></div>
            <div class="stat-icon blue">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
            </div>
            <div class="stat-content">
              <span class="stat-value">{{ data.stats.total_analyses }}</span>
              <span class="stat-label">Total Analyses</span>
            </div>
            <div class="stat-trend" *ngIf="data.stats.total_analyses > 0">{{ data.stats.total_analyses }}</div>
          </div>

          <div class="stat-card">
            <div class="stat-card-glow red"></div>
            <div class="stat-icon red">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
              </svg>
            </div>
            <div class="stat-content">
              <span class="stat-value">{{ data.stats.noisy_detections }}</span>
              <span class="stat-label">Vehicules Bruyants</span>
            </div>
            <div class="stat-trend" [class.up]="data.stats.noisy_detections > 0">
              {{ data.stats.noisy_detections > 0 ? '⚠️' : '✓' }}
            </div>
          </div>

          <div class="stat-card">
            <div class="stat-card-glow green"></div>
            <div class="stat-icon green">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <circle cx="12" cy="12" r="10"/>
                <polyline points="12 6 12 12 16 14"/>
              </svg>
            </div>
            <div class="stat-content">
              <span class="stat-value small">{{ data.stats.last_analysis_date ? (data.stats.last_analysis_date | date:'dd/MM') : '--' }}</span>
              <span class="stat-label">Derniere Analyse</span>
            </div>
          </div>
        </div>

        <!-- Welcome empty state - only when no analyses -->
        <div class="welcome-empty" *ngIf="data.stats.total_analyses === 0">
          <div class="welcome-icon">📊</div>
          <h2>Bienvenue !</h2>
          <p>Lancez votre première analyse pour commencer</p>
          <a routerLink="/" class="btn-primary">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
            </svg>
            Analyser un fichier audio
          </a>
        </div>

        <!-- History Section - only when analyses exist -->
        <section class="history-section" *ngIf="data.stats.total_analyses > 0">
          <div class="section-header">
            <div class="section-title-group">
              <h2>Analyses récentes</h2>
            </div>
            <span class="count-badge">{{ data.history.length }} entrées</span>
          </div>

          <div class="history-card">
            <div class="table-wrapper" *ngIf="data.history.length > 0; else noHistory">
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Fichier</th>
                    <th>Statut</th>
                    <th>Confiance</th>
                  </tr>
                </thead>
                <tbody>
                  <tr *ngFor="let item of data.history; let i = index; trackBy: trackByIndex" class="table-row" [style.animation-delay.ms]="i * 50">
                    <td class="date-cell">
                      <span class="date">{{ item.timestamp | date:'dd MMM' }}</span>
                      <span class="time">{{ item.timestamp | date:'HH:mm' }}</span>
                    </td>
                    <td class="file-cell">
                      <div class="file-icon">🎵</div>
                      <span class="filename">{{ item.filename }}</span>
                    </td>
                    <td>
                      <span class="status-badge" [class.danger]="item.is_noisy" [class.success]="!item.is_noisy">
                        {{ item.is_noisy ? '🔊 Bruyant' : '✓ Conforme' }}
                      </span>
                    </td>
                    <td>
                      <div class="confidence-cell">
                        <span class="confidence-value">{{ item.confidence | number:'1.0-0' }}%</span>
                        <div class="confidence-bar">
                          <div class="bar-fill" [style.width.%]="item.confidence"></div>
                        </div>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <ng-template #noHistory>
              <div class="empty-state">
                <div class="empty-icon-wrapper">
                  <div class="empty-icon-glow"></div>
                  <div class="empty-icon">📊</div>
                </div>
                <h3>Aucune analyse</h3>
                <p>Commencez par analyser un fichier audio</p>
                <a routerLink="/" class="btn-primary">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
                  </svg>
                  Nouvelle analyse
                </a>
              </div>
            </ng-template>
          </div>
        </section>

        <!-- Audio Review Section -->
        <section class="review-section">
          <div class="section-header">
            <div class="section-title-group">
              <h2>Revue Audio IA</h2>
            </div>
            <div class="review-header-actions">
              <button class="btn-scan" *ngIf="isAdmin" (click)="scanS3()" [disabled]="scanning">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true" [class.spin]="scanning">
                  <path d="M23 4v6h-6M1 20v-6h6"/>
                  <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
                </svg>
                {{ scanning ? 'Scan en cours...' : 'Scanner S3' }}
              </button>
            </div>
          </div>

          <!-- Review Stats Bar -->
          <div class="review-stats-bar" *ngIf="reviewData$ | async as rd">
            <div class="review-stat">
              <span class="review-stat-value">{{ rd.stats.total }}</span>
              <span class="review-stat-label">Total</span>
            </div>
            <div class="review-stat pending">
              <span class="review-stat-value">{{ rd.stats.pending }}</span>
              <span class="review-stat-label">En attente</span>
            </div>
            <div class="review-stat confirmed">
              <span class="review-stat-value">{{ rd.stats.confirmed }}</span>
              <span class="review-stat-label">Confirmes</span>
            </div>
            <div class="review-stat corrected">
              <span class="review-stat-value">{{ rd.stats.corrected }}</span>
              <span class="review-stat-label">Corriges</span>
            </div>
            <div class="review-stat accuracy" *ngIf="rd.stats.accuracy_rate !== null">
              <span class="review-stat-value">{{ rd.stats.accuracy_rate | number:'1.0-0' }}%</span>
              <span class="review-stat-label">Precision IA</span>
            </div>
          </div>

          <!-- Filter Tabs -->
          <div class="review-tabs">
            <button class="tab" [class.active]="reviewFilter === 'all'" (click)="setReviewFilter('all')">Tous</button>
            <button class="tab" [class.active]="reviewFilter === 'pending'" (click)="setReviewFilter('pending')">En attente</button>
            <button class="tab" [class.active]="reviewFilter === 'confirmed'" (click)="setReviewFilter('confirmed')">Confirmes</button>
            <button class="tab" [class.active]="reviewFilter === 'corrected'" (click)="setReviewFilter('corrected')">Corriges</button>
          </div>

          <!-- Review Cards -->
          <div class="review-list" *ngIf="reviewData$ | async as rd">
            <div *ngIf="rd.reviews.length === 0" class="empty-state">
              <div class="empty-icon">🔍</div>
              <h3>Aucune revue</h3>
              <p>{{ reviewFilter === 'all' ? 'Lancez un scan S3 pour analyser les fichiers audio' : 'Aucun fichier avec ce statut' }}</p>
            </div>

            <div class="review-card" *ngFor="let review of rd.reviews; trackBy: trackByReviewId">
              <div class="review-card-header">
                <span class="review-filename">{{ getFilename(review.s3_key) }}</span>
                <span class="review-badge" [ngClass]="review.review_status">
                  {{ review.review_status === 'pending' ? 'En attente' : review.review_status === 'confirmed' ? 'Confirme' : 'Corrige' }}
                </span>
              </div>

              <!-- Audio Player -->
              <audio *ngIf="review.audio_url" controls preload="none" class="review-audio">
                <source [src]="review.audio_url" type="audio/wav">
              </audio>

              <!-- Prediction Summary -->
              <div class="review-prediction">
                <div class="pred-item">
                  <span class="pred-label">Voiture</span>
                  <span class="pred-value" [class.detected]="review.car_detected" [class.not-detected]="!review.car_detected">
                    {{ review.car_detected ? 'Detectee' : 'Non detectee' }}
                  </span>
                  <span class="pred-confidence">{{ review.car_confidence | number:'1.0-0' }}%</span>
                </div>
                <div class="pred-item" *ngIf="review.is_noisy !== null">
                  <span class="pred-label">Bruyante</span>
                  <span class="pred-value" [class.detected]="review.is_noisy" [class.not-detected]="!review.is_noisy">
                    {{ review.is_noisy ? 'Oui' : 'Non' }}
                  </span>
                  <span class="pred-confidence">{{ review.noisy_confidence | number:'1.0-0' }}%</span>
                </div>
              </div>

              <!-- Action Buttons (only for pending reviews) -->
              <div class="review-actions" *ngIf="review.review_status === 'pending'">
                <button class="btn-confirm" (click)="validateReview(review.id, 'confirmed')">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                    <polyline points="20 6 9 17 4 12"/>
                  </svg>
                  Correct
                </button>
                <button class="btn-correct" (click)="validateReview(review.id, 'corrected')">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                    <line x1="18" y1="6" x2="6" y2="18"/>
                    <line x1="6" y1="6" x2="18" y2="18"/>
                  </svg>
                  Incorrect
                </button>
              </div>
            </div>

            <!-- Pagination -->
            <div class="review-pagination" *ngIf="rd.total > rd.pageSize">
              <button class="btn-page" [disabled]="reviewPage === 1" (click)="setReviewPage(reviewPage - 1)">Precedent</button>
              <span class="page-info">{{ reviewPage }} / {{ Math.ceil(rd.total / rd.pageSize) }}</span>
              <button class="btn-page" [disabled]="reviewPage * rd.pageSize >= rd.total" (click)="setReviewPage(reviewPage + 1)">Suivant</button>
            </div>
          </div>
        </section>

        <!-- Quick Action - only when analyses exist -->
        <section class="action-section" *ngIf="data.stats.total_analyses > 0">
          <div class="action-card">
            <div class="action-glow"></div>
            <div class="action-glow secondary"></div>
            <div class="action-content">
              <h3>Prêt pour une nouvelle analyse ?</h3>
              <p>Notre IA analyse vos fichiers audio en quelques secondes</p>
            </div>
            <a routerLink="/" class="btn-action">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <polygon points="5 3 19 12 5 21 5 3"/>
              </svg>
              Lancer une analyse
            </a>
          </div>
        </section>
      </ng-container>

      <!-- Loading State -->
      <ng-template #loading>
        <div class="loading-grid" *ngIf="(error$ | async) === null">
          <div class="skeleton-card" *ngFor="let i of [1,2,3]"></div>
        </div>
      </ng-template>
    </div>
  `,
  styles: [`
    .dashboard {
      padding: 1.5rem;
      max-width: 1200px;
      margin: 0 auto;
    }

    /* Header */
    .dash-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 1.5rem;
      padding-bottom: 2rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    }

    .header-content {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    .dash-header h1 {
      font-size: 2rem;
      font-weight: 800;
      color: white;
      margin: 0;
    }

    .gradient-text {
      color: var(--accent-light);
    }

    .welcome {
      color: rgba(255, 255, 255, 0.5);
      font-size: 0.95rem;
      margin: 0;
    }

    .user-name {
      color: var(--accent-light);
      font-weight: 600;
    }

    .btn-refresh {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.75rem 1.25rem;
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: var(--radius-md);
      color: rgba(255, 255, 255, 0.6);
      font-weight: 500;
      font-size: 0.875rem;
      cursor: pointer;
      transition: all 0.25s var(--ease-out-expo);
    }

    .btn-refresh:hover {
      background: rgba(255, 255, 255, 0.06);
      color: white;
      border-color: rgba(255, 255, 255, 0.15);
    }

    .btn-refresh svg {
      width: 16px;
      height: 16px;
      transition: transform 0.3s ease;
    }

    /* Alert */
    .alert-error {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 1rem 1.25rem;
      background: rgba(239, 68, 68, 0.1);
      border: 1px solid rgba(239, 68, 68, 0.3);
      border-radius: var(--radius-md);
      color: var(--danger-lighter);
      margin-bottom: 2rem;
    }

    .alert-error svg {
      width: 20px;
      height: 20px;
      flex-shrink: 0;
    }

    /* Stats Grid */
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 1.5rem;
      margin-bottom: 3rem;
    }

    .stat-card {
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: var(--radius-xl);
      padding: 1.5rem;
      display: flex;
      align-items: center;
      gap: 1.25rem;
      transition: all 0.3s var(--ease-out-expo);
      position: relative;
    }

    .stat-card-glow {
      display: none;
    }

    .stat-card:hover {
      background: rgba(255, 255, 255, 0.05);
      border-color: rgba(255, 255, 255, 0.1);
    }

    .stat-icon {
      width: 56px;
      height: 56px;
      border-radius: var(--radius-lg);
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.3s var(--ease-out-expo);
      position: relative;
      z-index: 1;
    }

    .stat-icon svg {
      width: 26px;
      height: 26px;
    }

    .stat-icon.blue {
      background: rgba(99, 102, 241, 0.15);
      color: var(--accent-light);
    }

    .stat-icon.red {
      background: rgba(239, 68, 68, 0.15);
      color: var(--danger-lighter);
    }

    .stat-icon.green {
      background: rgba(16, 185, 129, 0.15);
      color: var(--success-light);
    }

    .stat-content {
      flex: 1;
      position: relative;
      z-index: 1;
    }

    .stat-value {
      display: block;
      font-size: 2.25rem;
      font-weight: 800;
      line-height: 1;
      margin-bottom: 0.25rem;
      color: white;
    }

    .stat-value.small {
      font-size: 1.5rem;
    }

    .stat-label {
      font-size: 0.8rem;
      color: rgba(255, 255, 255, 0.5);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .stat-trend {
      font-size: 0.8rem;
      font-weight: 600;
      padding: 0.375rem 0.75rem;
      border-radius: 100px;
      background: rgba(255, 255, 255, 0.05);
      color: rgba(255, 255, 255, 0.5);
      position: relative;
      z-index: 1;
      transition: all 0.2s ease;
    }

    .stat-trend.up {
      background: rgba(16, 185, 129, 0.15);
      color: var(--success-light);
    }

    /* History Section */
    .history-section {
      margin-bottom: 2rem;
    }

    .section-header {
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 1rem;
      margin-bottom: 1.5rem;
    }

    .section-title-group {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    .section-header h2 {
      font-size: 1.5rem;
      font-weight: 700;
      color: white;
      margin: 0;
    }

    .count-badge {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: rgba(255, 255, 255, 0.7);
      padding: 0.375rem 1rem;
      border-radius: 100px;
      font-size: 0.8rem;
      font-weight: 500;
    }

    .history-card {
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: var(--radius-xl);
      overflow: hidden;
    }

    .table-wrapper {
      overflow-x: auto;
    }

    table {
      width: 100%;
      border-collapse: collapse;
    }

    th {
      text-align: left;
      padding: 1rem 1.25rem;
      font-size: 0.7rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: rgba(255, 255, 255, 0.4);
      background: rgba(255, 255, 255, 0.02);
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
      position: sticky;
      top: 0;
    }

    td {
      padding: 1rem 1.25rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
      color: rgba(255, 255, 255, 0.8);
      font-size: 0.9rem;
    }

    .table-row {
      transition: all 0.2s ease;
    }

    @keyframes fadeInRow {
      from { opacity: 0; transform: translateX(-10px); }
      to { opacity: 1; transform: translateX(0); }
    }

    tr:last-child td {
      border-bottom: none;
    }

    tr:hover {
      background: rgba(255, 255, 255, 0.03);
    }

    .date-cell {
      display: flex;
      flex-direction: column;
    }

    .date {
      font-weight: 600;
      color: white;
    }

    .time {
      font-size: 0.75rem;
      color: rgba(255, 255, 255, 0.4);
    }

    .file-cell {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .file-icon {
      font-size: 1.25rem;
    }

    .filename {
      font-family: 'SF Mono', monospace;
      font-size: 0.85rem;
      color: rgba(255, 255, 255, 0.7);
    }

    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 0.375rem;
      padding: 0.375rem 0.875rem;
      border-radius: 100px;
      font-size: 0.8rem;
      font-weight: 600;
      transition: all 0.2s ease;
    }

    .status-badge.success {
      background: rgba(16, 185, 129, 0.15);
      color: var(--success-light);
    }

    .status-badge.danger {
      background: rgba(239, 68, 68, 0.15);
      color: var(--danger-lighter);
    }

    .confidence-cell {
      display: flex;
      flex-direction: column;
      gap: 0.375rem;
      min-width: 100px;
    }

    .confidence-value {
      font-weight: 600;
      font-size: 0.9rem;
    }

    .confidence-bar {
      height: 4px;
      background: rgba(255, 255, 255, 0.1);
      border-radius: 100px;
      overflow: hidden;
    }

    .bar-fill {
      height: 100%;
      background: var(--accent-dark);
      border-radius: 100px;
      transition: width 0.5s var(--ease-out-expo);
      position: relative;
    }

    /* Empty State */
    .empty-state {
      padding: 4rem 2rem;
      text-align: center;
      background: transparent;
    }

    .empty-icon-wrapper {
      position: relative;
      display: inline-block;
      margin-bottom: 1.5rem;
    }

    .empty-icon-glow {
      display: none;
    }

    .empty-icon {
      position: relative;
      font-size: 3.5rem;
    }

    .empty-state h3 {
      color: white;
      margin-bottom: 0.5rem;
      font-size: 1.25rem;
    }

    .empty-state p {
      color: rgba(255, 255, 255, 0.5);
      margin-bottom: 1.5rem;
    }

    .btn-primary {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.875rem 1.5rem;
      background: var(--accent-dark);
      color: white;
      border-radius: var(--radius-md);
      font-weight: 600;
      text-decoration: none;
      transition: all 0.3s var(--ease-out-expo);
      position: relative;
    }

    .btn-primary:hover {
      background: var(--accent);
    }

    .btn-primary svg {
      width: 18px;
      height: 18px;
    }

    /* Welcome Empty State */
    .welcome-empty {
      text-align: center;
      padding: 4rem 2rem;
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: var(--radius-xl);
    }

    .welcome-empty .welcome-icon {
      font-size: 3.5rem;
      margin-bottom: 1rem;
    }

    .welcome-empty h2 {
      color: white;
      font-size: 1.5rem;
      font-weight: 700;
      margin-bottom: 0.5rem;
    }

    .welcome-empty p {
      color: rgba(255, 255, 255, 0.5);
      margin-bottom: 1.5rem;
    }

    /* Action Section */
    .action-section {
      margin-top: 2rem;
    }

    .action-card {
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid rgba(99, 102, 241, 0.2);
      border-radius: var(--radius-xl);
      padding: 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 2rem;
      position: relative;
      overflow: hidden;
      transition: all 0.3s ease;
    }

    .action-card:hover {
      border-color: rgba(99, 102, 241, 0.4);
    }

    .action-glow {
      display: none;
    }

    .action-content {
      position: relative;
      z-index: 1;
    }

    .action-content h3 {
      color: white;
      font-size: 1.35rem;
      font-weight: 700;
      margin-bottom: 0.375rem;
    }

    .action-content p {
      color: rgba(255, 255, 255, 0.5);
      margin: 0;
    }

    .btn-action {
      display: flex;
      align-items: center;
      gap: 0.625rem;
      padding: 1rem 1.75rem;
      background: var(--accent-dark);
      color: white;
      border-radius: 14px;
      font-weight: 600;
      text-decoration: none;
      transition: all 0.3s var(--ease-out-expo);
      white-space: nowrap;
      position: relative;
      z-index: 1;
    }

    .btn-action:hover {
      background: var(--accent);
    }

    .btn-action svg {
      width: 18px;
      height: 18px;
    }

    /* Loading */
    .loading-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 1.5rem;
    }

    .skeleton-card {
      height: 120px;
      background: linear-gradient(90deg, rgba(255,255,255,0.03) 25%, rgba(255,255,255,0.06) 50%, rgba(255,255,255,0.03) 75%);
      background-size: 200% 100%;
      border-radius: var(--radius-xl);
      animation: skeleton 1.5s infinite;
    }

    @keyframes skeleton {
      0% { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }

    /* Responsive - Tablet */
    @media (max-width: 768px) {
      .dashboard {
        padding: 1.5rem;
      }

      .dash-header {
        flex-direction: column;
        gap: 1rem;
        align-items: stretch;
      }

      .dash-header h1 {
        font-size: 1.5rem;
      }

      .btn-refresh {
        align-self: flex-start;
      }

      .stats-grid {
        grid-template-columns: 1fr;
        gap: 1rem;
      }

      .stat-card {
        padding: 1.25rem;
      }

      .stat-icon {
        width: 48px;
        height: 48px;
      }

      .stat-value {
        font-size: 1.75rem;
      }

      .action-card {
        flex-direction: column;
        text-align: center;
        padding: 1.5rem;
        gap: 1.5rem;
      }

      .table-wrapper {
        margin: 0 -1rem;
      }

      th, td {
        padding: 0.875rem 1rem;
        font-size: 0.8rem;
      }

      .filename {
        max-width: 120px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
    }

    /* Responsive - Mobile */
    @media (max-width: 600px) {
      .dashboard {
        padding: 1rem;
      }

      .dash-header h1 {
        font-size: 1.25rem;
      }

      .welcome {
        font-size: 0.8rem;
      }

      .btn-refresh {
        padding: 0.625rem 1rem;
        font-size: 0.8rem;
      }

      .stats-grid {
        margin-bottom: 2rem;
      }

      .stat-card {
        padding: 1rem;
        border-radius: var(--radius-lg);
      }

      .stat-icon {
        width: 44px;
        height: 44px;
        border-radius: var(--radius-md);
      }

      .stat-icon svg {
        width: 22px;
        height: 22px;
      }

      .stat-value {
        font-size: 1.5rem;
      }

      .stat-label {
        font-size: 0.7rem;
      }

      .section-header h2 {
        font-size: 1.1rem;
      }

      .history-card {
        border-radius: var(--radius-lg);
      }

      /* Hide some columns on mobile */
      th:nth-child(4),
      td:nth-child(4) {
        display: none;
      }

      th, td {
        padding: 0.75rem 0.875rem;
      }

      .file-cell {
        max-width: 100px;
      }

      .filename {
        max-width: 80px;
        font-size: 0.75rem;
      }

      .status-badge {
        font-size: 0.7rem;
        padding: 0.25rem 0.625rem;
      }

      .empty-state {
        padding: 2.5rem 1.5rem;
      }

      .empty-icon {
        font-size: 2.5rem;
      }

      .action-card {
        padding: 1.25rem;
        border-radius: var(--radius-lg);
      }

      .action-content h3 {
        font-size: 1.1rem;
      }

      .action-content p {
        font-size: 0.85rem;
      }

      .btn-action {
        padding: 0.875rem 1.5rem;
        font-size: 0.9rem;
        width: 100%;
        justify-content: center;
      }
    }

    @media (max-width: 400px) {
      .dashboard {
        padding: 0.75rem;
      }

      /* Hide date column too on very small screens */
      th:nth-child(1),
      td:nth-child(1) {
        display: none;
      }

      .stat-card {
        gap: 1rem;
      }

      .stat-trend {
        display: none;
      }
    }

    /* =================== Audio Review Section =================== */
    .review-section {
      margin-top: 3rem;
      margin-bottom: 2rem;
    }

    .review-header-actions {
      display: flex;
      gap: 0.75rem;
    }

    .btn-scan {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.625rem 1.25rem;
      background: rgba(99, 102, 241, 0.15);
      border: 1px solid rgba(99, 102, 241, 0.3);
      border-radius: var(--radius-md);
      color: var(--accent-light);
      font-weight: 600;
      font-size: 0.85rem;
      cursor: pointer;
      transition: all 0.25s ease;
    }

    .btn-scan:hover:not(:disabled) {
      background: rgba(99, 102, 241, 0.25);
      border-color: rgba(99, 102, 241, 0.5);
    }

    .btn-scan:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .btn-scan svg {
      width: 16px;
      height: 16px;
    }

    .btn-scan svg.spin {
      animation: spin 1s linear infinite;
    }

    @keyframes spin {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }

    /* Review Stats Bar */
    .review-stats-bar {
      display: flex;
      gap: 1rem;
      margin-bottom: 1.5rem;
      flex-wrap: wrap;
    }

    .review-stat {
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: var(--radius-md);
      padding: 0.75rem 1.25rem;
      display: flex;
      flex-direction: column;
      align-items: center;
      min-width: 80px;
    }

    .review-stat-value {
      font-size: 1.5rem;
      font-weight: 700;
      color: white;
    }

    .review-stat-label {
      font-size: 0.7rem;
      color: rgba(255, 255, 255, 0.5);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .review-stat.pending .review-stat-value { color: #fbbf24; }
    .review-stat.confirmed .review-stat-value { color: var(--success-light); }
    .review-stat.corrected .review-stat-value { color: var(--danger-lighter); }
    .review-stat.accuracy .review-stat-value { color: var(--accent-light); }

    /* Filter Tabs */
    .review-tabs {
      display: flex;
      gap: 0.25rem;
      margin-bottom: 1.5rem;
      background: rgba(255, 255, 255, 0.03);
      border-radius: var(--radius-md);
      padding: 0.25rem;
      border: 1px solid rgba(255, 255, 255, 0.06);
    }

    .tab {
      padding: 0.5rem 1rem;
      border: none;
      background: transparent;
      color: rgba(255, 255, 255, 0.5);
      font-size: 0.85rem;
      font-weight: 500;
      border-radius: var(--radius-sm);
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .tab:hover {
      color: rgba(255, 255, 255, 0.8);
      background: rgba(255, 255, 255, 0.05);
    }

    .tab.active {
      background: rgba(99, 102, 241, 0.2);
      color: var(--accent-light);
    }

    /* Review Cards */
    .review-list {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .review-card {
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: var(--radius-lg);
      padding: 1.25rem;
      transition: all 0.2s ease;
    }

    .review-card:hover {
      background: rgba(255, 255, 255, 0.04);
      border-color: rgba(255, 255, 255, 0.1);
    }

    .review-card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1rem;
    }

    .review-filename {
      font-family: 'SF Mono', monospace;
      font-size: 0.9rem;
      color: rgba(255, 255, 255, 0.8);
    }

    .review-badge {
      padding: 0.25rem 0.75rem;
      border-radius: 100px;
      font-size: 0.75rem;
      font-weight: 600;
    }

    .review-badge.pending {
      background: rgba(251, 191, 36, 0.15);
      color: #fbbf24;
    }

    .review-badge.confirmed {
      background: rgba(16, 185, 129, 0.15);
      color: var(--success-light);
    }

    .review-badge.corrected {
      background: rgba(239, 68, 68, 0.15);
      color: var(--danger-lighter);
    }

    .review-audio {
      width: 100%;
      height: 36px;
      margin-bottom: 1rem;
      border-radius: var(--radius-sm);
    }

    /* Prediction Summary */
    .review-prediction {
      display: flex;
      gap: 1.5rem;
      margin-bottom: 1rem;
      flex-wrap: wrap;
    }

    .pred-item {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .pred-label {
      font-size: 0.8rem;
      color: rgba(255, 255, 255, 0.4);
    }

    .pred-value {
      font-size: 0.85rem;
      font-weight: 600;
      color: rgba(255, 255, 255, 0.7);
    }

    .pred-value.detected { color: var(--danger-lighter); }
    .pred-value.not-detected { color: var(--success-light); }

    .pred-confidence {
      font-size: 0.75rem;
      color: rgba(255, 255, 255, 0.4);
    }

    /* Action Buttons */
    .review-actions {
      display: flex;
      gap: 0.75rem;
    }

    .btn-confirm, .btn-correct {
      display: flex;
      align-items: center;
      gap: 0.375rem;
      padding: 0.5rem 1rem;
      border: 1px solid;
      border-radius: var(--radius-md);
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .btn-confirm {
      background: rgba(16, 185, 129, 0.1);
      border-color: rgba(16, 185, 129, 0.3);
      color: var(--success-light);
    }

    .btn-confirm:hover {
      background: rgba(16, 185, 129, 0.2);
      border-color: rgba(16, 185, 129, 0.5);
    }

    .btn-correct {
      background: rgba(239, 68, 68, 0.1);
      border-color: rgba(239, 68, 68, 0.3);
      color: var(--danger-lighter);
    }

    .btn-correct:hover {
      background: rgba(239, 68, 68, 0.2);
      border-color: rgba(239, 68, 68, 0.5);
    }

    .btn-confirm svg, .btn-correct svg {
      width: 16px;
      height: 16px;
    }

    /* Pagination */
    .review-pagination {
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 1rem;
      margin-top: 1.5rem;
    }

    .btn-page {
      padding: 0.5rem 1rem;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: var(--radius-md);
      color: rgba(255, 255, 255, 0.7);
      font-size: 0.85rem;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .btn-page:hover:not(:disabled) {
      background: rgba(255, 255, 255, 0.1);
      color: white;
    }

    .btn-page:disabled {
      opacity: 0.3;
      cursor: not-allowed;
    }

    .page-info {
      font-size: 0.85rem;
      color: rgba(255, 255, 255, 0.5);
    }

    /* Review responsive */
    @media (max-width: 768px) {
      .review-stats-bar {
        gap: 0.5rem;
      }

      .review-stat {
        padding: 0.5rem 0.75rem;
        min-width: 60px;
      }

      .review-stat-value {
        font-size: 1.25rem;
      }

      .review-tabs {
        overflow-x: auto;
      }

      .review-prediction {
        flex-direction: column;
        gap: 0.5rem;
      }

      .review-actions {
        flex-direction: column;
      }

      .btn-confirm, .btn-correct {
        justify-content: center;
      }
    }
  `]
})
export class DashboardComponent implements OnInit {
  Math = Math;
  trackByIndex = (i: number) => i;
  trackByReviewId = (_: number, r: AudioReview) => r.id;

  user$: Observable<any>;
  data$: Observable<{ stats: any, history: any[] }>;
  error$ = new BehaviorSubject<string | null>(null);
  reviewData$!: Observable<ReviewPageData>;

  isAdmin = false;
  scanning = false;
  reviewFilter = 'all';
  reviewPage = 1;

  private refreshTrigger = new BehaviorSubject<void>(undefined);
  private reviewTrigger = new BehaviorSubject<{ filter: string; page: number }>({ filter: 'all', page: 1 });

  private dashboardService = inject(DashboardService);
  private audioReviewService = inject(AudioReviewService);

  constructor(public authService: AuthService) {
    this.user$ = this.authService.currentUser$;

    this.data$ = this.refreshTrigger.pipe(
      tap(() => this.error$.next(null)),
      switchMap(() => this.dashboardService.loadDashboardData().pipe(
        catchError(() => {
          this.error$.next('Impossible de charger les donnees.');
          return of({ stats: { total_analyses: 0, noisy_detections: 0, last_analysis_date: null }, history: [] });
        })
      ))
    );

    this.reviewData$ = this.reviewTrigger.pipe(
      switchMap(({ filter, page }) =>
        this.audioReviewService.loadReviewPage(filter, page).pipe(
          catchError(() => of({
            reviews: [], stats: { total: 0, pending: 0, confirmed: 0, corrected: 0, accuracy_rate: null },
            total: 0, page: 1, pageSize: 20,
          }))
        )
      )
    );

    this.authService.currentUser$.subscribe(user => {
      this.isAdmin = user?.is_admin ?? false;
    });
  }

  ngOnInit() {
    this.refreshStats();
  }

  refreshStats() {
    this.refreshTrigger.next();
    this.reviewTrigger.next({ filter: this.reviewFilter, page: this.reviewPage });
  }

  getFilename(s3Key: string): string {
    return s3Key.split('/').pop() || s3Key;
  }

  setReviewFilter(filter: string) {
    this.reviewFilter = filter;
    this.reviewPage = 1;
    this.reviewTrigger.next({ filter, page: 1 });
  }

  setReviewPage(page: number) {
    this.reviewPage = page;
    this.reviewTrigger.next({ filter: this.reviewFilter, page });
  }

  scanS3() {
    this.scanning = true;
    this.audioReviewService.scanNewFiles().subscribe({
      next: () => {
        this.scanning = false;
        this.reviewTrigger.next({ filter: this.reviewFilter, page: this.reviewPage });
      },
      error: () => {
        this.scanning = false;
      },
    });
  }

  validateReview(reviewId: number, status: 'confirmed' | 'corrected') {
    this.audioReviewService.validateReview(reviewId, { status }).subscribe({
      next: () => {
        this.reviewTrigger.next({ filter: this.reviewFilter, page: this.reviewPage });
      },
    });
  }
}
