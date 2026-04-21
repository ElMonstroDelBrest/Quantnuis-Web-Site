import { Component, OnInit, ChangeDetectorRef, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../services/ec2/auth.service';
import { AdminService, AnnotationRequest, AdminUser, ReviewAction } from '../services/admin.service';
import { Router } from '@angular/router';
import { finalize } from 'rxjs/operators';

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="admin-container">
      <!-- Header -->
      <header class="admin-header">
        <div class="header-content">
          <div class="header-badge">
            <span class="badge-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
              </svg>
            </span>
            Administration
          </div>
          <h1 class="header-title">
            <span class="gradient-text">Panneau</span> d'administration
          </h1>
          <p class="header-subtitle">
            Gerez les demandes d'annotations et les utilisateurs
          </p>
        </div>
      </header>

      <!-- Stats Cards -->
      <div class="stats-grid" *ngIf="stats">
        <div class="stat-card pending">
          <div class="stat-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <polyline points="12 6 12 12 16 14"/>
            </svg>
          </div>
          <div class="stat-content">
            <span class="stat-value">{{ stats.total_pending }}</span>
            <span class="stat-label">En attente</span>
          </div>
        </div>
        <div class="stat-card approved">
          <div class="stat-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
              <polyline points="22 4 12 14.01 9 11.01"/>
            </svg>
          </div>
          <div class="stat-content">
            <span class="stat-value">{{ stats.total_approved }}</span>
            <span class="stat-label">Approuvees</span>
          </div>
        </div>
        <div class="stat-card rejected">
          <div class="stat-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="15" y1="9" x2="9" y2="15"/>
              <line x1="9" y1="9" x2="15" y2="15"/>
            </svg>
          </div>
          <div class="stat-content">
            <span class="stat-value">{{ stats.total_rejected }}</span>
            <span class="stat-label">Rejetees</span>
          </div>
        </div>
        <div class="stat-card integrated">
          <div class="stat-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z"/>
              <path d="M2 17l10 5 10-5"/>
              <path d="M2 12l10 5 10-5"/>
            </svg>
          </div>
          <div class="stat-content">
            <span class="stat-value">{{ stats.total_annotations_integrated }}</span>
            <span class="stat-label">Annotations integrees</span>
          </div>
        </div>
      </div>

      <!-- Tab Navigation -->
      <div class="tab-navigation">
        <button class="tab-btn" [class.active]="activeTab === 'requests'" (click)="activeTab = 'requests'">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
          Demandes d'annotations
          <span class="badge" *ngIf="stats?.total_pending > 0">{{ stats.total_pending }}</span>
        </button>
        <button class="tab-btn" [class.active]="activeTab === 'users'" (click)="activeTab = 'users'; loadUsers()">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
            <circle cx="9" cy="7" r="4"/>
            <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
            <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
          </svg>
          Utilisateurs
        </button>
      </div>

      <!-- Requests Tab -->
      <div class="tab-content" *ngIf="activeTab === 'requests'">
        <!-- Filter -->
        <div class="filter-bar">
          <label>Filtrer par statut:</label>
          <div class="custom-select" [class.open]="isFilterOpen">
            <div class="select-trigger" (click)="toggleFilter()">
              <span>{{ getFilterLabel(statusFilter) }}</span>
              <span class="arrow">▼</span>
            </div>
            <div class="select-options">
              <div class="select-option" [class.selected]="statusFilter === 'pending'" (click)="selectFilter('pending')">En attente</div>
              <div class="select-option" [class.selected]="statusFilter === 'approved'" (click)="selectFilter('approved')">Approuvées</div>
              <div class="select-option" [class.selected]="statusFilter === 'rejected'" (click)="selectFilter('rejected')">Rejetées</div>
              <div class="select-option" [class.selected]="statusFilter === 'all'" (click)="selectFilter('all')">Toutes</div>
            </div>
          </div>
        </div>

        <!-- Requests List -->
        <div class="requests-list" *ngIf="requests.length > 0">
          <div class="request-card" *ngFor="let req of requests" [class.expanded]="selectedRequest?.id === req.id">
            <div class="request-header" (click)="selectRequest(req)">
              <div class="request-info">
                <div class="request-badge" [ngClass]="req.model_type">
                  {{ req.model_type === 'car_detector' ? 'AI1' : 'AI2' }}
                </div>
                <div class="request-details">
                  <h4>{{ req.filename }}</h4>
                  <p>{{ req.annotation_count }} annotations - {{ formatDuration(req.total_duration) }}</p>
                </div>
              </div>
              <div class="request-meta">
                <span class="status-badge" [ngClass]="req.status">{{ getStatusLabel(req.status) }}</span>
                <span class="date">{{ formatDate(req.created_at) }}</span>
                <span class="email">{{ req.submitted_by_email }}</span>
              </div>
              <div class="expand-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="6 9 12 15 18 9"/>
                </svg>
              </div>
            </div>

            <!-- Expanded Details -->
            <div class="request-expanded" *ngIf="selectedRequest?.id === req.id && requestDetails">
              <div class="annotations-preview">
                <h5>Apercu des annotations:</h5>
                <div class="annotations-table">
                  <div class="table-header">
                    <span>Debut</span>
                    <span>Fin</span>
                    <span>Label</span>
                    <span>Note</span>
                  </div>
                  <div class="table-row" *ngFor="let ann of requestDetails.annotations.slice(0, 5)">
                    <span>{{ ann.start }}</span>
                    <span>{{ ann.end }}</span>
                    <span class="label-badge" [ngClass]="ann.label">{{ ann.label }}</span>
                    <span class="note">{{ ann.note || '-' }}</span>
                  </div>
                  <div class="more-indicator" *ngIf="requestDetails.annotations.length > 5">
                    +{{ requestDetails.annotations.length - 5 }} autres annotations...
                  </div>
                </div>
              </div>

              <!-- Action Buttons -->
              <div class="action-buttons" *ngIf="req.status === 'pending'">
                <div class="note-input">
                  <input type="text" [(ngModel)]="adminNote" placeholder="Note (optionnel)...">
                </div>
                <button class="btn-approve" (click)="reviewRequest(req.id, 'approve')" [disabled]="isProcessing">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="20 6 9 17 4 12"/>
                  </svg>
                  Approuver
                </button>
                <button class="btn-reject" (click)="reviewRequest(req.id, 'reject')" [disabled]="isProcessing">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"/>
                    <line x1="6" y1="6" x2="18" y2="18"/>
                  </svg>
                  Rejeter
                </button>
              </div>

              <!-- Already reviewed -->
              <div class="review-info" *ngIf="req.status !== 'pending'">
                <p>
                  <strong>{{ req.status === 'approved' ? 'Approuvee' : 'Rejetee' }}</strong>
                  <span *ngIf="req.reviewed_by_email">par {{ req.reviewed_by_email }}</span>
                  <span *ngIf="req.reviewed_at">le {{ formatDate(req.reviewed_at!) }}</span>
                </p>
                <p *ngIf="req.admin_note" class="admin-note">Note: {{ req.admin_note }}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Empty State -->
        <div class="empty-state" *ngIf="requests.length === 0 && !isLoading">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"/>
            <rect x="9" y="3" width="6" height="4" rx="2"/>
          </svg>
          <h4>Aucune demande</h4>
          <p>Il n'y a pas de demandes avec ce statut.</p>
        </div>
      </div>

      <!-- Users Tab -->
      <div class="tab-content" *ngIf="activeTab === 'users'">
        <div class="users-list" *ngIf="users.length > 0 && !isLoading">
          <div class="user-card" *ngFor="let user of users">
            <div class="user-avatar">
              {{ user.email.charAt(0).toUpperCase() }}
            </div>
            <div class="user-info">
              <h4>{{ user.email }}</h4>
              <p>Inscrit le {{ formatDate(user.created_at) }}</p>
            </div>
            <div class="user-badges">
              <span class="badge admin" *ngIf="user.is_admin">Admin</span>
              <span class="badge active" *ngIf="user.is_active">Actif</span>
              <span class="badge inactive" *ngIf="!user.is_active">Inactif</span>
            </div>
            <button class="btn-make-admin"
                    *ngIf="!user.is_admin"
                    (click)="makeAdmin(user)"
                    [disabled]="isProcessing">
              Promouvoir admin
            </button>
          </div>
        </div>
        <div class="empty-state" *ngIf="users.length === 0 && !isLoading">
          <h4>Aucun utilisateur</h4>
          <p>Il n'y a pas d'utilisateurs enregistres.</p>
        </div>
      </div>

      <!-- Loading -->
      <div class="loading-overlay" *ngIf="isLoading">
        <div class="spinner"></div>
        <p>Chargement...</p>
      </div>
    </div>
  `,
  styles: [`
    .admin-container {
      padding: 1.5rem 2rem;
      max-width: 1400px;
      margin: 0 auto;
    }

    /* Header */
    .admin-header {
      margin-bottom: 2rem;
    }

    .header-badge {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      background: rgba(239, 68, 68, 0.1);
      border: 1px solid rgba(239, 68, 68, 0.2);
      padding: 0.5rem 1rem;
      border-radius: 100px;
      font-size: 0.85rem;
      color: var(--danger-light);
      margin-bottom: 1rem;
    }

    .badge-icon {
      width: 16px;
      height: 16px;
    }

    .badge-icon svg {
      width: 100%;
      height: 100%;
    }

    .header-title {
      font-size: 2.5rem;
      font-weight: 700;
      line-height: 1.2;
      margin-bottom: 1rem;
      color: white;
    }

    .gradient-text {
      background: linear-gradient(135deg, #ef4444 0%, #f97316 50%, #eab308 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }

    .header-subtitle {
      font-size: 1.1rem;
      color: rgba(255, 255, 255, 0.6);
    }

    /* Stats Grid */
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1rem;
      margin-bottom: 2rem;
    }

    .stat-card {
      display: flex;
      align-items: center;
      gap: 1rem;
      padding: 1.25rem;
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: var(--radius-lg);
    }

    .stat-card.pending { border-left: 4px solid var(--warning); }
    .stat-card.approved { border-left: 4px solid var(--success); }
    .stat-card.rejected { border-left: 4px solid var(--danger); }
    .stat-card.integrated { border-left: 4px solid var(--accent); }

    .stat-icon {
      width: 48px;
      height: 48px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: var(--radius-md);
    }

    .stat-card.pending .stat-icon { background: rgba(245, 158, 11, 0.15); color: var(--warning-light); }
    .stat-card.approved .stat-icon { background: rgba(16, 185, 129, 0.15); color: var(--success-light); }
    .stat-card.rejected .stat-icon { background: rgba(239, 68, 68, 0.15); color: var(--danger-light); }
    .stat-card.integrated .stat-icon { background: rgba(99, 102, 241, 0.15); color: var(--accent-light); }

    .stat-icon svg {
      width: 24px;
      height: 24px;
    }

    .stat-value {
      font-size: 1.75rem;
      font-weight: 700;
      color: white;
    }

    .stat-label {
      font-size: 0.85rem;
      color: rgba(255, 255, 255, 0.5);
    }

    /* Tab Navigation */
    .tab-navigation {
      display: flex;
      gap: 0.5rem;
      margin-bottom: 1.5rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
      padding-bottom: 1rem;
    }

    .tab-btn {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.75rem 1.25rem;
      background: transparent;
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 10px;
      color: rgba(255, 255, 255, 0.6);
      font-size: 0.9rem;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .tab-btn:hover {
      background: rgba(255, 255, 255, 0.05);
      color: white;
    }

    .tab-btn.active {
      background: rgba(99, 102, 241, 0.15);
      border-color: rgba(99, 102, 241, 0.3);
      color: var(--accent-light);
    }

    .tab-btn svg {
      width: 18px;
      height: 18px;
    }

    .tab-btn .badge {
      background: var(--danger);
      color: white;
      font-size: 0.75rem;
      padding: 0.15rem 0.5rem;
      border-radius: 100px;
    }

    /* Filter Bar */
    .filter-bar {
      display: flex;
      align-items: center;
      gap: 1rem;
      margin-bottom: 1.5rem;
    }

    .filter-bar label {
      color: rgba(255, 255, 255, 0.6);
      font-size: 0.9rem;
    }

    /* Custom Select Dropdown */
    .custom-select {
      position: relative;
      min-width: 180px;
    }

    .select-trigger {
      background: rgba(0, 0, 0, 0.3);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 8px;
      padding: 0.5rem 1rem;
      color: white;
      font-size: 0.9rem;
      cursor: pointer;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 0.5rem;
      transition: all 0.2s ease;
    }

    .select-trigger:hover {
      border-color: rgba(255, 255, 255, 0.2);
      background: rgba(0, 0, 0, 0.4);
    }

    .custom-select.open .select-trigger {
      border-color: var(--accent);
      border-bottom-left-radius: 0;
      border-bottom-right-radius: 0;
    }

    .select-trigger .arrow {
      font-size: 0.7rem;
      transition: transform 0.2s ease;
    }

    .custom-select.open .select-trigger .arrow {
      transform: rotate(180deg);
    }

    .select-options {
      position: absolute;
      top: 100%;
      left: 0;
      right: 0;
      background: #1a1a2e;
      border: 1px solid var(--accent);
      border-top: none;
      border-bottom-left-radius: 8px;
      border-bottom-right-radius: 8px;
      overflow: hidden;
      z-index: 100;
      display: none;
    }

    .custom-select.open .select-options {
      display: block;
    }

    .select-option {
      padding: 0.6rem 1rem;
      color: rgba(255, 255, 255, 0.8);
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .select-option:hover {
      background: rgba(99, 102, 241, 0.2);
      color: white;
    }

    .select-option.selected {
      background: rgba(99, 102, 241, 0.3);
      color: white;
      font-weight: 500;
    }

    /* Requests List */
    .requests-list {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .request-card {
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: var(--radius-lg);
      overflow: hidden;
      transition: all 0.3s ease;
    }

    .request-card.expanded {
      border-color: rgba(99, 102, 241, 0.3);
    }

    .request-header {
      display: flex;
      align-items: center;
      padding: 1rem 1.5rem;
      cursor: pointer;
      gap: 1rem;
    }

    .request-header:hover {
      background: rgba(255, 255, 255, 0.02);
    }

    .request-info {
      display: flex;
      align-items: center;
      gap: 1rem;
      flex: 1;
    }

    .request-badge {
      width: 40px;
      height: 40px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 10px;
      font-size: 0.8rem;
      font-weight: 700;
    }

    .request-badge.car_detector {
      background: rgba(59, 130, 246, 0.15);
      color: var(--info-light);
    }

    .request-badge.noisy_car_detector {
      background: rgba(239, 68, 68, 0.15);
      color: var(--danger-light);
    }

    .request-details h4 {
      font-size: 1rem;
      font-weight: 600;
      color: white;
      margin-bottom: 0.25rem;
    }

    .request-details p {
      font-size: 0.85rem;
      color: rgba(255, 255, 255, 0.5);
      margin: 0;
    }

    .request-meta {
      display: flex;
      align-items: center;
      gap: 1rem;
    }

    .status-badge {
      padding: 0.25rem 0.75rem;
      border-radius: 100px;
      font-size: 0.75rem;
      font-weight: 600;
    }

    .status-badge.pending {
      background: rgba(245, 158, 11, 0.15);
      color: var(--warning-light);
    }

    .status-badge.approved {
      background: rgba(16, 185, 129, 0.15);
      color: var(--success-light);
    }

    .status-badge.rejected {
      background: rgba(239, 68, 68, 0.15);
      color: var(--danger-light);
    }

    .date, .email {
      font-size: 0.85rem;
      color: rgba(255, 255, 255, 0.4);
    }

    .expand-icon {
      width: 24px;
      height: 24px;
      color: rgba(255, 255, 255, 0.3);
      transition: transform 0.3s ease;
    }

    .request-card.expanded .expand-icon {
      transform: rotate(180deg);
    }

    /* Expanded Details */
    .request-expanded {
      padding: 1.5rem;
      border-top: 1px solid rgba(255, 255, 255, 0.06);
      background: rgba(0, 0, 0, 0.2);
    }

    .annotations-preview h5 {
      font-size: 0.9rem;
      font-weight: 600;
      color: rgba(255, 255, 255, 0.7);
      margin-bottom: 1rem;
    }

    .annotations-table {
      background: rgba(0, 0, 0, 0.2);
      border-radius: var(--radius-md);
      overflow: hidden;
    }

    .table-header, .table-row {
      display: grid;
      grid-template-columns: 1fr 1fr 1fr 2fr;
      gap: 1rem;
      padding: 0.75rem 1rem;
    }

    .table-header {
      background: rgba(255, 255, 255, 0.05);
      font-size: 0.8rem;
      font-weight: 600;
      color: rgba(255, 255, 255, 0.5);
      text-transform: uppercase;
    }

    .table-row {
      border-top: 1px solid rgba(255, 255, 255, 0.05);
      font-size: 0.85rem;
      color: rgba(255, 255, 255, 0.8);
    }

    .label-badge {
      display: inline-block;
      padding: 0.15rem 0.5rem;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 600;
    }

    .label-badge.car { background: rgba(59, 130, 246, 0.2); color: var(--info-light); }
    .label-badge.noisy_car { background: rgba(239, 68, 68, 0.2); color: var(--danger-light); }
    .label-badge.noise { background: rgba(107, 114, 128, 0.2); color: var(--gray-light); }

    .note {
      color: rgba(255, 255, 255, 0.5);
      font-style: italic;
    }

    .more-indicator {
      padding: 0.75rem 1rem;
      text-align: center;
      color: rgba(255, 255, 255, 0.4);
      font-size: 0.85rem;
    }

    /* Action Buttons */
    .action-buttons {
      display: flex;
      gap: 1rem;
      margin-top: 1.5rem;
      align-items: center;
    }

    .note-input {
      flex: 1;
    }

    .note-input input {
      width: 100%;
      background: rgba(0, 0, 0, 0.3);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 8px;
      padding: 0.75rem 1rem;
      color: white;
      font-size: 0.9rem;
    }

    .btn-approve, .btn-reject {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.75rem 1.5rem;
      border: none;
      border-radius: 10px;
      font-size: 0.9rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .btn-approve {
      background: var(--success);
      color: white;
    }

    .btn-approve:hover:not(:disabled) {
      transform: translateY(-2px);
      box-shadow: var(--shadow-btn-success);
    }

    .btn-reject {
      background: rgba(239, 68, 68, 0.15);
      border: 1px solid rgba(239, 68, 68, 0.3);
      color: var(--danger-light);
    }

    .btn-reject:hover:not(:disabled) {
      background: rgba(239, 68, 68, 0.25);
    }

    .btn-approve:disabled, .btn-reject:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .btn-approve svg, .btn-reject svg {
      width: 18px;
      height: 18px;
    }

    /* Review Info */
    .review-info {
      margin-top: 1rem;
      padding: 1rem;
      background: rgba(255, 255, 255, 0.03);
      border-radius: 8px;
      color: rgba(255, 255, 255, 0.6);
      font-size: 0.9rem;
    }

    .admin-note {
      margin-top: 0.5rem;
      font-style: italic;
    }

    /* Users List */
    .users-list {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }

    .user-card {
      display: flex;
      align-items: center;
      gap: 1rem;
      padding: 1rem 1.5rem;
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: var(--radius-md);
    }

    .user-avatar {
      width: 44px;
      height: 44px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: linear-gradient(135deg, #6366f1, #a855f7);
      border-radius: 50%;
      font-size: 1.2rem;
      font-weight: 700;
      color: white;
    }

    .user-info {
      flex: 1;
    }

    .user-info h4 {
      font-size: 1rem;
      font-weight: 600;
      color: white;
      margin-bottom: 0.25rem;
    }

    .user-info p {
      font-size: 0.85rem;
      color: rgba(255, 255, 255, 0.5);
      margin: 0;
    }

    .user-badges {
      display: flex;
      gap: 0.5rem;
    }

    .user-badges .badge {
      padding: 0.25rem 0.75rem;
      border-radius: 100px;
      font-size: 0.75rem;
      font-weight: 600;
    }

    .user-badges .badge.admin {
      background: rgba(239, 68, 68, 0.15);
      color: var(--danger-light);
    }

    .user-badges .badge.active {
      background: rgba(16, 185, 129, 0.15);
      color: var(--success-light);
    }

    .user-badges .badge.inactive {
      background: rgba(107, 114, 128, 0.15);
      color: var(--gray-light);
    }

    .btn-make-admin {
      padding: 0.5rem 1rem;
      background: rgba(239, 68, 68, 0.1);
      border: 1px solid rgba(239, 68, 68, 0.3);
      border-radius: 8px;
      color: var(--danger-light);
      font-size: 0.85rem;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .btn-make-admin:hover:not(:disabled) {
      background: rgba(239, 68, 68, 0.2);
    }

    .btn-make-admin:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    /* Empty State */
    .empty-state {
      text-align: center;
      padding: 4rem 2rem;
      color: rgba(255, 255, 255, 0.4);
    }

    .empty-state svg {
      width: 64px;
      height: 64px;
      margin-bottom: 1rem;
      opacity: 0.3;
    }

    .empty-state h4 {
      font-size: 1.25rem;
      color: rgba(255, 255, 255, 0.6);
      margin-bottom: 0.5rem;
    }

    /* Loading */
    .loading-overlay {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 4rem;
      color: rgba(255, 255, 255, 0.5);
    }

    .spinner {
      width: 40px;
      height: 40px;
      border: 3px solid rgba(255, 255, 255, 0.1);
      border-top-color: var(--accent);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
      margin-bottom: 1rem;
    }

    /* Responsive */
    @media (max-width: 1100px) {
      .stats-grid {
        grid-template-columns: repeat(2, 1fr);
      }
    }

    @media (max-width: 768px) {
      .stats-grid {
        grid-template-columns: 1fr;
      }

      .request-header {
        flex-wrap: wrap;
      }

      .request-meta {
        width: 100%;
        margin-top: 0.5rem;
      }

      .action-buttons {
        flex-direction: column;
      }

      .table-header, .table-row {
        grid-template-columns: 1fr 1fr;
      }
    }
  `]
})
export class AdminComponent implements OnInit {
  activeTab: 'requests' | 'users' = 'requests';
  statusFilter: string = 'pending';

  stats: any = null;
  requests: AnnotationRequest[] = [];
  users: AdminUser[] = [];
  selectedRequest: AnnotationRequest | null = null;
  requestDetails: any = null;

  adminNote: string = '';
  isLoading: boolean = false;
  isProcessing: boolean = false;
  isFilterOpen: boolean = false;

  private adminService = inject(AdminService);

  constructor(
    private authService: AuthService,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit() {
    // Verifier si l'utilisateur est admin
    this.authService.currentUser$.subscribe(user => {
      if (user && !user.is_admin) {
        this.router.navigate(['/dashboard']);
      }
    });

    this.loadStats();
    this.loadRequests();
  }

  // Filter dropdown methods
  toggleFilter() {
    this.isFilterOpen = !this.isFilterOpen;
  }

  selectFilter(value: string) {
    this.statusFilter = value;
    this.isFilterOpen = false;
    this.loadRequests();
  }

  getFilterLabel(value: string): string {
    const labels: { [key: string]: string } = {
      'pending': 'En attente',
      'approved': 'Approuvées',
      'rejected': 'Rejetées',
      'all': 'Toutes'
    };
    return labels[value] || value;
  }

  loadStats() {
    this.adminService.getStats().subscribe({
      next: (stats) => {
        this.stats = stats;
        this.cdr.detectChanges();
      },
      error: (err) => console.error('Error loading stats:', err)
    });
  }

  loadRequests() {
    this.isLoading = true;
    this.selectedRequest = null;
    this.requestDetails = null;

    this.adminService.getAnnotationRequests(this.statusFilter).pipe(
      finalize(() => {
        this.isLoading = false;
        this.cdr.detectChanges();
      })
    ).subscribe({
      next: (requests) => {
        this.requests = requests;
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('Error loading requests:', err);
      }
    });
  }

  loadUsers() {
    if (this.users.length > 0) return;

    this.isLoading = true;
    this.adminService.getAllUsers().pipe(
      finalize(() => {
        this.isLoading = false;
        this.cdr.detectChanges();
      })
    ).subscribe({
      next: (users) => {
        this.users = users;
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('Error loading users:', err);
      }
    });
  }

  selectRequest(request: AnnotationRequest) {
    if (this.selectedRequest?.id === request.id) {
      this.selectedRequest = null;
      this.requestDetails = null;
      this.cdr.detectChanges();
      return;
    }

    this.selectedRequest = request;
    this.adminNote = '';

    this.adminService.getAnnotationRequestDetails(request.id).subscribe({
      next: (details) => {
        this.requestDetails = details;
        this.cdr.detectChanges();
      },
      error: (err) => console.error('Error loading details:', err)
    });
  }

  reviewRequest(requestId: number, action: 'approve' | 'reject') {
    this.isProcessing = true;

    this.adminService.reviewAnnotationRequest(requestId, action as ReviewAction, this.adminNote || undefined).subscribe({
      next: (result) => {
        alert(result.message);
        this.loadStats();
        this.loadRequests();
        this.isProcessing = false;
      },
      error: (err) => {
        alert('Erreur: ' + (err.error?.detail || 'Erreur inconnue'));
        this.isProcessing = false;
      }
    });
  }

  makeAdmin(user: AdminUser) {
    if (!confirm(`Etes-vous sur de vouloir promouvoir ${user.email} en administrateur ?`)) {
      return;
    }

    this.isProcessing = true;

    this.adminService.makeUserAdmin(user.id).subscribe({
      next: (result) => {
        alert(result.message);
        user.is_admin = true;
        this.isProcessing = false;
      },
      error: (err) => {
        alert('Erreur: ' + (err.error?.detail || 'Erreur inconnue'));
        this.isProcessing = false;
      }
    });
  }

  formatDuration(seconds: number): string {
    if (!seconds) return '0s';
    const min = Math.floor(seconds / 60);
    const sec = Math.floor(seconds % 60);
    return min > 0 ? `${min}m ${sec}s` : `${sec}s`;
  }

  formatDate(dateStr: string): string {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  getStatusLabel(status: string): string {
    switch (status) {
      case 'pending': return 'En attente';
      case 'approved': return 'Approuvee';
      case 'rejected': return 'Rejetee';
      default: return status;
    }
  }
}
