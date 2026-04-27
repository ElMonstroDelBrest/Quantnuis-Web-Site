import { Component, Output, EventEmitter, ViewChild, ElementRef, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-home-upload',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule],
  template: `
    <div class="upload-section">
      <div class="section-header">
        <h2>Deposez votre fichier audio</h2>
      </div>

      <div
        class="dropzone"
        [class.active]="isDragging"
        [class.has-file]="selectedFile"
        (dragover)="onDragOver($event)"
        (dragleave)="onDragLeave($event)"
        (drop)="onDrop($event)"
        (click)="fileInput.click()"
        role="button"
        tabindex="0"
        [attr.aria-label]="selectedFile ? 'Fichier selectionne: ' + selectedFile.name : null"
        (keydown.enter)="fileInput.click()"
        (keydown.space)="fileInput.click(); $event.preventDefault()"
      >
        <input type="file" #fileInput (change)="onFileSelected($event)" accept="audio/*" hidden>

        <div class="dropzone-content" *ngIf="!selectedFile">
          <div class="upload-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M12 16V4m0 0L8 8m4-4l4 4M20 16v4a2 2 0 01-2 2H6a2 2 0 01-2-2v-4"/>
            </svg>
          </div>
          <h3>Glissez-deposez votre fichier</h3>
          <p>ou cliquez pour parcourir</p>
          <span class="file-hint">WAV, MP3, M4A - Max 10MB</span>
        </div>

        <div class="file-preview" *ngIf="selectedFile" (click)="$event.stopPropagation()">
          <div class="file-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2z"/>
            </svg>
          </div>
          <div class="file-info">
            <span class="file-name">{{ selectedFile.name }}</span>
            <span class="file-size">{{ (selectedFile.size / 1024 / 1024) | number:'1.2-2' }} MB</span>
          </div>
          <button class="btn-remove" (click)="removeFile(); $event.stopPropagation()" aria-label="Retirer le fichier">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
      </div>

      <button
        class="btn-analyze"
        [disabled]="!selectedFile"
        (click)="analyzeClicked.emit()"
      >
        <span class="btn-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
          </svg>
        </span>
        <span>Lancer l'analyse</span>
      </button>

      <div class="demo-divider" aria-hidden="true">
        <span>ou</span>
      </div>

      <button class="btn-demo" (click)="demoClicked.emit()">
        <span class="demo-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="5 3 19 12 5 21 5 3"/>
          </svg>
        </span>
        <span class="demo-text">
          <strong>Voir un exemple d'analyse</strong>
          <small>Sans inscription, resultat instantane</small>
        </span>
      </button>
    </div>
  `,
  styles: [`
    .upload-section { max-width: 760px; margin: 0 auto; }

    .section-header { margin-bottom: 1.5rem; }
    .section-header h2 {
      font-size: 1.25rem; font-weight: 600;
      color: var(--text-primary); margin: 0;
      letter-spacing: -0.015em;
    }

    .dropzone {
      background: var(--bg-surface);
      border: 1px dashed var(--border-color-hover);
      border-radius: var(--radius-lg);
      padding: 2.5rem 1.5rem;
      text-align: center;
      transition: border-color 0.15s ease, background-color 0.15s ease;
      cursor: pointer;
    }
    .dropzone:hover, .dropzone.active {
      border-color: var(--accent);
      background: var(--accent-subtle-bg);
    }
    .dropzone.has-file {
      border-style: solid;
      border-color: var(--accent);
      background: var(--accent-subtle-bg);
    }

    .dropzone-content { display: flex; flex-direction: column; align-items: center; gap: 0.75rem; }

    .upload-icon {
      width: 56px; height: 56px;
      background: transparent;
      border: 1px solid var(--border-color-hover);
      border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      color: var(--text-secondary);
    }
    .upload-icon svg { width: 24px; height: 24px; }

    .dropzone h3 { font-size: 1.05rem; font-weight: 600; color: var(--text-primary); margin: 0; letter-spacing: -0.01em; }
    .dropzone p { color: var(--text-secondary); font-size: 0.875rem; margin: 0; }

    .file-hint { font-size: 0.75rem; color: var(--text-tertiary); margin-top: 0.35rem; }

    .file-preview {
      display: flex; align-items: center; gap: 0.85rem;
      background: var(--bg-elevated);
      padding: 1rem 1.1rem; border-radius: var(--radius-md);
      width: 100%; max-width: 420px; margin: 0 auto;
      border: 1px solid var(--accent);
    }

    .file-icon {
      width: 40px; height: 40px;
      background: var(--accent);
      border-radius: var(--radius-sm);
      display: flex; align-items: center; justify-content: center; flex-shrink: 0;
    }
    .file-icon svg { width: 20px; height: 20px; color: var(--bg-page); }

    .file-info { flex: 1; text-align: left; min-width: 0; }
    .file-name {
      display: block; font-weight: 600; font-size: 0.9rem;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
      color: var(--text-primary);
    }
    .file-size { font-size: 0.78rem; color: var(--text-tertiary); }

    .btn-remove {
      width: 30px; height: 30px;
      background: transparent;
      border: 1px solid var(--border-color);
      border-radius: 50%;
      color: var(--text-tertiary); cursor: pointer;
      transition: color 0.15s ease, border-color 0.15s ease, background-color 0.15s ease;
      display: flex; align-items: center; justify-content: center; flex-shrink: 0;
    }
    .btn-remove svg { width: 14px; height: 14px; }
    .btn-remove:hover { background: var(--danger); color: white; border-color: var(--danger); }

    .btn-analyze {
      width: 100%;
      background: var(--accent); color: var(--bg-page);
      border: 1px solid var(--accent);
      padding: 0.85rem 1.5rem; border-radius: var(--radius-md);
      font-size: 0.975rem; font-weight: 600; cursor: pointer;
      margin-top: 1.5rem;
      display: flex; align-items: center; justify-content: center; gap: 0.65rem;
      transition: background-color 0.15s ease, border-color 0.15s ease;
      font-family: inherit;
    }
    .btn-analyze:hover:not(:disabled) {
      background: var(--accent-hover);
      border-color: var(--accent-hover);
    }
    .btn-analyze:disabled { opacity: 0.45; cursor: not-allowed; }
    .btn-icon svg { width: 18px; height: 18px; }

    .demo-divider {
      display: flex; align-items: center; gap: 1rem; margin: 1.25rem 0;
      color: var(--text-tertiary);
      font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em;
    }
    .demo-divider::before, .demo-divider::after {
      content: ''; flex: 1; height: 1px; background: var(--border-color);
    }

    .btn-demo {
      width: 100%;
      display: flex; align-items: center; justify-content: center; gap: 0.75rem;
      padding: 0.85rem 1.25rem;
      background: transparent;
      border: 1px solid var(--border-color-hover);
      border-radius: var(--radius-md);
      cursor: pointer; transition: border-color 0.15s ease, background-color 0.15s ease;
      color: var(--text-primary);
      font-family: inherit;
    }
    .btn-demo:hover {
      background: var(--bg-surface);
      border-color: var(--border-strong);
    }

    .demo-icon { width: 18px; height: 18px; color: var(--accent); }
    .demo-icon svg { width: 100%; height: 100%; }

    .demo-text { display: flex; flex-direction: column; text-align: left; gap: 0.1rem; }
    .demo-text strong { color: var(--text-primary); font-size: 0.9rem; font-weight: 600; }
    .demo-text small { color: var(--text-tertiary); font-size: 0.75rem; }

    @media (max-width: 768px) { .dropzone { padding: 2rem 1.25rem; } }
    @media (max-width: 600px) {
      .btn-analyze { padding: 0.75rem; font-size: 0.9rem; }
      .upload-icon { width: 48px; height: 48px; }
      .upload-icon svg { width: 20px; height: 20px; }
    }
  `]
})
export class HomeUploadComponent {
  @Output() fileSelected = new EventEmitter<File>();
  @Output() analyzeClicked = new EventEmitter<void>();
  @Output() demoClicked = new EventEmitter<void>();
  @Output() fileRemoved = new EventEmitter<void>();

  @ViewChild('fileInput') fileInputRef!: ElementRef<HTMLInputElement>;

  triggerFileInput() {
    this.fileInputRef?.nativeElement.click();
  }

  isDragging = false;
  selectedFile: File | null = null;

  private readonly MAX_FILE_SIZE = 10 * 1024 * 1024;
  private readonly ALLOWED_EXTENSIONS = ['.wav', '.mp3', '.m4a', '.mp4'];

  onDragOver(event: DragEvent) { event.preventDefault(); this.isDragging = true; }
  onDragLeave(event: DragEvent) { event.preventDefault(); this.isDragging = false; }

  onDrop(event: DragEvent) {
    event.preventDefault();
    this.isDragging = false;
    if (event.dataTransfer?.files.length) this.handleFile(event.dataTransfer.files[0]);
  }

  onFileSelected(event: Event) {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (file) this.handleFile(file);
  }

  handleFile(file: File) {
    const fileName = file.name.toLowerCase();
    const hasValidExtension = this.ALLOWED_EXTENSIONS.some(ext => fileName.endsWith(ext));

    if (!hasValidExtension) { alert('Extension non autorisée. Formats acceptés : WAV, MP3, M4A'); return; }
    if (!file.type.startsWith('audio/')) { alert('Type de fichier non autorisé. Veuillez sélectionner un fichier audio.'); return; }
    if (file.size > this.MAX_FILE_SIZE) { alert('Fichier trop volumineux. Taille maximale: 10 MB'); return; }
    if (file.size === 0) { alert('Le fichier est vide.'); return; }

    this.selectedFile = file;
    this.fileSelected.emit(file);
  }

  removeFile() {
    this.selectedFile = null;
    this.fileRemoved.emit();
  }
}
