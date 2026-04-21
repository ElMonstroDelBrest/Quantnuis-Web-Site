import { Component, Input, OnChanges, SimpleChanges, OnDestroy, ChangeDetectorRef, inject, ChangeDetectionStrategy } from '@angular/core';

@Component({
  selector: 'app-db-gauge',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [],
  template: `
    <div class="gauge-container" [class.danger]="currentValue > threshold" role="meter" [attr.aria-valuenow]="displayValue" aria-valuemin="0" aria-valuemax="120" [attr.aria-label]="'Niveau sonore: ' + displayValue + ' decibels'">
      <svg class="gauge-svg" viewBox="0 0 200 200" aria-hidden="true">
        <!-- Background track -->
        <circle
          cx="100" cy="100" r="85"
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          stroke-width="6"
          stroke-linecap="round"
          stroke-dasharray="400 134"
          transform="rotate(135 100 100)"
        />

        <!-- Progress arc -->
        <circle
          class="gauge-progress"
          cx="100" cy="100" r="85"
          fill="none"
          [attr.stroke]="progressColor"
          stroke-width="6"
          stroke-linecap="round"
          [attr.stroke-dasharray]="dashArray"
          transform="rotate(135 100 100)"
        />
      </svg>

      <!-- Digital display -->
      <div class="digital-display">
        <div class="value-container">
          <span class="value">{{ displayValue }}</span>
          <span class="unit">dB</span>
        </div>
        <div class="status-badge" [class.safe]="currentValue <= threshold" [class.danger]="currentValue > threshold">
          {{ currentValue > threshold ? 'DÉPASSEMENT' : 'NORMAL' }}
        </div>
      </div>

      <!-- Threshold indicator -->
      <div class="threshold-indicator">
        <span class="threshold-label">Seuil: {{ threshold }} dB</span>
      </div>
    </div>
  `,
  styles: [`
    .gauge-container {
      position: relative;
      width: 220px;
      height: 220px;
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-xl);
      padding: 15px;
      transition: border-color 0.3s ease;
    }

    .gauge-container.danger {
      border-color: rgba(239, 68, 68, 0.3);
    }

    .gauge-svg {
      width: 100%;
      height: 100%;
    }

    .gauge-progress {
      transition: stroke-dasharray 0.5s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .digital-display {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      text-align: center;
      pointer-events: none;
    }

    .value-container {
      display: flex;
      align-items: baseline;
      justify-content: center;
      gap: 2px;
    }

    .value {
      font-size: 2.5rem;
      font-weight: 700;
      font-family: 'SF Mono', 'Monaco', monospace;
      color: white;
    }

    .unit {
      font-size: 1rem;
      font-weight: 600;
      color: rgba(255, 255, 255, 0.5);
    }

    .status-badge {
      margin-top: 8px;
      padding: 2px 8px;
      border-radius: 10px;
      font-size: 0.55rem;
      font-weight: 700;
      letter-spacing: 0.1em;
      text-transform: uppercase;
    }

    .status-badge.safe {
      background: rgba(16, 185, 129, 0.12);
      color: var(--success);
      border: 1px solid rgba(16, 185, 129, 0.25);
    }

    .status-badge.danger {
      background: rgba(239, 68, 68, 0.12);
      color: var(--danger);
      border: 1px solid rgba(239, 68, 68, 0.25);
    }

    .threshold-indicator {
      position: absolute;
      bottom: 10px;
      left: 50%;
      transform: translateX(-50%);
    }

    .threshold-label {
      font-size: 0.6rem;
      color: rgba(255, 255, 255, 0.35);
    }
  `]
})
export class DbGaugeComponent implements OnChanges, OnDestroy {
  @Input() value = 0;
  @Input() threshold = 80;
  @Input() animate = true;

  currentValue = 0;
  displayValue = 0;
  isAnimating = false;

  private animationFrame: number | null = null;
  private cdr = inject(ChangeDetectorRef);

  ngOnChanges(changes: SimpleChanges) {
    if (changes['value'] && this.animate) {
      this.animateToValue(this.value);
    } else if (changes['value']) {
      this.currentValue = this.value;
      this.displayValue = Math.round(this.value);
    }
  }

  ngOnDestroy() {
    if (this.animationFrame) {
      cancelAnimationFrame(this.animationFrame);
    }
  }

  private animateToValue(targetValue: number) {
    const startValue = this.currentValue;
    const startTime = performance.now();
    const duration = 800;

    const animate = (currentTime: number) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);

      // Easing function
      const eased = 1 - Math.pow(1 - progress, 3);

      this.currentValue = startValue + (targetValue - startValue) * eased;
      this.displayValue = Math.round(this.currentValue);
      this.isAnimating = true;

      this.cdr.detectChanges();

      if (progress < 1) {
        this.animationFrame = requestAnimationFrame(animate);
      } else {
        this.isAnimating = false;
      }
    };

    this.animationFrame = requestAnimationFrame(animate);
  }

  get progressColor(): string {
    if (this.currentValue > this.threshold) {
      return '#ef4444'; // Red for danger
    } else if (this.currentValue > this.threshold * 0.75) {
      return '#f59e0b'; // Orange for warning
    }
    return '#10b981'; // Green for safe
  }

  get dashArray(): string {
    const maxArc = 400; // 270 degrees worth of circumference
    const progress = Math.min(this.currentValue / 120, 1);
    const arcLength = progress * maxArc;
    return `${arcLength} 534`;
  }

}
