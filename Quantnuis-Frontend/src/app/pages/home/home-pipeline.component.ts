import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

export interface PipelineStep {
  id: string;
  label: string;
  icon: string;
  status: 'waiting' | 'processing' | 'completed' | 'error';
  result?: string;
}

@Component({
  selector: 'app-home-pipeline',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="pipeline-section">
      <div class="pipeline-header">
        <span class="pipeline-badge" [class.done]="!isAnalyzing">
          {{ !isAnalyzing ? 'Terminé' : 'En cours' }}
        </span>
        <h2>{{ !isAnalyzing ? 'Analyse terminée' : 'Analyse en cours...' }}</h2>
        <p class="pipeline-filename" *ngIf="fileName">{{ fileName }}</p>
      </div>

      <div class="pipeline-steps" role="list" aria-label="Étapes de l'analyse">
        <div
          *ngFor="let step of steps; let i = index; let last = last; trackBy: trackByIndex"
          class="step-row"
          role="listitem"
        >
          <!-- Indicator column -->
          <div class="step-track">
            <div class="step-dot" [class]="'dot-' + step.status" aria-hidden="true">
              <!-- Waiting: number -->
              <span class="dot-number" *ngIf="step.status === 'waiting'">{{ i + 1 }}</span>
              <!-- Processing: spinner -->
              <span class="dot-spinner" *ngIf="step.status === 'processing'"></span>
              <!-- Completed: check -->
              <svg *ngIf="step.status === 'completed'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" aria-hidden="true">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
              <!-- Error: X -->
              <svg *ngIf="step.status === 'error'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" aria-hidden="true">
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </div>
            <div class="step-line" *ngIf="!last" [class.line-done]="step.status === 'completed'" aria-hidden="true"></div>
          </div>

          <!-- Content column -->
          <div class="step-body">
            <span class="step-label" [class.label-active]="step.status === 'processing'" [class.label-done]="step.status === 'completed'">
              {{ step.label }}
            </span>
            <span class="step-result" *ngIf="step.result">{{ step.result }}</span>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    @keyframes fadeSlideIn {
      from { opacity: 0; transform: translateY(6px); }
      to   { opacity: 1; transform: translateY(0); }
    }

    .pipeline-section { margin-bottom: 1.5rem; animation: fadeSlideIn 0.35s ease; }

    /* Header */
    .pipeline-header { text-align: center; margin-bottom: 2rem; }

    .pipeline-badge {
      display: inline-block;
      background: var(--accent-subtle-bg);
      color: var(--accent);
      padding: 0.25rem 0.7rem;
      border-radius: var(--radius-sm);
      font-size: 0.68rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      margin-bottom: 0.6rem;
    }
    .pipeline-badge.done { background: var(--success-glow); color: var(--success); }

    .pipeline-header h2 {
      font-size: 1.25rem; font-weight: 600;
      color: var(--text-primary); margin: 0 0 0.25rem;
      letter-spacing: -0.015em;
    }
    .pipeline-filename {
      color: var(--text-tertiary); font-size: 0.8rem; margin: 0;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
      max-width: 400px; margin: 0 auto;
      font-variant-numeric: tabular-nums;
    }

    .pipeline-steps { display: flex; flex-direction: column; }

    .step-row {
      display: flex;
      gap: 1rem;
      align-items: flex-start;
      animation: fadeSlideIn 0.3s ease both;
    }

    .step-track {
      display: flex;
      flex-direction: column;
      align-items: center;
      flex-shrink: 0;
    }

    .step-dot {
      width: 28px; height: 28px;
      border-radius: 50%;
      background: var(--bg-surface);
      border: 1px solid var(--border-color-hover);
      display: flex; align-items: center; justify-content: center;
      transition: background 0.25s, border-color 0.25s;
      flex-shrink: 0;
    }

    .dot-number { font-size: 0.75rem; font-weight: 600; color: var(--text-tertiary); }

    .dot-processing {
      border-color: var(--accent);
      background: var(--accent-subtle-bg);
    }
    .dot-completed {
      background: var(--accent);
      border-color: var(--accent);
    }
    .dot-completed svg { width: 14px; height: 14px; color: var(--bg-page); }
    .dot-error {
      background: var(--danger-glow);
      border-color: var(--danger);
    }
    .dot-error svg { width: 14px; height: 14px; color: var(--danger); }

    .dot-spinner {
      display: block;
      width: 14px; height: 14px;
      border: 2px solid var(--border-color);
      border-top-color: var(--accent);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }

    .step-line {
      width: 1px; flex: 1; min-height: 20px;
      background: var(--border-color);
      margin: 4px 0;
      transition: background 0.3s ease;
    }
    .step-line.line-done { background: var(--accent); }

    .step-body {
      display: flex; flex-direction: column;
      padding: 0.3rem 0 1.25rem;
      min-width: 0;
    }

    .step-label {
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--text-tertiary);
      transition: color 0.25s;
      line-height: 1.35;
      margin-top: 0.2rem;
    }
    .label-active { color: var(--text-primary); font-weight: 600; }
    .label-done { color: var(--text-primary); }

    .step-result {
      font-size: 0.78rem;
      color: var(--accent);
      margin-top: 0.25rem;
      animation: fadeSlideIn 0.25s ease;
      font-variant-numeric: tabular-nums;
    }
  `]
})
export class HomePipelineComponent {
  @Input() steps: PipelineStep[] = [];
  @Input() isAnalyzing = false;
  @Input() fileName = '';
  @Input() audioFile?: File;
  trackByIndex = (i: number) => i;
}
