import { Component, Input, Output, EventEmitter, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
export interface AnalysisResultData {
  hasNoisyVehicle: boolean;
  carDetected: boolean;
  confidence: number;
  message: string;
  error?: boolean;
}

@Component({
  selector: 'app-home-result',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule],
  template: `
    <div class="result-card" *ngIf="result && result.error" role="status" aria-live="polite">
      <div class="verdict-label verdict-label--error">ANALYSE INDISPONIBLE</div>
      <p class="verdict-message">{{ result.message }}</p>
      <p class="verdict-hint">Le serveur d'analyse n'a pas répondu. Réessayez dans quelques secondes — la fonction Lambda peut prendre ~30 s au premier appel (cold start).</p>
    </div>

    <div class="result-card" *ngIf="result && !result.error" [class.noisy]="result.hasNoisyVehicle" [class.safe]="!result.hasNoisyVehicle" role="status" aria-live="polite">

      <!-- Verdict icon -->
      <div class="verdict-icon" aria-hidden="true">
        <svg *ngIf="!result.hasNoisyVehicle" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
          <polyline points="22 4 12 14.01 9 11.01"/>
        </svg>
        <svg *ngIf="result.hasNoisyVehicle" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
      </div>

      <!-- Verdict text -->
      <div class="verdict-label">{{ result.hasNoisyVehicle ? 'VEHICULE BRUYANT DETECTE' : 'VEHICULE CONFORME' }}</div>
      <p class="verdict-message">{{ result.message }}</p>

      <!-- Confidence -->
      <div class="confidence-section">
        <div class="confidence-header">
          <span class="confidence-title">Confiance du modele</span>
          <span class="confidence-value">{{ result.confidence * 100 | number:'1.0-0' }}%</span>
        </div>
        <div class="bar-track" role="progressbar" [attr.aria-valuenow]="result.confidence * 100" aria-valuemin="0" aria-valuemax="100">
          <div class="bar-fill" [style.width.%]="result.confidence * 100"></div>
        </div>
      </div>

      <!-- Models -->
      <div class="models-row">
        <div class="model-chip">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <rect x="3" y="3" width="18" height="18" rx="2"/>
            <path d="M3 9h18M9 21V9"/>
          </svg>
          CarDetector CRNN
        </div>
        <div class="model-chip">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M12 2a10 10 0 0 1 10 10"/>
            <path d="M12 6a6 6 0 0 1 6 6"/>
            <path d="M12 10a2 2 0 0 1 2 2"/>
            <circle cx="12" cy="12" r="1" fill="currentColor"/>
          </svg>
          NoisyCarDetector CNN
        </div>
      </div>
    </div>

    <button class="btn-reset" (click)="resetClicked.emit()" *ngIf="result" aria-label="Lancer une nouvelle analyse">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <path d="M23 4v6h-6M1 20v-6h6"/>
        <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
      </svg>
      Nouvelle analyse
    </button>
  `,
  styles: [`
    @keyframes fadeUp {
      from { opacity: 0; transform: translateY(12px); }
      to   { opacity: 1; transform: translateY(0); }
    }

    .result-card {
      background: var(--bg-elevated);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-lg);
      padding: 2rem;
      text-align: center;
      margin-bottom: 1.25rem;
      animation: fadeUp 0.4s ease;
    }
    .result-card.safe {
      border-color: var(--success);
      border-left: 3px solid var(--success);
    }
    .result-card.noisy {
      border-color: var(--danger);
      border-left: 3px solid var(--danger);
    }

    .verdict-icon {
      width: 48px; height: 48px;
      border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      margin: 0 auto 0.85rem;
    }
    .safe .verdict-icon { background: var(--success-glow); color: var(--success); }
    .noisy .verdict-icon { background: var(--danger-glow); color: var(--danger); }
    .verdict-icon svg { width: 24px; height: 24px; }

    .verdict-label {
      font-size: 0.82rem;
      font-weight: 700;
      letter-spacing: 0.08em;
      margin-bottom: 0.5rem;
      text-transform: uppercase;
    }
    .safe .verdict-label { color: var(--success); }
    .noisy .verdict-label { color: var(--danger); }
    .verdict-label--error { color: var(--danger); }

    .verdict-hint {
      color: var(--text-tertiary);
      font-size: 0.82rem;
      max-width: 420px;
      margin: 0.5rem auto 0;
      line-height: 1.55;
    }

    .verdict-message {
      color: var(--text-secondary);
      font-size: 0.925rem;
      max-width: 420px;
      margin: 0 auto 1.75rem;
      line-height: 1.55;
    }

    .confidence-section { margin-bottom: 1.5rem; text-align: left; max-width: 420px; margin-left: auto; margin-right: auto; }

    .confidence-header {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      margin-bottom: 0.4rem;
    }
    .confidence-title {
      font-size: 0.72rem; color: var(--text-tertiary);
      font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em;
    }
    .confidence-value {
      font-size: 0.95rem; font-weight: 700;
      color: var(--text-primary);
      font-variant-numeric: tabular-nums;
      letter-spacing: -0.01em;
    }

    .bar-track {
      height: 4px; background: var(--border-color);
      border-radius: 100px; overflow: hidden;
    }
    .bar-fill { height: 100%; border-radius: 100px; transition: width 1.2s cubic-bezier(0.16,1,0.3,1); }
    .safe .bar-fill { background: var(--success); }
    .noisy .bar-fill { background: var(--danger); }

    .models-row { display: flex; gap: 0.5rem; justify-content: center; flex-wrap: wrap; }

    .model-chip {
      display: inline-flex; align-items: center; gap: 0.4rem;
      background: transparent;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      padding: 0.3rem 0.65rem;
      font-size: 0.72rem;
      color: var(--text-secondary);
      font-weight: 500;
      font-variant-numeric: tabular-nums;
    }
    .model-chip svg { width: 12px; height: 12px; flex-shrink: 0; }

    .btn-reset {
      background: transparent;
      border: 1px solid var(--border-color-hover);
      color: var(--text-primary);
      padding: 0.625rem 1.5rem;
      border-radius: var(--radius-md);
      font-weight: 500;
      font-size: 0.875rem;
      cursor: pointer;
      display: flex; align-items: center; justify-content: center; gap: 0.5rem;
      margin: 0 auto 2rem;
      transition: background 0.15s, border-color 0.15s, color 0.15s;
      font-family: inherit;
    }
    .btn-reset svg { width: 15px; height: 15px; transition: transform 0.3s ease; color: var(--text-tertiary); }
    .btn-reset:hover {
      background: var(--bg-surface);
      border-color: var(--border-strong);
    }
    .btn-reset:hover svg { transform: rotate(-180deg); color: var(--accent); }

    @media (max-width: 600px) {
      .result-card { padding: 1.5rem; }
      .verdict-label { font-size: 0.95rem; }
    }
  `]
})
export class HomeResultComponent {
  @Input() result: AnalysisResultData | null = null;
  @Output() resetClicked = new EventEmitter<void>();
}
