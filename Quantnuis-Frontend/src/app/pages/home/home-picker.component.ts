import { Component, EventEmitter, Output, OnInit, ChangeDetectionStrategy, ChangeDetectorRef, OnDestroy, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';

export interface DemoAudio {
  id: string;
  file: string;
  label: string;
  description: string;
  icon?: 'car' | 'sport' | 'moto' | 'street';
}

interface DemoAudiosManifest {
  audios: DemoAudio[];
}

@Component({
  selector: 'app-home-picker',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule],
  template: `
    <div class="picker-section">

      <div *ngIf="loading" class="loading-state" aria-live="polite">
        <div class="spinner" aria-hidden="true"></div>
        <span>Chargement des extraits…</span>
      </div>

      <div *ngIf="error" class="error-state" role="alert">
        <p>Impossible de charger la liste des extraits.</p>
        <button class="btn-retry" (click)="reload()">Réessayer</button>
      </div>

      <ng-container *ngIf="!loading && !error">
        <!-- Column labels -->
        <div class="specimen-header" aria-hidden="true">
          <span class="sh-num">№</span>
          <span class="sh-label">Extrait</span>
          <span class="sh-actions"></span>
        </div>

        <!-- Specimen list -->
        <div class="specimen-list" role="radiogroup" aria-label="Extraits audio disponibles">
          <div
            *ngFor="let audio of audios; let i = index; trackBy: trackById"
            class="specimen-row"
            [class.selected]="selectedId === audio.id"
            role="radio"
            [attr.aria-checked]="selectedId === audio.id"
            (click)="select(audio)"
            tabindex="0"
            (keydown.enter)="select(audio)"
            (keydown.space)="select(audio); $event.preventDefault()"
          >
            <!-- Col 1: row number -->
            <span class="specimen-num" aria-hidden="true">{{ (i + 1).toString().padStart(2, '0') }}</span>

            <!-- Col 2: label + description -->
            <span class="specimen-info">
              <span class="specimen-label">{{ audio.label }}</span>
              <span class="specimen-desc">{{ audio.description }}</span>
            </span>

            <!-- Col 3: actions -->
            <span class="specimen-actions" (click)="$event.stopPropagation()">
              <!-- Play / Pause -->
              <button
                type="button"
                class="btn-play"
                [class.playing]="playingId === audio.id"
                (click)="togglePreview(audio, $event)"
                [attr.aria-label]="playingId === audio.id ? 'Mettre en pause ' + audio.label : 'Écouter ' + audio.label"
              >
                <svg *ngIf="playingId !== audio.id" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" width="10" height="10">
                  <polygon points="6 4 20 12 6 20 6 4"/>
                </svg>
                <svg *ngIf="playingId === audio.id" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" width="10" height="10">
                  <rect x="6" y="4" width="4" height="16"/>
                  <rect x="14" y="4" width="4" height="16"/>
                </svg>
              </button>
            </span>
          </div>
        </div>

        <!-- Global analyze button -->
        <div class="picker-footer">
          <button
            class="btn-analyze"
            [disabled]="!selectedId || preparing"
            (click)="confirmSelection()"
            type="button"
          >
            <span *ngIf="!preparing">→ Lancer l'analyse</span>
            <span *ngIf="preparing" class="spinner-inline" aria-hidden="true"></span>
            <span *ngIf="preparing">Préparation…</span>
          </button>

          <button class="btn-upload-link" (click)="uploadRequested.emit()" type="button">
            Ou téléverser votre propre fichier audio
          </button>
        </div>
      </ng-container>

      <audio #previewPlayer (ended)="onPreviewEnded()" (error)="onPreviewError()" preload="none"></audio>
    </div>
  `,
  styles: [`
    .picker-section { max-width: 800px; margin: 0 auto; }

    .loading-state, .error-state {
      display: flex; flex-direction: column; align-items: center; gap: 0.75rem;
      padding: 2.5rem 1.5rem;
      color: var(--text-secondary);
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      font-family: 'Inter', system-ui, sans-serif;
    }
    .spinner {
      width: 24px; height: 24px;
      border: 2px solid var(--border-color);
      border-top-color: var(--accent);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    .spinner-inline {
      display: inline-block;
      width: 14px; height: 14px;
      border: 2px solid var(--border-color-hover);
      border-top-color: var(--accent);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    .btn-retry {
      background: transparent;
      color: var(--accent);
      border: 1px solid var(--border-color-hover);
      padding: 0.4rem 0.9rem;
      border-radius: var(--radius-sm);
      font-weight: 500;
      cursor: pointer;
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 0.82rem;
    }
    .btn-retry:hover { border-color: var(--accent); background: var(--accent-subtle-bg); }

    /* Column header */
    .specimen-header {
      display: grid;
      grid-template-columns: 2rem 1fr auto;
      gap: 0.5rem;
      padding: 0 0.5rem 0.5rem;
      border-bottom: 1px solid var(--border-color);
      margin-bottom: 0;
    }
    .sh-num, .sh-label, .sh-actions {
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 0.7rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--text-tertiary);
    }

    /* Specimen list */
    .specimen-list {
      display: flex;
      flex-direction: column;
      margin-bottom: 1.5rem;
    }

    .specimen-row {
      display: grid;
      grid-template-columns: 2rem 1fr auto;
      gap: 0.5rem;
      align-items: center;
      padding: 0.85rem 0.5rem;
      border-bottom: 1px solid var(--border-color);
      cursor: pointer;
      transition: background-color 0.1s ease;
      position: relative;
      border-left: 2px solid transparent;
      outline: none;
    }
    .specimen-row:first-child { border-top: none; }
    .specimen-row:hover { background: var(--bg-surface); }
    .specimen-row:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }

    .specimen-row.selected {
      border-left-color: var(--accent);
      background: var(--accent-subtle-bg);
    }

    /* Col 1: number */
    .specimen-num {
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 0.78rem;
      font-weight: 500;
      color: var(--text-tertiary);
      font-variant-numeric: tabular-nums;
      line-height: 1;
    }

    /* Col 2: label + desc */
    .specimen-info {
      display: flex;
      flex-direction: column;
      gap: 0.2rem;
      min-width: 0;
    }
    .specimen-label {
      font-family: 'Newsreader', 'Charter', 'Georgia', serif;
      font-size: 1rem;
      font-weight: 500;
      color: var(--text-primary);
      line-height: 1.3;
    }
    .specimen-desc {
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 0.78rem;
      color: var(--text-tertiary);
      line-height: 1.35;
    }

    /* Col 3: actions */
    .specimen-actions {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      flex-shrink: 0;
    }

    .btn-play {
      width: 28px; height: 28px;
      border-radius: 50%;
      background: transparent;
      border: 1px solid var(--border-color-hover);
      color: var(--text-secondary);
      display: flex; align-items: center; justify-content: center;
      cursor: pointer;
      transition: color 0.15s ease, background-color 0.15s ease, border-color 0.15s ease;
      flex-shrink: 0;
    }
    .btn-play:hover { background: var(--bg-surface-hover); border-color: var(--border-strong); color: var(--text-primary); }
    .btn-play.playing { background: var(--accent-subtle-bg); border-color: var(--accent); color: var(--accent); }
    .btn-play:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

    /* Footer */
    .picker-footer {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.75rem;
    }

    .btn-analyze {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      padding: 0.55rem 1.25rem;
      background: transparent;
      border: 1px solid var(--border-color-hover);
      border-radius: var(--radius-sm);
      color: var(--text-primary);
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 0.875rem;
      font-weight: 500;
      cursor: pointer;
      transition: border-color 0.15s ease, background-color 0.15s ease, color 0.15s ease;
      min-width: 160px;
    }
    .btn-analyze:hover:not(:disabled) {
      border-color: var(--accent);
      background: var(--accent-subtle-bg);
      color: var(--accent);
    }
    .btn-analyze:disabled { opacity: 0.4; cursor: not-allowed; }

    .btn-upload-link {
      background: none; border: none;
      color: var(--text-tertiary);
      font-size: 0.8rem; cursor: pointer;
      text-decoration: underline; text-underline-offset: 3px;
      text-decoration-color: var(--border-color-hover);
      padding: 0.2rem 0.5rem;
      font-family: 'Inter', system-ui, sans-serif;
      transition: color 0.15s ease;
    }
    .btn-upload-link:hover {
      color: var(--accent);
      text-decoration-color: var(--accent);
    }

    @media (max-width: 600px) {
      .specimen-row { grid-template-columns: 1.75rem 1fr auto; }
      .specimen-label { font-size: 0.9rem; }
    }
  `]
})
export class HomePickerComponent implements OnInit, OnDestroy {
  @Output() fileSelected = new EventEmitter<File>();
  @Output() analyzeClicked = new EventEmitter<void>();
  @Output() uploadRequested = new EventEmitter<void>();

  @ViewChild('previewPlayer') previewPlayer!: ElementRef<HTMLAudioElement>;

  audios: DemoAudio[] = [];
  selectedId: string | null = null;
  playingId: string | null = null;
  loading = true;
  error = false;
  preparing = false;

  private readonly manifestUrl = '/demo-audios/manifest.json';

  constructor(private http: HttpClient, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    this.reload();
  }

  ngOnDestroy() {
    this.stopPreview();
  }

  trackById = (_: number, a: DemoAudio) => a.id;

  reload() {
    this.loading = true;
    this.error = false;
    this.cdr.markForCheck();
    this.http.get<DemoAudiosManifest>(this.manifestUrl).subscribe({
      next: (m) => {
        this.audios = m?.audios || [];
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.loading = false;
        this.error = true;
        this.cdr.markForCheck();
      }
    });
  }

  select(audio: DemoAudio) {
    this.selectedId = audio.id;
    this.cdr.markForCheck();
  }

  togglePreview(audio: DemoAudio, event: Event) {
    event.stopPropagation();
    const player = this.previewPlayer?.nativeElement;
    if (!player) return;

    if (this.playingId === audio.id) {
      player.pause();
      this.playingId = null;
    } else {
      player.src = `/demo-audios/${audio.file}`;
      player.currentTime = 0;
      player.play().then(() => {
        this.playingId = audio.id;
        this.cdr.markForCheck();
      }).catch(() => {
        this.playingId = null;
        this.cdr.markForCheck();
      });
    }
    this.cdr.markForCheck();
  }

  onPreviewEnded() {
    this.playingId = null;
    this.cdr.markForCheck();
  }

  onPreviewError() {
    this.playingId = null;
    this.cdr.markForCheck();
  }

  async confirmSelection() {
    if (!this.selectedId) return;
    const audio = this.audios.find(a => a.id === this.selectedId);
    if (!audio) return;

    this.stopPreview();
    this.preparing = true;
    this.cdr.markForCheck();

    try {
      const response = await fetch(`/demo-audios/${audio.file}`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const blob = await response.blob();
      const mime = inferMime(audio.file);
      const file = new File([blob], audio.file, { type: mime });
      this.fileSelected.emit(file);
      this.analyzeClicked.emit();
    } catch {
      this.error = true;
    } finally {
      this.preparing = false;
      this.cdr.markForCheck();
    }
  }

  private stopPreview() {
    const player = this.previewPlayer?.nativeElement;
    if (player && !player.paused) player.pause();
    this.playingId = null;
  }
}

function inferMime(filename: string): string {
  const ext = filename.toLowerCase().split('.').pop();
  const map: Record<string, string> = {
    wav: 'audio/wav',
    mp3: 'audio/mpeg',
    ogg: 'audio/ogg',
    flac: 'audio/flac',
    m4a: 'audio/mp4',
    mp4: 'audio/mp4'
  };
  return map[ext || ''] || 'audio/wav';
}
