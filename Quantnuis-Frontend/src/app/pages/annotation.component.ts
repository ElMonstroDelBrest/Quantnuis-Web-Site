import { Component, ElementRef, ViewChild, AfterViewInit, OnDestroy, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { environment } from '../../environments/environment';
import { AuthService } from '../services/ec2/auth.service';
import { S3AudioService, S3AudioFile } from '../services/s3-audio.service';
import { AnnotationPersistenceService, AnnotationSession } from '../services/annotation-persistence.service';
import { TextGridService, AnnotationWithTier } from '../services/textgrid.service';
import { SafeHtmlPipe } from '../shared/pipes/safe-html.pipe';

interface Annotation {
  id: number;
  startTime: number;
  endTime: number;
  label: string;
  aiModel: 'car_detector' | 'noisy_car_detector';
  note: string;
  dbPeak?: number;
}

interface SavedSession {
  fileName: string;
  fileSize: number;
  annotations: Annotation[];
  currentTime: number;
  currentAiModel: 'car_detector' | 'noisy_car_detector';
  savedAt: string;
  s3Key?: string;  // If loaded from S3
}

@Component({
  selector: 'app-annotation',
  standalone: true,
  imports: [CommonModule, FormsModule, SafeHtmlPipe],
  template: `
    <!-- Quick Feedback Toast (keyboard shortcuts) -->
    <div class="quick-feedback-toast" [class.show]="showQuickFeedbackToast">
      {{ quickFeedbackMessage }}
    </div>

    <!-- TextGrid Import Modal -->
    <div class="import-modal-overlay" *ngIf="showImportModal">
      <div class="import-modal">
        <div class="import-modal-header">
          <div class="import-modal-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
          </div>
          <h3>Importer TextGrid</h3>
        </div>

        <div class="import-modal-content">
          <p class="import-file-name">{{ importFileName }}</p>
          <p class="import-summary">
            {{ importedAnnotations.length }} annotation(s) trouvee(s)
          </p>

          <div class="import-preview" *ngIf="importedAnnotations.length > 0">
            <div class="import-preview-item" *ngFor="let ann of importedAnnotations.slice(0, 5)">
              <span class="preview-time">{{ formatTime(ann.startTime) }} - {{ formatTime(ann.endTime) }}</span>
              <span class="preview-tier">{{ ann.tier }}</span>
              <span class="preview-label">{{ ann.label }}</span>
            </div>
            <p class="import-more" *ngIf="importedAnnotations.length > 5">
              ... et {{ importedAnnotations.length - 5 }} de plus
            </p>
          </div>

          <div class="import-options">
            <label class="import-option">
              <input type="radio" name="importMode" value="replace" [(ngModel)]="importMode">
              <span>Remplacer les annotations existantes</span>
            </label>
            <label class="import-option">
              <input type="radio" name="importMode" value="merge" [(ngModel)]="importMode">
              <span>Fusionner avec les annotations existantes</span>
            </label>
          </div>
        </div>

        <div class="import-modal-actions">
          <button class="btn-cancel" (click)="cancelImport()">Annuler</button>
          <button class="btn-import" (click)="confirmImport()" [disabled]="importedAnnotations.length === 0">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
            Importer
          </button>
        </div>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div class="delete-modal-overlay" *ngIf="showDeleteConfirmModal">
      <div class="delete-modal">
        <div class="delete-modal-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"/>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            <line x1="10" y1="11" x2="10" y2="17"/>
            <line x1="14" y1="11" x2="14" y2="17"/>
          </svg>
        </div>
        <h3>Supprimer cette annotation ?</h3>
        <p class="delete-info" *ngIf="annotationToDelete">
          <strong>{{ formatTime(annotationToDelete.startTime) }} - {{ formatTime(annotationToDelete.endTime) }}</strong><br>
          {{ getLabelText(annotationToDelete.label) }}
        </p>
        <p class="delete-hint">Vous pouvez annuler avec <kbd>Ctrl+Z</kbd></p>
        <div class="delete-modal-actions">
          <button class="btn-cancel" (click)="cancelDelete()">Annuler</button>
          <button class="btn-delete" (click)="confirmDelete()">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/>
            </svg>
            Supprimer
          </button>
        </div>
      </div>
    </div>

    <!-- Session Restoration Modal -->
    <div class="session-modal-overlay" *ngIf="showSessionModal">
      <div class="session-modal">
        <div class="session-modal-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
            <path d="M3 3v5h5"/>
            <path d="M12 7v5l4 2"/>
          </svg>
        </div>
        <h3>Session precedente detectee</h3>
        <p class="session-info">
          <strong>{{ savedSession?.fileName }}</strong><br>
          {{ savedSession?.annotations?.length || 0 }} annotation(s) sauvegardee(s)<br>
          <span class="session-date">{{ formatSessionDate(savedSession?.savedAt) }}</span>
        </p>
        <div class="session-modal-actions">
          <button class="btn-restore" (click)="restoreSession()">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="1 4 1 10 7 10"/>
              <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/>
            </svg>
            Reprendre
          </button>
          <button class="btn-discard" (click)="discardSession()">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
            Nouvelle session
          </button>
        </div>
      </div>
    </div>

    <div class="annotation-container">
      <!-- Hero Section -->
      <header class="hero-section">
        <div class="hero-content">
          <div class="hero-badge">
            <span class="badge-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                <path d="M2 17l10 5 10-5"/>
                <path d="M2 12l10 5 10-5"/>
              </svg>
            </span>
            Outil d'annotation
          </div>
          <h1 class="hero-title">
            <span class="gradient-text">Annotez</span> vos fichiers audio
          </h1>
          <p class="hero-subtitle">
            Marquez les segments temporels, assignez des etiquettes et exportez pour l'entrainement de modeles ML.
          </p>
        </div>
        <div class="hero-visual">
          <div class="waveform-preview">
            <div class="wave-bar" *ngFor="let h of wavePreviewBars" [style.height.%]="h" [style.animation-delay.ms]="h * 10"></div>
          </div>
        </div>
      </header>

      <!-- Features Strip -->
      <div class="features-strip" *ngIf="!audioSrc">
        <div class="feature-item" *ngFor="let feature of features; let i = index" [style.animation-delay.ms]="i * 100">
          <div class="feature-icon" [innerHTML]="feature.icon | safeHtml"></div>
          <div class="feature-text">
            <h4>{{ feature.title }}</h4>
            <p>{{ feature.desc }}</p>
          </div>
        </div>
      </div>

      <!-- Upload Section -->
      <div class="upload-section" *ngIf="!audioSrc">
        <!-- Source Tabs -->
        <div class="source-tabs">
          <button class="source-tab" [class.active]="sourceMode === 'local'" (click)="sourceMode = 'local'">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>
              <polyline points="13 2 13 9 20 9"/>
            </svg>
            Fichier local
          </button>
          <button class="source-tab" [class.active]="sourceMode === 's3'" (click)="switchToS3Mode()">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <ellipse cx="12" cy="5" rx="9" ry="3"/>
              <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
              <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
            </svg>
            Charger depuis S3
          </button>
        </div>

        <!-- S3 Browser -->
        <div class="s3-browser" *ngIf="sourceMode === 's3'">
          <div class="s3-browser-header">
            <h3>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <ellipse cx="12" cy="5" rx="9" ry="3"/>
                <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
                <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
              </svg>
              Fichiers audio sur S3
            </h3>
            <button class="refresh-btn" (click)="loadS3Files()" [disabled]="isLoadingS3">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" [class.spinning]="isLoadingS3">
                <polyline points="23 4 23 10 17 10"/>
                <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
              </svg>
            </button>
          </div>

          <!-- Loading State -->
          <div class="s3-loading" *ngIf="isLoadingS3">
            <div class="loading-spinner"></div>
            <span>Chargement des fichiers...</span>
          </div>

          <!-- Error State -->
          <div class="s3-error" *ngIf="s3Error && !isLoadingS3">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <span>{{ s3Error }}</span>
            <button class="retry-btn" (click)="loadS3Files()">Reessayer</button>
          </div>

          <!-- Empty State -->
          <div class="s3-empty" *ngIf="!isLoadingS3 && !s3Error && s3Files.length === 0">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>
              <polyline points="13 2 13 9 20 9"/>
            </svg>
            <span>Aucun fichier audio trouve</span>
            <p>Uploadez des fichiers audio dans le bucket S3 pour les annoter</p>
          </div>

          <!-- Files List -->
          <div class="s3-files-list" *ngIf="!isLoadingS3 && !s3Error && s3Files.length > 0">
            <div class="s3-file-item"
                 *ngFor="let file of s3Files"
                 [class.selected]="selectedS3File?.key === file.key"
                 (click)="selectS3File(file)">
              <div class="file-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M9 18V5l12-2v13"/>
                  <circle cx="6" cy="18" r="3"/>
                  <circle cx="18" cy="16" r="3"/>
                </svg>
              </div>
              <div class="file-info">
                <span class="file-name">{{ file.filename }}</span>
                <span class="file-meta">{{ file.size_formatted }} - {{ formatS3Date(file.last_modified) }}</span>
              </div>
              <div class="file-check" *ngIf="selectedS3File?.key === file.key">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
              </div>
            </div>
          </div>

          <!-- Load Button -->
          <button class="s3-load-btn"
                  *ngIf="selectedS3File && !isLoadingS3"
                  (click)="loadFromS3()"
                  [disabled]="isLoadingS3File">
            <span class="spinner" *ngIf="isLoadingS3File"></span>
            <svg *ngIf="!isLoadingS3File" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            {{ isLoadingS3File ? 'Chargement...' : 'Charger ' + selectedS3File.filename }}
          </button>
        </div>

        <!-- Local File Drop Zone (existing) -->
        <div class="drop-zone" *ngIf="sourceMode === 'local'"
             (click)="fileInput.click()"
             (dragover)="onDragOver($event)"
             (dragleave)="onDragLeave($event)"
             (drop)="onDrop($event)"
             [class.drag-over]="isDragOver">
          <input #fileInput type="file" accept="audio/*" (change)="onFileSelected($event)" hidden>

          <div class="drop-zone-content">
            <div class="upload-visual">
              <div class="upload-circle">
                <div class="upload-icon-wrapper">
                  <svg class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="17 8 12 3 7 8"/>
                    <line x1="12" y1="3" x2="12" y2="15"/>
                  </svg>
                </div>
              </div>
              <div class="pulse-ring"></div>
              <div class="pulse-ring delay-1"></div>
              <div class="pulse-ring delay-2"></div>
            </div>

            <h3 class="drop-title">Deposez votre fichier audio</h3>
            <p class="drop-subtitle">ou cliquez pour parcourir</p>

            <div class="format-tags">
              <span class="format-tag">MP3</span>
              <span class="format-tag">WAV</span>
              <span class="format-tag">OGG</span>
              <span class="format-tag">FLAC</span>
            </div>
          </div>
        </div>

        <!-- Quick Tips -->
        <div class="tips-section">
          <h4>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 16v-4"/>
              <path d="M12 8h.01"/>
            </svg>
            Conseils rapides
          </h4>
          <ul>
            <li>Utilisez des fichiers audio de bonne qualite pour de meilleures annotations</li>
            <li>Les raccourcis clavier accelerent votre workflow</li>
            <li>Exportez en CSV compatible avec le pipeline d'entrainement</li>
          </ul>
        </div>
      </div>

      <!-- Main Annotation Interface -->
      <div class="annotation-workspace" *ngIf="audioSrc">

        <!-- Toolbar -->
        <div class="workspace-toolbar">
          <div class="file-info-bar">
            <div class="file-badge">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 18V5l12-2v13"/>
                <circle cx="6" cy="18" r="3"/>
                <circle cx="18" cy="16" r="3"/>
              </svg>
              <span class="file-name">{{ fileName }}</span>
            </div>

            <!-- Save Status Indicator -->
            <div class="save-status" [class.saving]="persistenceService.isSaving()" [class.saved]="persistenceService.lastSaved()">
              <svg *ngIf="persistenceService.isSaving()" class="save-spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
              </svg>
              <svg *ngIf="!persistenceService.isSaving() && persistenceService.lastSaved()" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
                <polyline points="17 21 17 13 7 13 7 21"/>
                <polyline points="7 3 7 8 15 8"/>
              </svg>
              <span class="save-text">{{ getSaveStatusText() }}</span>
            </div>

            <!-- Undo/Redo Buttons -->
            <div class="undo-redo-group">
              <button class="toolbar-btn undo-btn"
                      (click)="performUndo()"
                      [disabled]="!persistenceService.canUndo()"
                      [title]="persistenceService.getUndoDescription() || 'Annuler (Ctrl+Z)'">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M3 7v6h6"/>
                  <path d="M21 17a9 9 0 0 0-9-9 9 9 0 0 0-6 2.3L3 13"/>
                </svg>
                <span class="undo-count" *ngIf="persistenceService.undoCount() > 0">{{ persistenceService.undoCount() }}</span>
              </button>
              <button class="toolbar-btn redo-btn"
                      (click)="performRedo()"
                      [disabled]="!persistenceService.canRedo()"
                      [title]="persistenceService.getRedoDescription() || 'Refaire (Ctrl+Y)'">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 7v6h-6"/>
                  <path d="M3 17a9 9 0 0 1 9-9 9 9 0 0 1 6 2.3l3 2.7"/>
                </svg>
                <span class="redo-count" *ngIf="persistenceService.redoCount() > 0">{{ persistenceService.redoCount() }}</span>
              </button>
            </div>

            <div class="toolbar-actions">
              <button class="toolbar-btn" (click)="togglePlayPause()" [title]="isPlaying ? 'Pause' : 'Lecture'">
                <svg *ngIf="!isPlaying" viewBox="0 0 24 24" fill="currentColor">
                  <polygon points="5 3 19 12 5 21 5 3"/>
                </svg>
                <svg *ngIf="isPlaying" viewBox="0 0 24 24" fill="currentColor">
                  <rect x="6" y="4" width="4" height="16"/>
                  <rect x="14" y="4" width="4" height="16"/>
                </svg>
              </button>
              <button class="toolbar-btn" (click)="skipBackward()" title="Reculer 5s">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polygon points="11 19 2 12 11 5 11 19"/>
                  <polygon points="22 19 13 12 22 5 22 19"/>
                </svg>
              </button>
              <button class="toolbar-btn" (click)="skipForward()" title="Avancer 5s">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polygon points="13 19 22 12 13 5 13 19"/>
                  <polygon points="2 19 11 12 2 5 2 19"/>
                </svg>
              </button>
              <div class="toolbar-separator"></div>
              <button class="toolbar-btn danger" (click)="resetAudio()" title="Fermer">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="18" y1="6" x2="6" y2="18"/>
                  <line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>
          </div>
        </div>

        <!-- Waveform & Timeline Section -->
        <div class="waveform-section">
          <!-- Zoom Controls -->
          <div class="zoom-controls" *ngIf="audioSrc">
            <button class="zoom-btn" (click)="zoomOut()" [disabled]="zoomLevel <= 1">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35M8 11h6"/>
              </svg>
            </button>
            <span class="zoom-label">{{ zoomLevel }}x</span>
            <button class="zoom-btn" (click)="zoomIn()" [disabled]="zoomLevel >= 10">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35M8 11h6M11 8v6"/>
              </svg>
            </button>
          </div>

          <!-- Scrollable Spectrogram Container -->
          <div class="spectrogram-scroll-container" #spectrogramScroll (scroll)="onSpectrogramScroll($event)">
            <div class="waveform-container" #waveformContainer
                 [style.width.px]="spectrogramWidth"
                 (click)="seekToPosition($event)">

              <!-- Spectrogram Canvas -->
              <canvas #spectrogramCanvas class="spectrogram-canvas"></canvas>

              <!-- Waveform Canvas (overlay) -->
              <canvas #waveformCanvas class="waveform-canvas"></canvas>

              <!-- Loading indicator -->
              <div class="spectrogram-loading" *ngIf="isGeneratingSpectrogram">
                <div class="loading-spinner"></div>
                <span>Generation du spectrogramme...</span>
              </div>

              <!-- Selection Overlay -->
              <div class="selection-overlay"
                   *ngIf="currentStart > 0 || currentEnd > 0"
                   [style.left.%]="getSelectionStart()"
                   [style.width.%]="getSelectionWidth()">
              </div>

              <!-- Playhead -->
              <div class="playhead" [style.left.%]="progressPercent">
                <div class="playhead-line"></div>
                <div class="playhead-time">{{ formatTime(currentTime) }}</div>
              </div>

              <!-- Annotation Markers -->
              <div class="annotation-marker"
                   *ngFor="let ann of annotations"
                   [style.left.%]="getAnnotationPosition(ann.startTime)"
                   [style.width.%]="getAnnotationWidth(ann)"
                   [ngClass]="ann.label"
                   (click)="playAnnotation(ann, $event)">
                <span class="marker-label">{{ getLabelShort(ann.label) }}</span>
              </div>
            </div>
          </div>

          <!-- Time Ruler (also scrollable) -->
          <div class="time-ruler-container">
            <div class="time-ruler" [style.width.px]="spectrogramWidth">
              <span *ngFor="let t of timeMarkers"
                    [style.left.%]="(t / duration) * 100">{{ formatTime(t) }}</span>
            </div>
          </div>

          <!-- Hidden Audio Element -->
          <audio #audioPlayer [src]="audioSrc" (timeupdate)="onTimeUpdate()" (loadedmetadata)="onMetadataLoaded()" (ended)="onEnded()"></audio>
        </div>

        <!-- Main Content Grid -->
        <div class="content-grid">

          <!-- Annotation Form -->
          <div class="annotation-form-card">
            <div class="card-header-modern">
              <div class="header-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 20h9"/>
                  <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
                </svg>
              </div>
              <h3>Nouvelle annotation</h3>
            </div>

            <div class="form-grid">
              <!-- Time Inputs -->
              <div class="time-inputs-row">
                <div class="time-input-group">
                  <label>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <circle cx="12" cy="12" r="10"/>
                      <polyline points="12 6 12 12 16 14"/>
                    </svg>
                    Debut
                  </label>
                  <div class="time-input-wrapper">
                    <input type="number" [(ngModel)]="currentStart" step="0.1" min="0" class="time-input">
                    <button class="set-time-btn" (click)="setStartToCurrent()" title="Utiliser le temps actuel">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="9 11 12 14 22 4"/>
                        <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
                      </svg>
                    </button>
                  </div>
                </div>

                <div class="time-arrow">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="5" y1="12" x2="19" y2="12"/>
                    <polyline points="12 5 19 12 12 19"/>
                  </svg>
                </div>

                <div class="time-input-group">
                  <label>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <circle cx="12" cy="12" r="10"/>
                      <polyline points="12 6 12 12 16 14"/>
                    </svg>
                    Fin
                  </label>
                  <div class="time-input-wrapper">
                    <input type="number" [(ngModel)]="currentEnd" step="0.1" min="0" class="time-input">
                    <button class="set-time-btn" (click)="setEndToCurrent()" title="Utiliser le temps actuel">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="9 11 12 14 22 4"/>
                        <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
                      </svg>
                    </button>
                  </div>
                </div>
              </div>

              <!-- Duration Display -->
              <div class="duration-display" *ngIf="currentEnd > currentStart">
                <span class="duration-label">Duree:</span>
                <span class="duration-value">{{ formatTime(currentEnd - currentStart) }}</span>
              </div>

              <!-- AI Model Selection -->
              <div class="ai-model-selection">
                <label>Modele IA cible</label>
                <div class="ai-model-tabs">
                  <button class="ai-tab"
                          [class.active]="currentAiModel === 'car_detector'"
                          (click)="selectAiModel('car_detector')">
                    <span class="tab-icon">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="1" y="3" width="15" height="13"/>
                        <polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/>
                        <circle cx="5.5" cy="18.5" r="2.5"/>
                        <circle cx="18.5" cy="18.5" r="2.5"/>
                      </svg>
                    </span>
                    <span class="tab-content">
                      <span class="tab-title">AI 1 - Detecteur</span>
                      <span class="tab-desc">Presence vehicule</span>
                    </span>
                  </button>
                  <button class="ai-tab"
                          [class.active]="currentAiModel === 'noisy_car_detector'"
                          (click)="selectAiModel('noisy_car_detector')">
                    <span class="tab-icon">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
                        <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/>
                      </svg>
                    </span>
                    <span class="tab-content">
                      <span class="tab-title">AI 2 - Bruit</span>
                      <span class="tab-desc">Analyse sonore</span>
                    </span>
                  </button>
                </div>
              </div>

              <!-- Label Selection - Dynamic based on AI Model -->
              <div class="label-selection">
                <label>Etiquette {{ currentAiModel === 'car_detector' ? '(Detecteur)' : '(Bruit)' }}</label>
                <div class="label-options">
                  <button class="label-option"
                          *ngFor="let label of getCurrentLabels()"
                          [class.selected]="currentLabel === label.value"
                          [ngClass]="label.value"
                          (click)="currentLabel = label.value">
                    <span class="label-icon" [innerHTML]="label.icon | safeHtml"></span>
                    <span class="label-text">{{ label.text }}</span>
                  </button>
                </div>
              </div>

              <!-- Note Input -->
              <div class="note-input-group">
                <label>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                    <line x1="16" y1="13" x2="8" y2="13"/>
                    <line x1="16" y1="17" x2="8" y2="17"/>
                  </svg>
                  Note (optionnel)
                </label>
                <textarea [(ngModel)]="currentNote" placeholder="Ajoutez des details sur ce segment..." rows="2"></textarea>
              </div>

              <!-- Add Button -->
              <button class="add-annotation-btn" (click)="addAnnotation()" [disabled]="currentEnd <= currentStart">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"/>
                  <line x1="12" y1="8" x2="12" y2="16"/>
                  <line x1="8" y1="12" x2="16" y2="12"/>
                </svg>
                Ajouter l'annotation
              </button>
            </div>
          </div>

          <!-- Annotations List -->
          <div class="annotations-list-card">
            <div class="card-header-modern">
              <div class="header-left">
                <div class="header-icon green">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="8" y1="6" x2="21" y2="6"/>
                    <line x1="8" y1="12" x2="21" y2="12"/>
                    <line x1="8" y1="18" x2="21" y2="18"/>
                    <line x1="3" y1="6" x2="3.01" y2="6"/>
                    <line x1="3" y1="12" x2="3.01" y2="12"/>
                    <line x1="3" y1="18" x2="3.01" y2="18"/>
                  </svg>
                </div>
                <h3>Annotations</h3>
                <span class="count-badge">{{ annotations.length }}</span>
                <span class="count-badge ai1" *ngIf="getAnnotationsByModel('car_detector').length > 0">
                  AI1: {{ getAnnotationsByModel('car_detector').length }}
                </span>
                <span class="count-badge ai2" *ngIf="getAnnotationsByModel('noisy_car_detector').length > 0">
                  AI2: {{ getAnnotationsByModel('noisy_car_detector').length }}
                </span>
              </div>
              <div class="header-actions">
                <!-- Import TextGrid -->
                <button class="import-btn" (click)="textGridInput.click()" title="Importer TextGrid (Praat)">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="17 8 12 3 7 8"/>
                    <line x1="12" y1="3" x2="12" y2="15"/>
                  </svg>
                </button>
                <input #textGridInput type="file" accept=".TextGrid,.textgrid" (change)="onTextGridImport($event)" hidden>

                <!-- Export CSV -->
                <button class="export-btn" (click)="exportAnnotations()" [disabled]="annotations.length === 0" title="Exporter CSV">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="7 10 12 15 17 10"/>
                    <line x1="12" y1="15" x2="12" y2="3"/>
                  </svg>
                  CSV
                </button>

                <!-- Export TextGrid -->
                <button class="export-btn textgrid" (click)="exportTextGrid()" [disabled]="annotations.length === 0" title="Exporter TextGrid (Praat)">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="7 10 12 15 17 10"/>
                    <line x1="12" y1="15" x2="12" y2="3"/>
                  </svg>
                  Praat
                </button>

                <!-- Integrate to AI -->
                <button class="integrate-btn"
                        (click)="integrateToModel()"
                        [disabled]="annotations.length === 0 || isIntegrating"
                        [class.loading]="isIntegrating">
                  <svg *ngIf="!isIntegrating" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                    <path d="M2 17l10 5 10-5"/>
                    <path d="M2 12l10 5 10-5"/>
                  </svg>
                  <span class="spinner" *ngIf="isIntegrating"></span>
                  {{ isIntegrating ? 'Integration...' : 'Integrer IA' }}
                </button>
              </div>
            </div>

            <div class="annotations-list" *ngIf="annotations.length > 0">
              <div class="annotation-item"
                   *ngFor="let ann of annotations; let i = index"
                   [style.animation-delay.ms]="i * 50"
                   [class.playing]="isAnnotationPlaying(ann)"
                   [class.ai1]="ann.aiModel === 'car_detector'"
                   [class.ai2]="ann.aiModel === 'noisy_car_detector'"
                   (click)="playAnnotation(ann, $event)">
                <div class="item-color-bar" [ngClass]="ann.label"></div>
                <div class="item-content">
                  <div class="item-header">
                    <span class="item-time">
                      {{ formatTime(ann.startTime) }} - {{ formatTime(ann.endTime) }}
                    </span>
                    <span class="item-ai-badge" [ngClass]="ann.aiModel">
                      {{ ann.aiModel === 'car_detector' ? 'AI1' : 'AI2' }}
                    </span>
                    <span class="item-label" [ngClass]="ann.label">
                      {{ getLabelText(ann.label) }}
                    </span>
                  </div>
                  <p class="item-note" *ngIf="ann.note">{{ ann.note }}</p>
                </div>
                <button class="delete-btn" (click)="removeAnnotation(i, $event)" title="Supprimer">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"/>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                  </svg>
                </button>
              </div>
            </div>

            <!-- Empty State -->
            <div class="empty-state" *ngIf="annotations.length === 0">
              <div class="empty-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
                </svg>
              </div>
              <h4>Aucune annotation</h4>
              <p>Selectionnez une plage temporelle et ajoutez votre premiere annotation</p>
            </div>
          </div>
        </div>

        <!-- Session Dashboard & Sprint Mode -->
        <div class="session-dashboard">
          <!-- Progress Stats -->
          <div class="dashboard-stats">
            <div class="stat-item">
              <span class="stat-value">{{ annotations.length }}</span>
              <span class="stat-label">Annotations</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">{{ getAnnotatedPercentage() }}%</span>
              <span class="stat-label">Couverture</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">{{ getSessionDuration() }}</span>
              <span class="stat-label">Duree session</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">{{ getAnnotationSpeed() }}</span>
              <span class="stat-label">Vitesse (ann/min)</span>
            </div>
          </div>

          <!-- Sprint Mode Toggle -->
          <div class="sprint-mode-section">
            <button class="sprint-toggle"
                    [class.active]="sprintModeActive"
                    (click)="toggleSprintMode()">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
              </svg>
              <span>Sprint Mode</span>
              <span class="sprint-status">{{ sprintModeActive ? 'ON' : 'OFF' }}</span>
            </button>

            <div class="sprint-settings" *ngIf="sprintModeActive">
              <label>
                <span>Duree segment:</span>
                <select [(ngModel)]="sprintSegmentDuration">
                  <option [value]="2">2s</option>
                  <option [value]="3">3s</option>
                  <option [value]="5">5s</option>
                  <option [value]="10">10s</option>
                </select>
              </label>
              <button class="sprint-start-btn" (click)="startSprintAnnotation()">
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <polygon points="5 3 19 12 5 21 5 3"/>
                </svg>
                Demarrer Sprint
              </button>
            </div>

            <p class="sprint-hint" *ngIf="sprintModeActive">
              Appuyez sur <kbd>1</kbd> ou <kbd>2</kbd> pour annoter rapidement chaque segment
            </p>
          </div>
        </div>

        <!-- Onboarding Overlay -->
        <div class="onboarding-overlay" *ngIf="showOnboarding">
          <div class="onboarding-card" [attr.data-step]="onboardingStep">
            <button class="onboarding-close" (click)="closeOnboarding()">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>

            <div class="onboarding-content" *ngIf="onboardingStep === 0">
              <div class="onboarding-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M9 18V5l12-2v13"/>
                  <circle cx="6" cy="18" r="3"/>
                  <circle cx="18" cy="16" r="3"/>
                </svg>
              </div>
              <h3>Bienvenue dans l'outil d'annotation!</h3>
              <p>Apprenez a annoter des fichiers audio en quelques etapes simples.</p>
            </div>

            <div class="onboarding-content" *ngIf="onboardingStep === 1">
              <div class="onboarding-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"/>
                  <polyline points="12 6 12 12 16 14"/>
                </svg>
              </div>
              <h3>Selectionnez une plage temporelle</h3>
              <p>Utilisez <kbd>S</kbd> pour marquer le debut et <kbd>E</kbd> pour la fin. Ou utilisez <kbd>B</kbd> pour creer des boundaries rapidement.</p>
            </div>

            <div class="onboarding-content" *ngIf="onboardingStep === 2">
              <div class="onboarding-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/>
                  <line x1="4" y1="22" x2="4" y2="15"/>
                </svg>
              </div>
              <h3>Choisissez un label</h3>
              <p>Selectionnez le type d'evenement: vehicule, vehicule bruyant, ou bruit. Utilisez les touches <kbd>1</kbd> et <kbd>2</kbd> pour un etiquetage rapide.</p>
            </div>

            <div class="onboarding-content" *ngIf="onboardingStep === 3">
              <div class="onboarding-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
                </svg>
              </div>
              <h3>Mode Sprint pour aller vite</h3>
              <p>Activez le Sprint Mode pour annoter rapidement segment par segment avec auto-play!</p>
            </div>

            <div class="onboarding-content" *ngIf="onboardingStep === 4">
              <div class="onboarding-icon success">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
              </div>
              <h3>Vous etes pret!</h3>
              <p>Vos annotations sont sauvegardees automatiquement. Exportez en CSV ou TextGrid quand vous avez termine.</p>
            </div>

            <div class="onboarding-nav">
              <div class="onboarding-dots">
                <span *ngFor="let step of [0,1,2,3,4]"
                      class="dot"
                      [class.active]="onboardingStep === step"
                      (click)="goToOnboardingStep(step)"></span>
              </div>
              <div class="onboarding-buttons">
                <button *ngIf="onboardingStep > 0" class="btn-prev" (click)="prevOnboardingStep()">Precedent</button>
                <button *ngIf="onboardingStep < 4" class="btn-next" (click)="nextOnboardingStep()">Suivant</button>
                <button *ngIf="onboardingStep === 4" class="btn-finish" (click)="finishOnboarding()">Commencer!</button>
              </div>
            </div>
          </div>
        </div>

        <!-- Help Button (shows onboarding) -->
        <button class="help-fab" (click)="showOnboarding = true" title="Aide et tutoriel">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
        </button>

        <!-- Keyboard Shortcuts -->
        <div class="shortcuts-bar">
          <div class="shortcuts-row">
            <span class="shortcut"><kbd>Espace</kbd> Play</span>
            <span class="shortcut"><kbd>Shift+Espace</kbd> Play selection</span>
            <span class="shortcut"><kbd>←</kbd><kbd>→</kbd> ±5s</span>
            <span class="shortcut"><kbd>Shift+←</kbd><kbd>→</kbd> ±0.1s</span>
          </div>
          <div class="shortcuts-row">
            <span class="shortcut"><kbd>S</kbd> Debut</span>
            <span class="shortcut"><kbd>E</kbd> Fin</span>
            <span class="shortcut"><kbd>B</kbd> Boundary</span>
            <span class="shortcut"><kbd>Enter</kbd> Ajouter</span>
            <span class="shortcut"><kbd>Esc</kbd> Effacer</span>
          </div>
          <div class="shortcuts-row">
            <span class="shortcut"><kbd>Tab</kbd> Annotation suivante</span>
            <span class="shortcut"><kbd>N</kbd> Segment non annote</span>
            <span class="shortcut"><kbd>1</kbd><kbd>2</kbd> Labels rapides</span>
            <span class="shortcut"><kbd>3</kbd><kbd>4</kbd> Changer AI</span>
          </div>
          <div class="shortcuts-row">
            <span class="shortcut"><kbd>Ctrl+Z</kbd> Annuler</span>
            <span class="shortcut"><kbd>Ctrl+Y</kbd> Refaire</span>
            <span class="shortcut"><kbd>Ctrl+Scroll</kbd> Zoom</span>
          </div>
        </div>
      </div>
    </div>
  `,
  styleUrls: ['./annotation.component.css']
})
export class AnnotationComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('audioPlayer') audioPlayer!: ElementRef<HTMLAudioElement>;
  @ViewChild('waveformContainer') waveformContainer!: ElementRef<HTMLDivElement>;
  @ViewChild('spectrogramCanvas') spectrogramCanvas!: ElementRef<HTMLCanvasElement>;
  @ViewChild('waveformCanvas') waveformCanvas!: ElementRef<HTMLCanvasElement>;
  @ViewChild('spectrogramScroll') spectrogramScroll!: ElementRef<HTMLDivElement>;

  private authService = inject(AuthService);
  private s3AudioService = inject(S3AudioService);
  persistenceService = inject(AnnotationPersistenceService);
  private textGridService = inject(TextGridService);
  private cdr = inject(ChangeDetectorRef);
  private apiUrl = environment.apiUrl;
  private audioContext: AudioContext | null = null;
  private audioBuffer: AudioBuffer | null = null;

  // Delete confirmation
  showDeleteConfirmModal = false;
  annotationToDelete: Annotation | null = null;
  private deleteIndex: number = -1;

  // Auto-save interval
  private autoSaveTimer: ReturnType<typeof setInterval> | null = null;
  private saveStatusTimer: ReturnType<typeof setInterval> | null = null;

  // Quick feedback toast (for keyboard shortcuts)
  showQuickFeedbackToast = false;
  quickFeedbackMessage = '';

  // TextGrid import/export
  showImportModal = false;
  importedAnnotations: AnnotationWithTier[] = [];
  importFileName = '';

  // Multi-tier support
  availableTiers = ['Evenement', 'Intensite', 'Confiance', 'Notes'];
  currentTier = 'Evenement';
  importMode: 'replace' | 'merge' = 'merge';

  // Vague 4: Sprint Mode
  sprintModeActive = false;
  sprintSegmentDuration = 3; // seconds per segment
  private sprintPlaybackEndHandler: (() => void) | null = null;

  // Vague 4: Session Statistics
  sessionStartTime: Date | null = null;
  annotationsThisSession = 0;
  totalAnnotationTime = 0; // in seconds

  // Vague 4: Onboarding
  showOnboarding = false;
  onboardingStep = 0;
  hasSeenOnboarding = false;

  // Interface level (beginner, intermediate, expert)
  interfaceLevel: 'beginner' | 'intermediate' | 'expert' = 'intermediate';

  // S3 Audio Browser
  sourceMode: 'local' | 's3' = 'local';
  s3Files: S3AudioFile[] = [];
  selectedS3File: S3AudioFile | null = null;
  isLoadingS3: boolean = false;
  isLoadingS3File: boolean = false;
  s3Error: string | null = null;

  // Spectrogram settings
  zoomLevel = 1;
  spectrogramWidth = 800; // Base width, will be calculated
  isGeneratingSpectrogram = false;
  private readonly PIXELS_PER_SECOND = 100; // Base pixels per second of audio
  private readonly SPECTROGRAM_HEIGHT = 150;
  private readonly FFT_SIZE = 2048;

  audioSrc: string | null = null;
  audioFile: File | null = null;
  fileName: string = '';

  currentTime: number = 0;
  duration: number = 0;
  isPlaying: boolean = false;
  isDragOver: boolean = false;
  isIntegrating: boolean = false;
  integrationMessage: string = '';

  currentStart: number = 0;
  currentEnd: number = 0;
  currentLabel: string = 'car';
  currentAiModel: 'car_detector' | 'noisy_car_detector' = 'car_detector';
  currentNote: string = '';

  annotations: Annotation[] = [];

  // Waveform data (simulated)
  waveformData: number[] = [];
  wavePreviewBars: number[] = [];
  timeMarkers: number[] = [];

  // Features for the landing state
  features = [
    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>',
      title: 'Import facile',
      desc: 'Glissez-deposez vos fichiers audio'
    },
    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
      title: 'Marquage precis',
      desc: 'Timestamps au dixieme de seconde'
    },
    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/></svg>',
      title: 'Labels flexibles',
      desc: '4 categories pour vos annotations'
    },
    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>',
      title: 'Export CSV',
      desc: 'Compatible pipeline ML'
    }
  ];

  // Label options for AI 1 (Car Detector) - Detects vehicle presence
  carDetectorLabels = [
    { value: 'car', text: 'Vehicule present', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="3" width="15" height="13"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/></svg>' },
    { value: 'noise', text: 'Pas de vehicule', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg>' }
  ];

  // Label options for AI 2 (Noisy Car Detector) - Analyzes if vehicle is noisy
  noisyCarDetectorLabels = [
    { value: 'noisy_car', text: 'Vehicule bruyant', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>' },
    { value: 'car', text: 'Vehicule normal', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="3" width="15" height="13"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/></svg>' }
  ];

  // Combined for backward compatibility
  labelOptions = [...this.carDetectorLabels, ...this.noisyCarDetectorLabels];

  // Session management
  private readonly SESSION_KEY = 'quantnuis_annotation_session';
  showSessionModal = false;
  savedSession: SavedSession | null = null;
  private currentS3Key: string | null = null;
  private visibilityListener: (() => void) | null = null;
  private beforeUnloadListener: ((e: BeforeUnloadEvent) => void) | null = null;

  private keyboardListener: ((e: KeyboardEvent) => void) | null = null;

  constructor() {
    // Generate preview waveform bars
    this.wavePreviewBars = Array.from({ length: 40 }, () => 20 + Math.random() * 60);
  }

  ngOnInit() {
    this.checkForSavedSession();
    this.setupAutoSave();
    this.startSaveStatusUpdater();
  }

  ngAfterViewInit() {
    this.setupKeyboardShortcuts();
  }

  ngOnDestroy() {
    if (this.keyboardListener) {
      document.removeEventListener('keydown', this.keyboardListener);
    }
    if (this.visibilityListener) {
      document.removeEventListener('visibilitychange', this.visibilityListener);
    }
    if (this.beforeUnloadListener) {
      window.removeEventListener('beforeunload', this.beforeUnloadListener);
    }
    if (this.autoSaveTimer) {
      clearInterval(this.autoSaveTimer);
    }
    if (this.saveStatusTimer) {
      clearInterval(this.saveStatusTimer);
    }
    this.persistenceService.endSession();
  }

  // ==============================================================================
  // SESSION MANAGEMENT
  // ==============================================================================

  private setupAutoSave() {
    // Save when tab becomes hidden
    this.visibilityListener = () => {
      if (document.visibilityState === 'hidden') {
        this.saveSession();
        this.saveSessionToIndexedDB();
      }
    };
    document.addEventListener('visibilitychange', this.visibilityListener);

    // Save before page unload
    this.beforeUnloadListener = (e: BeforeUnloadEvent) => {
      this.saveSession();
      this.saveSessionToIndexedDB();
      // No warning needed - everything is auto-saved!
      return;
    };
    window.addEventListener('beforeunload', this.beforeUnloadListener);

    // Auto-save every 30 seconds
    this.autoSaveTimer = setInterval(() => {
      if (this.annotations.length > 0 && this.audioSrc) {
        this.saveSessionToIndexedDB();
      }
    }, 30000);
  }

  private checkForSavedSession() {
    try {
      const saved = localStorage.getItem(this.SESSION_KEY);
      if (saved) {
        this.savedSession = JSON.parse(saved);
        // Only show modal if there are annotations
        if (this.savedSession && this.savedSession.annotations.length > 0) {
          this.showSessionModal = true;
        }
      }
    } catch (e) {
      console.error('Error loading saved session:', e);
      this.clearSavedSession();
    }
  }

  saveSession() {
    if (!this.audioFile && !this.currentS3Key) return;
    if (this.annotations.length === 0) return;

    const session: SavedSession = {
      fileName: this.fileName,
      fileSize: this.audioFile?.size || 0,
      annotations: this.annotations,
      currentTime: this.currentTime,
      currentAiModel: this.currentAiModel,
      savedAt: new Date().toISOString(),
      s3Key: this.currentS3Key || undefined
    };

    try {
      localStorage.setItem(this.SESSION_KEY, JSON.stringify(session));
    } catch (e) {
      console.error('Error saving session:', e);
    }
  }

  async restoreSession() {
    if (!this.savedSession) return;

    this.showSessionModal = false;

    // Restore annotations and settings
    this.annotations = this.savedSession.annotations;
    this.currentAiModel = this.savedSession.currentAiModel;
    this.fileName = this.savedSession.fileName;

    // If it was an S3 file, reload it
    if (this.savedSession.s3Key) {
      this.currentS3Key = this.savedSession.s3Key;
      this.isLoadingS3File = true;
      try {
        const file = await this.s3AudioService.downloadAudioFile(this.savedSession.s3Key);
        this.audioFile = file;
        this.audioSrc = URL.createObjectURL(file);
        setTimeout(() => {
          this.generateSpectrogram();
          // Restore playback position
          if (this.audioPlayer?.nativeElement) {
            this.audioPlayer.nativeElement.currentTime = this.savedSession!.currentTime;
          }
        }, 100);
      } catch (error) {
        console.error('Error restoring S3 file:', error);
        alert('Impossible de recharger le fichier depuis S3. Veuillez le reselectionner.');
        this.sourceMode = 's3';
        this.loadS3Files();
      } finally {
        this.isLoadingS3File = false;
      }
    } else {
      // Local file - user needs to re-select it
      alert(`Veuillez reselectionner le fichier "${this.savedSession.fileName}" pour restaurer votre session.`);
    }
  }

  discardSession() {
    this.showSessionModal = false;
    this.clearSavedSession();
    this.savedSession = null;
  }

  private clearSavedSession() {
    try {
      localStorage.removeItem(this.SESSION_KEY);
    } catch (e) {
      console.error('Error clearing session:', e);
    }
  }

  formatSessionDate(dateStr: string | undefined): string {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  // Save status display
  private startSaveStatusUpdater(): void {
    // Update save status text every second
    this.saveStatusTimer = setInterval(() => {
      this.cdr.detectChanges();
    }, 1000);
  }

  getSaveStatusText(): string {
    if (this.persistenceService.isSaving()) {
      return 'Sauvegarde...';
    }
    const lastSaved = this.persistenceService.lastSaved();
    if (!lastSaved) {
      return '';
    }
    const seconds = Math.floor((Date.now() - lastSaved.getTime()) / 1000);
    if (seconds < 5) return 'Sauvegarde';
    if (seconds < 60) return `Il y a ${seconds}s`;
    if (seconds < 3600) return `Il y a ${Math.floor(seconds / 60)}min`;
    return `Il y a ${Math.floor(seconds / 3600)}h`;
  }

  // Undo/Redo methods
  performUndo(): void {
    const result = this.persistenceService.undo(this.annotations);
    if (result) {
      this.annotations = result.newAnnotations;
      this.saveSessionToIndexedDB();
      this.cdr.detectChanges();
    }
  }

  performRedo(): void {
    const result = this.persistenceService.redo(this.annotations);
    if (result) {
      this.annotations = result.newAnnotations;
      this.saveSessionToIndexedDB();
      this.cdr.detectChanges();
    }
  }

  // Delete confirmation methods
  requestDeleteAnnotation(index: number, event: Event): void {
    event.stopPropagation();
    this.annotationToDelete = this.annotations[index];
    this.deleteIndex = index;
    this.showDeleteConfirmModal = true;
  }

  confirmDelete(): void {
    if (this.deleteIndex >= 0 && this.annotationToDelete) {
      // Record for undo
      this.persistenceService.recordRemove(this.annotationToDelete, this.deleteIndex);

      // Remove annotation
      this.annotations.splice(this.deleteIndex, 1);

      // Auto-save
      this.saveSessionToIndexedDB();
    }
    this.cancelDelete();
  }

  cancelDelete(): void {
    this.showDeleteConfirmModal = false;
    this.annotationToDelete = null;
    this.deleteIndex = -1;
  }

  // Save to IndexedDB
  private async saveSessionToIndexedDB(): Promise<void> {
    if (!this.audioFile && !this.currentS3Key) return;

    const session: AnnotationSession = {
      id: this.persistenceService.generateSessionId(),
      fileName: this.fileName,
      fileSize: this.audioFile?.size || 0,
      annotations: this.annotations,
      currentTime: this.currentTime,
      currentAiModel: this.currentAiModel,
      savedAt: new Date().toISOString(),
      s3Key: this.currentS3Key || undefined,
      duration: this.duration
    };

    try {
      await this.persistenceService.saveSession(session);
    } catch (error) {
      console.error('Error saving to IndexedDB:', error);
    }
  }

  setupKeyboardShortcuts() {
    this.keyboardListener = (e: KeyboardEvent) => {
      // Undo/Redo work even without audio loaded
      if ((e.ctrlKey || e.metaKey) && e.code === 'KeyZ' && !e.shiftKey) {
        e.preventDefault();
        this.performUndo();
        return;
      }
      if ((e.ctrlKey || e.metaKey) && (e.code === 'KeyY' || (e.code === 'KeyZ' && e.shiftKey))) {
        e.preventDefault();
        this.performRedo();
        return;
      }

      if (!this.audioSrc) return;
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      // Handle Shift+Space for play selection
      if (e.code === 'Space' && e.shiftKey) {
        e.preventDefault();
        this.playSelection();
        return;
      }

      switch(e.code) {
        case 'Space':
          e.preventDefault();
          this.togglePlayPause();
          break;
        case 'ArrowLeft':
          e.preventDefault();
          if (e.shiftKey) {
            // Fine navigation: 0.1s
            this.seekRelative(-0.1);
          } else {
            this.skipBackward();
          }
          break;
        case 'ArrowRight':
          e.preventDefault();
          if (e.shiftKey) {
            // Fine navigation: 0.1s
            this.seekRelative(0.1);
          } else {
            this.skipForward();
          }
          break;
        case 'KeyS':
          e.preventDefault();
          this.setStartToCurrent();
          break;
        case 'KeyE':
          e.preventDefault();
          this.setEndToCurrent();
          break;
        case 'KeyB':
          // Create boundary at current position (Praat-style)
          e.preventDefault();
          this.createBoundaryAtPlayhead();
          break;
        case 'Tab':
          // Navigate between annotations
          e.preventDefault();
          if (e.shiftKey) {
            this.navigateToPreviousAnnotation();
          } else {
            this.navigateToNextAnnotation();
          }
          break;
        case 'KeyN':
          // Jump to next unlabeled segment
          e.preventDefault();
          this.jumpToNextUnlabeled();
          break;
        case 'Enter':
          // Quick add annotation if valid
          e.preventDefault();
          if (this.currentEnd > this.currentStart) {
            this.addAnnotation();
          }
          break;
        case 'Escape':
          // Clear selection
          e.preventDefault();
          this.clearSelection();
          break;
        // Quick labels with number keys (1-4)
        case 'Digit1':
        case 'Numpad1':
          e.preventDefault();
          this.applyQuickLabel(0);
          break;
        case 'Digit2':
        case 'Numpad2':
          e.preventDefault();
          this.applyQuickLabel(1);
          break;
        case 'Digit3':
        case 'Numpad3':
          e.preventDefault();
          this.switchAiModelByKey(0); // Switch to AI1
          break;
        case 'Digit4':
        case 'Numpad4':
          e.preventDefault();
          this.switchAiModelByKey(1); // Switch to AI2
          break;
        // Home/End for start/end of audio
        case 'Home':
          e.preventDefault();
          this.seekToStart();
          break;
        case 'End':
          e.preventDefault();
          this.seekToEnd();
          break;
      }
    };
    document.addEventListener('keydown', this.keyboardListener);

    // Setup wheel zoom (Ctrl+Scroll)
    this.setupWheelZoom();
  }

  // ============================================================================
  // VAGUE 2: PRODUCTIVITE PRO - METHODES
  // ============================================================================

  private setupWheelZoom(): void {
    // Will be called after view init when spectrogramScroll is available
    setTimeout(() => {
      if (this.spectrogramScroll?.nativeElement) {
        this.spectrogramScroll.nativeElement.addEventListener('wheel', (e: WheelEvent) => {
          if (e.ctrlKey || e.metaKey) {
            e.preventDefault();
            if (e.deltaY < 0) {
              this.zoomIn();
            } else {
              this.zoomOut();
            }
          }
        }, { passive: false });
      }
    }, 500);
  }

  /**
   * Play only the selected range (Shift+Space)
   */
  playSelection(): void {
    if (this.currentEnd <= this.currentStart) return;

    // Seek to start of selection
    this.audioPlayer.nativeElement.currentTime = this.currentStart;

    // Play
    this.audioPlayer.nativeElement.play();
    this.isPlaying = true;

    // Stop at end of selection
    const checkEnd = () => {
      if (this.currentTime >= this.currentEnd) {
        this.audioPlayer.nativeElement.pause();
        this.isPlaying = false;
        this.audioPlayer.nativeElement.removeEventListener('timeupdate', checkEnd);
      }
    };
    this.audioPlayer.nativeElement.addEventListener('timeupdate', checkEnd);
  }

  /**
   * Seek relative to current position
   */
  seekRelative(deltaSeconds: number): void {
    if (this.audioPlayer) {
      const newTime = Math.max(0, Math.min(this.duration, this.currentTime + deltaSeconds));
      this.audioPlayer.nativeElement.currentTime = newTime;
    }
  }

  /**
   * Create a boundary at current playhead position (Praat B key)
   */
  createBoundaryAtPlayhead(): void {
    const time = parseFloat(this.currentTime.toFixed(2));

    // If no start is set, set start
    if (this.currentStart === 0 && this.currentEnd === 0) {
      this.currentStart = time;
      this.showQuickFeedback('Debut: ' + this.formatTime(time));
    }
    // If start is set but no end, set end
    else if (this.currentStart > 0 && this.currentEnd <= this.currentStart) {
      if (time > this.currentStart) {
        this.currentEnd = time;
        this.showQuickFeedback('Fin: ' + this.formatTime(time));
      } else {
        // If current time is before start, swap
        this.currentEnd = this.currentStart;
        this.currentStart = time;
        this.showQuickFeedback('Segment: ' + this.formatTime(time) + ' - ' + this.formatTime(this.currentEnd));
      }
    }
    // If both are set, start new segment
    else {
      this.currentStart = time;
      this.currentEnd = 0;
      this.showQuickFeedback('Nouveau debut: ' + this.formatTime(time));
    }
  }

  /**
   * Navigate to next annotation (Tab)
   */
  navigateToNextAnnotation(): void {
    if (this.annotations.length === 0) return;

    // Find next annotation after current time
    const nextAnn = this.annotations.find(a => a.startTime > this.currentTime);
    if (nextAnn) {
      this.audioPlayer.nativeElement.currentTime = nextAnn.startTime;
      this.currentStart = nextAnn.startTime;
      this.currentEnd = nextAnn.endTime;
      this.showQuickFeedback('→ ' + this.getLabelText(nextAnn.label));
    } else {
      // Wrap to first annotation
      const first = this.annotations[0];
      this.audioPlayer.nativeElement.currentTime = first.startTime;
      this.currentStart = first.startTime;
      this.currentEnd = first.endTime;
      this.showQuickFeedback('→ ' + this.getLabelText(first.label) + ' (debut)');
    }
  }

  /**
   * Navigate to previous annotation (Shift+Tab)
   */
  navigateToPreviousAnnotation(): void {
    if (this.annotations.length === 0) return;

    // Find previous annotation before current time
    const prevAnn = [...this.annotations].reverse().find(a => a.endTime < this.currentTime);
    if (prevAnn) {
      this.audioPlayer.nativeElement.currentTime = prevAnn.startTime;
      this.currentStart = prevAnn.startTime;
      this.currentEnd = prevAnn.endTime;
      this.showQuickFeedback('← ' + this.getLabelText(prevAnn.label));
    } else {
      // Wrap to last annotation
      const last = this.annotations[this.annotations.length - 1];
      this.audioPlayer.nativeElement.currentTime = last.startTime;
      this.currentStart = last.startTime;
      this.currentEnd = last.endTime;
      this.showQuickFeedback('← ' + this.getLabelText(last.label) + ' (fin)');
    }
  }

  /**
   * Jump to next unlabeled segment (N key)
   */
  jumpToNextUnlabeled(): void {
    // Find gaps between annotations where there's unlabeled audio
    const sortedAnnotations = [...this.annotations].sort((a, b) => a.startTime - b.startTime);

    // Check for gap at the beginning
    if (sortedAnnotations.length === 0 || sortedAnnotations[0].startTime > 0.5) {
      this.audioPlayer.nativeElement.currentTime = 0;
      this.currentStart = 0;
      this.currentEnd = sortedAnnotations.length > 0 ? sortedAnnotations[0].startTime : this.duration;
      this.showQuickFeedback('Segment non annote (debut)');
      return;
    }

    // Find gaps between annotations
    for (let i = 0; i < sortedAnnotations.length - 1; i++) {
      const gap = sortedAnnotations[i + 1].startTime - sortedAnnotations[i].endTime;
      if (gap > 0.5 && sortedAnnotations[i].endTime > this.currentTime) {
        this.audioPlayer.nativeElement.currentTime = sortedAnnotations[i].endTime;
        this.currentStart = sortedAnnotations[i].endTime;
        this.currentEnd = sortedAnnotations[i + 1].startTime;
        this.showQuickFeedback('Segment non annote');
        return;
      }
    }

    // Check for gap at the end
    const lastAnn = sortedAnnotations[sortedAnnotations.length - 1];
    if (lastAnn && lastAnn.endTime < this.duration - 0.5) {
      this.audioPlayer.nativeElement.currentTime = lastAnn.endTime;
      this.currentStart = lastAnn.endTime;
      this.currentEnd = this.duration;
      this.showQuickFeedback('Segment non annote (fin)');
      return;
    }

    this.showQuickFeedback('Tout est annote!');
  }

  /**
   * Apply quick label using number keys (1-2)
   */
  applyQuickLabel(index: number): void {
    const labels = this.getCurrentLabels();
    if (index < labels.length) {
      this.currentLabel = labels[index].value;
      this.showQuickFeedback('Label: ' + labels[index].text);

      // If selection is valid, auto-add annotation
      if (this.currentEnd > this.currentStart) {
        this.addAnnotation();

        // Continue sprint mode if active
        if (this.sprintModeActive) {
          this.continueSprintAfterLabel();
        }
      }
    }
  }

  /**
   * Switch AI model using number keys (3-4)
   */
  switchAiModelByKey(index: number): void {
    const models: Array<'car_detector' | 'noisy_car_detector'> = ['car_detector', 'noisy_car_detector'];
    if (index < models.length) {
      this.selectAiModel(models[index]);
      const name = index === 0 ? 'AI1 - Detecteur' : 'AI2 - Bruit';
      this.showQuickFeedback('Modele: ' + name);
    }
  }

  /**
   * Clear current selection (Escape)
   */
  clearSelection(): void {
    this.currentStart = 0;
    this.currentEnd = 0;
    this.currentNote = '';
    this.showQuickFeedback('Selection effacee');
  }

  /**
   * Seek to start of audio (Home)
   */
  seekToStart(): void {
    this.audioPlayer.nativeElement.currentTime = 0;
  }

  /**
   * Seek to end of audio (End)
   */
  seekToEnd(): void {
    this.audioPlayer.nativeElement.currentTime = this.duration;
  }

  /**
   * Show quick feedback toast
   */
  private quickFeedbackTimeout: ReturnType<typeof setTimeout> | null = null;
  showQuickFeedback(message: string): void {
    this.quickFeedbackMessage = message;
    this.showQuickFeedbackToast = true;

    if (this.quickFeedbackTimeout) {
      clearTimeout(this.quickFeedbackTimeout);
    }

    this.quickFeedbackTimeout = setTimeout(() => {
      this.showQuickFeedbackToast = false;
      this.cdr.detectChanges();
    }, 1500);

    this.cdr.detectChanges();
  }

  get progressPercent(): number {
    return this.duration > 0 ? (this.currentTime / this.duration) * 100 : 0;
  }

  selectAiModel(model: 'car_detector' | 'noisy_car_detector') {
    this.currentAiModel = model;
    // Set default label for the selected model
    this.currentLabel = model === 'car_detector' ? 'car' : 'noisy_car';
  }

  getCurrentLabels() {
    return this.currentAiModel === 'car_detector'
      ? this.carDetectorLabels
      : this.noisyCarDetectorLabels;
  }

  getAnnotationsByModel(model: string): Annotation[] {
    return this.annotations.filter(ann => ann.aiModel === model);
  }

  onFileSelected(event: any) {
    const file = event.target.files[0];
    if (file) {
      this.handleFile(file);
    }
  }

  onDragOver(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = true;
  }

  onDragLeave(event: DragEvent) {
    event.preventDefault();
    this.isDragOver = false;
  }

  onDrop(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = false;
    const file = event.dataTransfer?.files[0];
    if (file) {
      this.handleFile(file);
    }
  }

  handleFile(file: File) {
    // Validation sécurisée des fichiers audio
    const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50 MB pour annotation
    const ALLOWED_TYPES = ['audio/wav', 'audio/mpeg', 'audio/mp3', 'audio/x-m4a', 'audio/mp4', 'audio/x-wav'];
    const ALLOWED_EXTENSIONS = ['.wav', '.mp3', '.m4a', '.mp4'];

    const fileName = file.name.toLowerCase();
    const hasValidExtension = ALLOWED_EXTENSIONS.some(ext => fileName.endsWith(ext));

    if (!hasValidExtension) {
      alert('Extension non autorisée. Formats acceptés: WAV, MP3, M4A');
      return;
    }

    if (!ALLOWED_TYPES.includes(file.type) && !file.type.startsWith('audio/')) {
      alert('Type de fichier non autorisé.');
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      alert('Fichier trop volumineux. Taille maximale: 50 MB');
      return;
    }

    if (file.size === 0) {
      alert('Le fichier est vide.');
      return;
    }

    this.fileName = file.name;
    this.audioFile = file;
    this.audioSrc = URL.createObjectURL(file);
    this.resetForm();

    // Clear S3 key if this is a local file drop (not from S3 load)
    if (!this.isLoadingS3File) {
      this.currentS3Key = null;
    }

    // Clear any previously saved session since we're starting fresh
    this.clearSavedSession();

    // Initialize session tracking
    this.initSessionTracking();

    // Wait for Angular to render the canvas elements (inside *ngIf)
    setTimeout(() => this.generateSpectrogram(), 100);
  }

  // ==============================================================================
  // S3 AUDIO METHODS
  // ==============================================================================

  switchToS3Mode() {
    this.sourceMode = 's3';
    if (this.s3Files.length === 0 && !this.isLoadingS3) {
      this.loadS3Files();
    }
  }

  loadS3Files() {
    if (!this.authService.isAuthenticated()) {
      this.s3Error = 'Vous devez etre connecte pour acceder aux fichiers S3';
      return;
    }

    this.isLoadingS3 = true;
    this.s3Error = null;

    this.s3AudioService.listAudioFiles().subscribe({
      next: (response) => {
        this.s3Files = response.files;
        this.isLoadingS3 = false;
      },
      error: (error) => {
        console.error('Erreur lors du chargement des fichiers S3:', error);
        this.s3Error = error.error?.detail || 'Erreur lors du chargement des fichiers';
        this.isLoadingS3 = false;
      }
    });
  }

  selectS3File(file: S3AudioFile) {
    this.selectedS3File = file;
  }

  async loadFromS3() {
    if (!this.selectedS3File) return;

    this.isLoadingS3File = true;

    try {
      // Save S3 key for session restoration
      this.currentS3Key = this.selectedS3File.key;
      const file = await this.s3AudioService.downloadAudioFile(this.selectedS3File.key);
      this.handleFile(file);
      // Reset S3 selection after successful load
      this.selectedS3File = null;
    } catch (error: any) {
      console.error('Erreur lors du telechargement du fichier:', error);
      alert('Erreur lors du telechargement: ' + (error.message || 'Erreur inconnue'));
      this.currentS3Key = null;
    } finally {
      this.isLoadingS3File = false;
    }
  }

  formatS3Date(dateString: string | null): string {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  async generateSpectrogram() {
    if (!this.audioFile || !this.spectrogramCanvas || !this.waveformCanvas) return;

    this.isGeneratingSpectrogram = true;

    try {
      // Create AudioContext if needed
      if (!this.audioContext) {
        this.audioContext = new AudioContext();
      }

      // Decode audio file
      const arrayBuffer = await this.audioFile.arrayBuffer();
      this.audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);

      // Calculate dimensions
      this.updateSpectrogramWidth();

      // Wait for next frame to ensure canvas is ready
      await new Promise(resolve => setTimeout(resolve, 50));

      // Generate spectrogram
      this.drawSpectrogram();
      this.drawWaveform();

    } catch (error) {
      console.error('Error generating spectrogram:', error);
    } finally {
      this.isGeneratingSpectrogram = false;
    }
  }

  updateSpectrogramWidth() {
    if (!this.audioBuffer) return;
    this.spectrogramWidth = Math.max(800, this.audioBuffer.duration * this.PIXELS_PER_SECOND * this.zoomLevel);
  }

  drawSpectrogram() {
    if (!this.audioBuffer || !this.spectrogramCanvas) return;

    const canvas = this.spectrogramCanvas.nativeElement;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // HiDPI support for sharp rendering
    const dpr = window.devicePixelRatio || 1;
    const displayWidth = this.spectrogramWidth;
    const displayHeight = this.SPECTROGRAM_HEIGHT;

    // Set canvas buffer size (accounting for device pixel ratio)
    canvas.width = displayWidth * dpr;
    canvas.height = displayHeight * dpr;

    // Set display size via CSS
    canvas.style.width = displayWidth + 'px';
    canvas.style.height = displayHeight + 'px';

    // Scale context to match device pixel ratio
    ctx.scale(dpr, dpr);

    // Clear canvas with dark background
    ctx.fillStyle = 'rgb(13, 8, 35)';
    ctx.fillRect(0, 0, displayWidth, displayHeight);

    const audioData = this.audioBuffer.getChannelData(0);

    // Parameters for energy-based spectrogram visualization
    const numColumns = Math.min(displayWidth, 1200);
    const numRows = 64;
    const samplesPerColumn = Math.floor(audioData.length / numColumns);
    const columnWidth = displayWidth / numColumns;
    const rowHeight = displayHeight / numRows;

    // First pass: compute all energies and find max for normalization
    const energyGrid: number[][] = [];
    let maxEnergy = 0;

    for (let col = 0; col < numColumns; col++) {
      const startSample = col * samplesPerColumn;
      const endSample = Math.min(startSample + samplesPerColumn, audioData.length);
      const columnEnergies: number[] = [];

      // Compute RMS energy for this time slice
      let totalRms = 0;
      for (let i = startSample; i < endSample; i++) {
        totalRms += audioData[i] * audioData[i];
      }
      totalRms = Math.sqrt(totalRms / (endSample - startSample));

      // Create pseudo-frequency bands using different window sizes
      for (let row = 0; row < numRows; row++) {
        // Simulate frequency bands: higher rows = higher "frequency" (more rapid variation)
        const windowSize = Math.max(4, Math.floor(samplesPerColumn / (row + 1)));
        const numWindows = Math.floor((endSample - startSample) / windowSize);

        let varianceSum = 0;
        for (let w = 0; w < Math.min(numWindows, 10); w++) {
          const windowStart = startSample + w * windowSize;
          const windowEnd = Math.min(windowStart + windowSize, endSample);

          let localSum = 0;
          let localCount = 0;
          for (let i = windowStart; i < windowEnd; i++) {
            localSum += audioData[i] * audioData[i];
            localCount++;
          }
          if (localCount > 0) {
            varianceSum += Math.sqrt(localSum / localCount);
          }
        }

        const energy = numWindows > 0 ? varianceSum / Math.min(numWindows, 10) : 0;
        columnEnergies.push(energy);
        if (energy > maxEnergy) maxEnergy = energy;
      }

      energyGrid.push(columnEnergies);
    }

    if (maxEnergy === 0) maxEnergy = 1;

    // Second pass: draw with normalized colors
    for (let col = 0; col < numColumns; col++) {
      for (let row = 0; row < numRows; row++) {
        const energy = energyGrid[col][row];

        // Normalize and apply logarithmic scaling
        const normalized = energy / maxEnergy;

        // Convert to dB-like scale for better visibility
        let intensity = 0;
        if (normalized > 0.001) {
          intensity = (Math.log10(normalized * 1000) / 3); // 0-1 range
        }
        intensity = Math.max(0, Math.min(1, intensity));

        // Apply gamma correction for better contrast
        const gamma = 0.7;
        const adjusted = Math.pow(intensity, gamma);

        // Get color from viridis palette
        const color = this.viridisColor(Math.floor(adjusted * 255));

        ctx.fillStyle = `rgb(${color[0]}, ${color[1]}, ${color[2]})`;

        // Draw from bottom (low freq) to top (high freq)
        const y = displayHeight - (row + 1) * rowHeight;
        ctx.fillRect(col * columnWidth, y, columnWidth + 1, rowHeight + 1);
      }
    }

    // Reset scale for future drawings
    ctx.setTransform(1, 0, 0, 1, 0, 0);
  }

  // Viridis colormap - returns [R, G, B]
  viridisColor(value: number): [number, number, number] {
    const t = Math.max(0, Math.min(255, value)) / 255;

    // Viridis color stops - beautiful purple to yellow gradient
    const stops = [
      [0.00, 68, 1, 84],      // Dark purple
      [0.25, 59, 82, 139],    // Blue-purple
      [0.50, 33, 145, 140],   // Teal
      [0.75, 94, 201, 98],    // Green
      [1.00, 253, 231, 37]    // Yellow
    ];

    // Find the two stops to interpolate between
    let lower = stops[0];
    let upper = stops[stops.length - 1];

    for (let i = 0; i < stops.length - 1; i++) {
      if (t >= stops[i][0] && t <= stops[i + 1][0]) {
        lower = stops[i];
        upper = stops[i + 1];
        break;
      }
    }

    // Interpolate
    const range = upper[0] - lower[0];
    const ratio = range > 0 ? (t - lower[0]) / range : 0;

    return [
      Math.round(lower[1] + (upper[1] - lower[1]) * ratio),
      Math.round(lower[2] + (upper[2] - lower[2]) * ratio),
      Math.round(lower[3] + (upper[3] - lower[3]) * ratio)
    ];
  }

  drawWaveform() {
    if (!this.audioBuffer || !this.waveformCanvas) return;

    const canvas = this.waveformCanvas.nativeElement;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // HiDPI support
    const dpr = window.devicePixelRatio || 1;
    const displayWidth = this.spectrogramWidth;
    const displayHeight = this.SPECTROGRAM_HEIGHT;

    canvas.width = displayWidth * dpr;
    canvas.height = displayHeight * dpr;
    canvas.style.width = displayWidth + 'px';
    canvas.style.height = displayHeight + 'px';
    ctx.scale(dpr, dpr);

    const audioData = this.audioBuffer.getChannelData(0);
    const step = Math.ceil(audioData.length / displayWidth);

    ctx.clearRect(0, 0, displayWidth, displayHeight);

    const centerY = displayHeight / 2;

    // Create gradient for waveform (semi-transparent with glow effect)
    const gradient = ctx.createLinearGradient(0, 0, 0, displayHeight);
    gradient.addColorStop(0, 'rgba(255, 255, 255, 0.1)');
    gradient.addColorStop(0.5, 'rgba(255, 255, 255, 0.4)');
    gradient.addColorStop(1, 'rgba(255, 255, 255, 0.1)');

    // Draw filled waveform
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.moveTo(0, centerY);

    // Top half of waveform
    for (let x = 0; x < displayWidth; x++) {
      let max = -1.0;
      for (let j = 0; j < step; j++) {
        const index = x * step + j;
        if (index < audioData.length) {
          const value = Math.abs(audioData[index]);
          if (value > max) max = value;
        }
      }
      const y = centerY - max * centerY * 0.85;
      ctx.lineTo(x, y);
    }

    // Bottom half (mirror)
    for (let x = displayWidth - 1; x >= 0; x--) {
      let max = -1.0;
      for (let j = 0; j < step; j++) {
        const index = x * step + j;
        if (index < audioData.length) {
          const value = Math.abs(audioData[index]);
          if (value > max) max = value;
        }
      }
      const y = centerY + max * centerY * 0.85;
      ctx.lineTo(x, y);
    }

    ctx.closePath();
    ctx.fill();

    // Add subtle center line
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, centerY);
    ctx.lineTo(displayWidth, centerY);
    ctx.stroke();

    ctx.setTransform(1, 0, 0, 1, 0, 0);
  }

  createSpectrogramColorMap(): string[] {
    // Modern Viridis-inspired colormap (perceptually uniform, accessible)
    const colors: string[] = [];

    // Viridis color stops: dark purple -> blue -> teal -> green -> yellow
    const colorStops = [
      { pos: 0.00, r: 13, g: 8, b: 35 },      // Very dark purple (silence)
      { pos: 0.15, r: 68, g: 1, b: 84 },      // Dark purple
      { pos: 0.30, r: 59, g: 82, b: 139 },    // Blue-purple
      { pos: 0.45, r: 33, g: 144, b: 140 },   // Teal
      { pos: 0.60, r: 90, g: 200, b: 101 },   // Green
      { pos: 0.75, r: 170, g: 220, b: 50 },   // Yellow-green
      { pos: 0.90, r: 253, g: 231, b: 37 },   // Bright yellow
      { pos: 1.00, r: 255, g: 255, b: 255 }   // White (loudest)
    ];

    for (let i = 0; i < 256; i++) {
      const t = i / 255;

      // Find the two color stops to interpolate between
      let lower = colorStops[0];
      let upper = colorStops[colorStops.length - 1];

      for (let j = 0; j < colorStops.length - 1; j++) {
        if (t >= colorStops[j].pos && t <= colorStops[j + 1].pos) {
          lower = colorStops[j];
          upper = colorStops[j + 1];
          break;
        }
      }

      // Interpolate between stops
      const range = upper.pos - lower.pos;
      const localT = range > 0 ? (t - lower.pos) / range : 0;

      // Smooth interpolation using ease-in-out
      const smoothT = localT * localT * (3 - 2 * localT);

      const r = Math.round(lower.r + (upper.r - lower.r) * smoothT);
      const g = Math.round(lower.g + (upper.g - lower.g) * smoothT);
      const b = Math.round(lower.b + (upper.b - lower.b) * smoothT);

      colors.push(`rgb(${r},${g},${b})`);
    }
    return colors;
  }

  applyHannWindow(data: Float32Array): Float32Array {
    const windowed = new Float32Array(data.length);
    for (let i = 0; i < data.length; i++) {
      const multiplier = 0.5 * (1 - Math.cos(2 * Math.PI * i / (data.length - 1)));
      windowed[i] = data[i] * multiplier;
    }
    return windowed;
  }

  computeSpectrum(data: Float32Array): Float32Array {
    // Simple DFT for spectrum computation
    const n = data.length;
    const numBins = Math.floor(n / 2);

    // Use only a subset of frequencies for display (128 bins for performance)
    const displayBins = Math.min(numBins, 128);
    const spectrum = new Float32Array(displayBins);

    for (let k = 0; k < displayBins; k++) {
      let real = 0;
      let imag = 0;

      // Map k to frequency bin (focus on lower frequencies where most audio energy is)
      const freqBin = Math.floor(k * numBins / displayBins * 0.5);

      for (let n_idx = 0; n_idx < n; n_idx++) {
        const angle = -2 * Math.PI * freqBin * n_idx / n;
        real += data[n_idx] * Math.cos(angle);
        imag += data[n_idx] * Math.sin(angle);
      }

      // Magnitude with log scale
      const magnitude = Math.sqrt(real * real + imag * imag) / n;
      // Convert to dB scale and normalize (wide range for quiet audio)
      const db = 20 * Math.log10(magnitude + 1e-10);
      // Wide range: -100dB to 0dB for maximum visibility of quiet sounds
      const normalized = Math.max(0, Math.min(1, (db + 100) / 100));
      spectrum[k] = normalized;
    }

    return spectrum;
  }

  // Zoom controls
  zoomIn() {
    if (this.zoomLevel < 10) {
      this.zoomLevel = Math.min(10, this.zoomLevel + 1);
      this.updateSpectrogramWidth();
      this.redrawSpectrogram();
    }
  }

  zoomOut() {
    if (this.zoomLevel > 1) {
      this.zoomLevel = Math.max(1, this.zoomLevel - 1);
      this.updateSpectrogramWidth();
      this.redrawSpectrogram();
    }
  }

  redrawSpectrogram() {
    if (this.audioBuffer) {
      setTimeout(() => {
        this.drawSpectrogram();
        this.drawWaveform();
      }, 50);
    }
  }

  onSpectrogramScroll(event: Event) {
    // Sync time ruler scroll with spectrogram
    const scrollContainer = event.target as HTMLElement;
    const timeRulerContainer = scrollContainer.parentElement?.querySelector('.time-ruler-container') as HTMLElement;
    if (timeRulerContainer) {
      timeRulerContainer.scrollLeft = scrollContainer.scrollLeft;
    }
  }

  // Keep playhead visible during playback
  scrollToPlayhead() {
    if (!this.spectrogramScroll || !this.isPlaying) return;

    const container = this.spectrogramScroll.nativeElement;
    const playheadPosition = (this.currentTime / this.duration) * this.spectrogramWidth;
    const containerWidth = container.clientWidth;
    const scrollLeft = container.scrollLeft;

    // If playhead is outside visible area, scroll to it
    if (playheadPosition < scrollLeft || playheadPosition > scrollLeft + containerWidth - 50) {
      container.scrollLeft = playheadPosition - containerWidth / 2;
    }
  }

  onMetadataLoaded() {
    if (this.audioPlayer) {
      this.duration = this.audioPlayer.nativeElement.duration;
      this.generateTimeMarkers();
    }
  }

  generateTimeMarkers() {
    const markerCount = 6;
    this.timeMarkers = Array.from({ length: markerCount }, (_, i) =>
      (this.duration / (markerCount - 1)) * i
    );
  }

  resetAudio() {
    this.audioSrc = null;
    this.audioFile = null;
    this.fileName = '';
    this.annotations = [];
    this.waveformData = [];
    this.timeMarkers = [];
    this.isPlaying = false;
    this.isIntegrating = false;
    this.integrationMessage = '';
    this.resetForm();
  }

  resetForm() {
    this.currentStart = 0;
    this.currentEnd = 0;
    this.currentNote = '';
    this.currentAiModel = 'car_detector';
    this.currentLabel = 'car';
  }

  onTimeUpdate() {
    if (this.audioPlayer) {
      this.currentTime = this.audioPlayer.nativeElement.currentTime;
      this.scrollToPlayhead();
    }
  }

  onEnded() {
    this.isPlaying = false;
  }

  togglePlayPause() {
    if (this.audioPlayer) {
      if (this.isPlaying) {
        this.audioPlayer.nativeElement.pause();
      } else {
        this.audioPlayer.nativeElement.play();
      }
      this.isPlaying = !this.isPlaying;
    }
  }

  skipForward() {
    if (this.audioPlayer) {
      this.audioPlayer.nativeElement.currentTime = Math.min(
        this.duration,
        this.currentTime + 5
      );
    }
  }

  skipBackward() {
    if (this.audioPlayer) {
      this.audioPlayer.nativeElement.currentTime = Math.max(0, this.currentTime - 5);
    }
  }

  seekToPosition(event: MouseEvent) {
    if (!this.waveformContainer || !this.duration) return;
    const rect = this.waveformContainer.nativeElement.getBoundingClientRect();
    const percent = (event.clientX - rect.left) / rect.width;
    this.audioPlayer.nativeElement.currentTime = percent * this.duration;
  }

  setStartToCurrent() {
    this.currentStart = parseFloat(this.currentTime.toFixed(2));
  }

  setEndToCurrent() {
    this.currentEnd = parseFloat(this.currentTime.toFixed(2));
  }

  addAnnotation() {
    if (this.currentEnd <= this.currentStart) {
      return;
    }

    const newAnnotation: Annotation = {
      id: Date.now(),
      startTime: this.currentStart,
      endTime: this.currentEnd,
      label: this.currentLabel,
      aiModel: this.currentAiModel,
      note: this.currentNote
    };

    this.annotations.push(newAnnotation);
    this.annotations.sort((a, b) => a.startTime - b.startTime);

    // Record for undo
    this.persistenceService.recordAdd(newAnnotation);

    // Update session stats
    this.annotationsThisSession++;
    this.totalAnnotationTime += newAnnotation.endTime - newAnnotation.startTime;

    // Prepare for next annotation
    this.currentStart = this.currentEnd;
    this.currentEnd = parseFloat((this.currentEnd + 1).toFixed(2));
    this.currentNote = '';

    // Auto-save session (both localStorage and IndexedDB)
    this.saveSession();
    this.saveSessionToIndexedDB();
  }

  removeAnnotation(index: number, event: Event) {
    // Use confirmation modal
    this.requestDeleteAnnotation(index, event);
  }

  playAnnotation(ann: Annotation, event: Event) {
    event.stopPropagation();
    if (this.audioPlayer) {
      this.audioPlayer.nativeElement.currentTime = ann.startTime;
      this.audioPlayer.nativeElement.play();
      this.isPlaying = true;
    }
  }

  isAnnotationPlaying(ann: Annotation): boolean {
    return this.isPlaying && this.currentTime >= ann.startTime && this.currentTime <= ann.endTime;
  }

  isBarActive(index: number): boolean {
    const barPercent = (index / this.waveformData.length) * 100;
    return barPercent <= this.progressPercent;
  }

  isBarInSelection(index: number): boolean {
    if (this.duration === 0) return false;
    const barTime = (index / this.waveformData.length) * this.duration;
    return barTime >= this.currentStart && barTime <= this.currentEnd;
  }

  getSelectionStart(): number {
    return this.duration > 0 ? (this.currentStart / this.duration) * 100 : 0;
  }

  getSelectionWidth(): number {
    return this.duration > 0 ? ((this.currentEnd - this.currentStart) / this.duration) * 100 : 0;
  }

  getAnnotationPosition(startTime: number): number {
    return this.duration > 0 ? (startTime / this.duration) * 100 : 0;
  }

  getAnnotationWidth(ann: Annotation): number {
    return this.duration > 0 ? ((ann.endTime - ann.startTime) / this.duration) * 100 : 0;
  }

  getLabelText(label: string): string {
    const found = this.labelOptions.find(l => l.value === label);
    return found ? found.text : label;
  }

  getLabelShort(label: string): string {
    switch(label) {
      case 'car': return 'V';
      case 'noisy_car': return 'B';
      case 'noise': return 'N';
      case 'other': return '?';
      default: return '•';
    }
  }

  formatTime(seconds: number): string {
    const min = Math.floor(seconds / 60);
    const sec = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 10);
    return `${min}:${sec.toString().padStart(2, '0')}.${ms}`;
  }

  formatTimeForCSV(seconds: number): string {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  }

  exportAnnotations() {
    // Export annotations grouped by AI model
    const ai1Annotations = this.getAnnotationsByModel('car_detector');
    const ai2Annotations = this.getAnnotationsByModel('noisy_car_detector');

    if (ai1Annotations.length > 0) {
      this.downloadCSV(ai1Annotations, 'car_detector');
    }

    if (ai2Annotations.length > 0) {
      this.downloadCSV(ai2Annotations, 'noisy_car_detector');
    }

    // If both are empty but there are annotations (old format), export all
    if (ai1Annotations.length === 0 && ai2Annotations.length === 0 && this.annotations.length > 0) {
      this.downloadCSV(this.annotations, 'all');
    }
  }

  private downloadCSV(annotations: Annotation[], modelName: string) {
    let csvContent = "Start,End,Label,Reliability,Note\n";

    annotations.forEach(ann => {
      const start = this.formatTimeForCSV(ann.startTime);
      const end = this.formatTimeForCSV(ann.endTime);
      const note = ann.note ? ann.note.replace(/"/g, '""') : '';
      csvContent += `${start},${end},${ann.label},3,"${note}"\n`;
    });

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    if (link.download !== undefined) {
      const url = URL.createObjectURL(blob);
      const baseName = this.fileName.replace(/\.[^/.]+$/, "");
      link.setAttribute('href', url);
      link.setAttribute('download', `annotations_${baseName}_${modelName}.csv`);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  }

  async integrateToModel() {
    if (!this.audioFile || this.annotations.length === 0) {
      alert('Veuillez charger un fichier audio et ajouter des annotations.');
      return;
    }

    this.isIntegrating = true;
    this.integrationMessage = '';

    try {
      const ai1Annotations = this.getAnnotationsByModel('car_detector');
      const ai2Annotations = this.getAnnotationsByModel('noisy_car_detector');

      const results: string[] = [];

      // Integrate AI 1 annotations
      if (ai1Annotations.length > 0) {
        const result = await this.sendToBackend(ai1Annotations, 'car');
        results.push(`AI 1 (Detecteur): ${result}`);
      }

      // Integrate AI 2 annotations
      if (ai2Annotations.length > 0) {
        const result = await this.sendToBackend(ai2Annotations, 'noisy_car');
        results.push(`AI 2 (Bruit): ${result}`);
      }

      if (results.length === 0) {
        alert('Aucune annotation a integrer. Veuillez selectionner un modele AI pour vos annotations.');
      } else {
        this.integrationMessage = results.join('\n');
        if (environment.production) {
          alert('Demande soumise avec succes!\n\n' + this.integrationMessage + '\n\nVotre demande sera examinee par un administrateur.');
        } else {
          alert('Integration reussie!\n\n' + this.integrationMessage + '\n\nCommandes pour entrainer:\npython -m models.car_detector.train\npython -m models.noisy_car_detector.train');
        }
      }
    } catch (error: any) {
      console.error('Integration error:', error);
      alert('Erreur lors de l\'integration: ' + (error.message || 'Erreur inconnue'));
    } finally {
      this.isIntegrating = false;
    }
  }

  private async sendToBackend(annotations: Annotation[], modelType: 'car' | 'noisy_car'): Promise<string> {
    // Create CSV content
    let csvContent = "Start,End,Label,Reliability,Note\n";
    annotations.forEach(ann => {
      const start = this.formatTimeForCSV(ann.startTime);
      const end = this.formatTimeForCSV(ann.endTime);
      const note = ann.note ? ann.note.replace(/"/g, '""') : '';
      csvContent += `${start},${end},${ann.label},3,"${note}"\n`;
    });

    // Create form data
    const formData = new FormData();
    formData.append('audio', this.audioFile!, this.fileName);
    formData.append('annotations', new Blob([csvContent], { type: 'text/csv' }), `annotations_${modelType}.csv`);
    formData.append('model', modelType);

    // Use annotation-requests on production (requires auth), integrate-annotations on localhost
    const isProduction = environment.production;
    const endpoint = isProduction ? '/annotation-requests' : '/integrate-annotations';

    // Build headers with auth token
    const headers: HeadersInit = {};
    const token = this.authService.getToken();

    if (isProduction) {
      if (!token) {
        throw new Error('Vous devez etre connecte pour soumettre des annotations. Veuillez vous connecter.');
      }
      headers['Authorization'] = `Bearer ${token}`;
    } else if (token) {
      // Include token in dev mode too if available
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${this.apiUrl}${endpoint}`, {
      method: 'POST',
      headers,
      body: formData
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Erreur serveur' }));
      throw new Error(errorData.detail || `Erreur HTTP ${response.status}`);
    }

    const result = await response.json();

    if (isProduction) {
      return `Demande soumise (ID: ${result.request_id || result.id}). En attente d'approbation admin.`;
    }
    return result.message || `${annotations.length} annotations integrees`;
  }

  // ============================================================================
  // VAGUE 3: TEXTGRID IMPORT/EXPORT
  // ============================================================================

  /**
   * Export annotations to Praat TextGrid format
   */
  exportTextGrid(): void {
    if (this.annotations.length === 0 || !this.duration) return;

    // Convert annotations to multi-tier format
    const multiTierAnnotations = this.textGridService.convertToMultiTier(this.annotations);

    // Generate TextGrid content
    const textGridContent = this.textGridService.exportToTextGrid(
      multiTierAnnotations,
      this.duration,
      ['Evenement', 'Confiance', 'Notes']
    );

    // Download file
    const baseName = this.fileName.replace(/\.[^/.]+$/, '');
    this.textGridService.downloadTextGrid(textGridContent, `${baseName}.TextGrid`);

    this.showQuickFeedback('TextGrid exporte!');
  }

  /**
   * Handle TextGrid file import
   */
  async onTextGridImport(event: Event): Promise<void> {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    try {
      this.importFileName = file.name;
      const textGrid = await this.textGridService.readTextGridFile(file);
      this.importedAnnotations = this.textGridService.textGridToAnnotations(textGrid);
      this.showImportModal = true;
    } catch (error) {
      console.error('TextGrid import error:', error);
      alert('Erreur lors de l\'import du fichier TextGrid. Verifiez le format du fichier.');
    }

    // Reset input
    input.value = '';
  }

  /**
   * Confirm TextGrid import
   */
  confirmImport(): void {
    if (this.importedAnnotations.length === 0) return;

    // Convert imported annotations to standard format
    const standardAnnotations: Annotation[] = this.importedAnnotations
      .filter(ann => ann.tier === 'Evenement' || !this.availableTiers.includes(ann.tier))
      .map(ann => ({
        id: ann.id,
        startTime: ann.startTime,
        endTime: ann.endTime,
        label: this.mapVocabularyToLabel(ann.label),
        aiModel: this.guessAiModel(ann.label),
        note: this.findNoteForAnnotation(ann)
      }));

    if (this.importMode === 'replace') {
      // Record for undo (batch)
      for (const ann of this.annotations) {
        this.persistenceService.recordRemove(ann, this.annotations.indexOf(ann));
      }
      this.annotations = standardAnnotations;
    } else {
      // Merge: add new annotations
      for (const ann of standardAnnotations) {
        // Check for overlap with existing
        const overlapping = this.annotations.find(
          existing => !(ann.endTime <= existing.startTime || ann.startTime >= existing.endTime)
        );
        if (!overlapping) {
          this.annotations.push(ann);
          this.persistenceService.recordAdd(ann);
        }
      }
    }

    // Sort by start time
    this.annotations.sort((a, b) => a.startTime - b.startTime);

    // Save and close modal
    this.saveSession();
    this.saveSessionToIndexedDB();
    this.closeImportModal();

    this.showQuickFeedback(`${standardAnnotations.length} annotations importees`);
  }

  /**
   * Cancel TextGrid import
   */
  cancelImport(): void {
    this.closeImportModal();
  }

  /**
   * Close import modal
   */
  private closeImportModal(): void {
    this.showImportModal = false;
    this.importedAnnotations = [];
    this.importFileName = '';
  }

  /**
   * Map vocabulary terms back to internal labels
   */
  private mapVocabularyToLabel(vocabTerm: string): string {
    const mapping: Record<string, string> = {
      'vehicule': 'car',
      'vehicule_bruyant': 'noisy_car',
      'bruit_ambiant': 'noise',
      'silence': 'noise',
      'autre': 'other'
    };
    return mapping[vocabTerm.toLowerCase()] || vocabTerm;
  }

  /**
   * Guess AI model based on label
   */
  private guessAiModel(label: string): 'car_detector' | 'noisy_car_detector' {
    const noisyLabels = ['vehicule_bruyant', 'noisy_car', 'fort', 'tres_fort'];
    return noisyLabels.includes(label.toLowerCase()) ? 'noisy_car_detector' : 'car_detector';
  }

  /**
   * Find note for an annotation from Notes tier
   */
  private findNoteForAnnotation(ann: AnnotationWithTier): string {
    const noteAnn = this.importedAnnotations.find(
      n => n.tier === 'Notes' &&
           Math.abs(n.startTime - ann.startTime) < 0.01 &&
           Math.abs(n.endTime - ann.endTime) < 0.01
    );
    return noteAnn?.label || '';
  }

  // ============================================================================
  // VAGUE 4: SPRINT MODE, DASHBOARD & ONBOARDING
  // ============================================================================

  /**
   * Initialize session tracking
   */
  private initSessionTracking(): void {
    if (!this.sessionStartTime) {
      this.sessionStartTime = new Date();
      this.annotationsThisSession = 0;

      // Check if user has seen onboarding
      this.hasSeenOnboarding = localStorage.getItem('quantnuis_onboarding_seen') === 'true';
      if (!this.hasSeenOnboarding) {
        setTimeout(() => {
          this.showOnboarding = true;
        }, 1000);
      }

      // Load interface level preference
      const savedLevel = localStorage.getItem('quantnuis_interface_level');
      if (savedLevel && ['beginner', 'intermediate', 'expert'].includes(savedLevel)) {
        this.interfaceLevel = savedLevel as 'beginner' | 'intermediate' | 'expert';
      }
    }
  }

  // ==================== DASHBOARD STATS ====================

  /**
   * Get percentage of audio that has been annotated
   */
  getAnnotatedPercentage(): number {
    if (!this.duration || this.duration === 0) return 0;

    let annotatedTime = 0;
    for (const ann of this.annotations) {
      annotatedTime += ann.endTime - ann.startTime;
    }

    return Math.min(100, Math.round((annotatedTime / this.duration) * 100));
  }

  /**
   * Get session duration as formatted string
   */
  getSessionDuration(): string {
    if (!this.sessionStartTime) return '0:00';

    const seconds = Math.floor((Date.now() - this.sessionStartTime.getTime()) / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) {
      return `${hours}h${(minutes % 60).toString().padStart(2, '0')}`;
    }
    return `${minutes}:${(seconds % 60).toString().padStart(2, '0')}`;
  }

  /**
   * Get annotation speed (annotations per minute)
   */
  getAnnotationSpeed(): string {
    if (!this.sessionStartTime || this.annotationsThisSession === 0) return '0';

    const minutes = (Date.now() - this.sessionStartTime.getTime()) / 60000;
    if (minutes < 0.5) return '-';

    const speed = this.annotationsThisSession / minutes;
    return speed.toFixed(1);
  }

  // ==================== SPRINT MODE ====================

  /**
   * Toggle sprint mode on/off
   */
  toggleSprintMode(): void {
    this.sprintModeActive = !this.sprintModeActive;

    if (!this.sprintModeActive && this.sprintPlaybackEndHandler) {
      // Clean up sprint mode
      this.audioPlayer?.nativeElement.removeEventListener('timeupdate', this.sprintPlaybackEndHandler);
      this.sprintPlaybackEndHandler = null;
    }

    this.showQuickFeedback(this.sprintModeActive ? 'Sprint Mode active!' : 'Sprint Mode desactive');
  }

  /**
   * Start sprint annotation workflow
   */
  startSprintAnnotation(): void {
    if (!this.audioSrc || !this.sprintModeActive) return;

    // Find next unannotated segment
    const nextStart = this.findNextUnannotatedTime();
    if (nextStart === null) {
      this.showQuickFeedback('Audio entierement annote!');
      return;
    }

    // Set up segment
    this.currentStart = nextStart;
    this.currentEnd = Math.min(nextStart + this.sprintSegmentDuration, this.duration);

    // Seek and play
    this.audioPlayer.nativeElement.currentTime = this.currentStart;
    this.audioPlayer.nativeElement.play();
    this.isPlaying = true;

    // Set up auto-pause at segment end
    this.setupSprintPlaybackEnd();

    this.showQuickFeedback(`Segment ${this.formatTime(this.currentStart)} - ${this.formatTime(this.currentEnd)}`);
  }

  /**
   * Find next unannotated time position
   */
  private findNextUnannotatedTime(): number | null {
    const sortedAnnotations = [...this.annotations].sort((a, b) => a.startTime - b.startTime);

    // Check from current position
    let checkTime = this.currentTime;

    // Find if current position is inside an annotation
    for (const ann of sortedAnnotations) {
      if (checkTime >= ann.startTime && checkTime < ann.endTime) {
        checkTime = ann.endTime;
      }
    }

    // Check if there's unannotated space
    if (checkTime < this.duration - 0.5) {
      return checkTime;
    }

    // Check from beginning
    checkTime = 0;
    for (const ann of sortedAnnotations) {
      if (ann.startTime > checkTime + 0.5) {
        return checkTime;
      }
      checkTime = Math.max(checkTime, ann.endTime);
    }

    // Check end
    if (checkTime < this.duration - 0.5) {
      return checkTime;
    }

    return null; // Fully annotated
  }

  /**
   * Setup auto-pause when sprint segment ends
   */
  private setupSprintPlaybackEnd(): void {
    if (this.sprintPlaybackEndHandler) {
      this.audioPlayer.nativeElement.removeEventListener('timeupdate', this.sprintPlaybackEndHandler);
    }

    this.sprintPlaybackEndHandler = () => {
      if (this.currentTime >= this.currentEnd - 0.05) {
        this.audioPlayer.nativeElement.pause();
        this.isPlaying = false;
        this.showQuickFeedback('Appuyez sur 1 ou 2 pour etiqueter');
      }
    };

    this.audioPlayer.nativeElement.addEventListener('timeupdate', this.sprintPlaybackEndHandler);
  }

  /**
   * Continue to next sprint segment after labeling
   */
  private continueSprintAfterLabel(): void {
    if (!this.sprintModeActive) return;

    // Small delay then start next segment
    setTimeout(() => {
      this.startSprintAnnotation();
    }, 300);
  }

  // ==================== ONBOARDING ====================

  /**
   * Go to specific onboarding step
   */
  goToOnboardingStep(step: number): void {
    this.onboardingStep = step;
  }

  /**
   * Next onboarding step
   */
  nextOnboardingStep(): void {
    if (this.onboardingStep < 4) {
      this.onboardingStep++;
    }
  }

  /**
   * Previous onboarding step
   */
  prevOnboardingStep(): void {
    if (this.onboardingStep > 0) {
      this.onboardingStep--;
    }
  }

  /**
   * Finish onboarding
   */
  finishOnboarding(): void {
    this.closeOnboarding();
    localStorage.setItem('quantnuis_onboarding_seen', 'true');
    this.hasSeenOnboarding = true;
  }

  /**
   * Close onboarding without marking as seen
   */
  closeOnboarding(): void {
    this.showOnboarding = false;
    this.onboardingStep = 0;
  }

  // ==================== INTERFACE LEVEL ====================

  /**
   * Set interface complexity level
   */
  setInterfaceLevel(level: 'beginner' | 'intermediate' | 'expert'): void {
    this.interfaceLevel = level;
    localStorage.setItem('quantnuis_interface_level', level);
    this.showQuickFeedback(`Mode ${level === 'beginner' ? 'Debutant' : level === 'intermediate' ? 'Intermediaire' : 'Expert'}`);
  }
}
