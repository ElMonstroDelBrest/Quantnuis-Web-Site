import { Component, Input, OnChanges, OnDestroy, SimpleChanges, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';

interface ConfettiPiece {
  id: number;
  x: number;
  color: string;
  delay: number;
  duration: number;
  size: number;
}

@Component({
  selector: 'app-confetti',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule],
  template: `
    <div class="confetti-container" *ngIf="active && pieces.length > 0">
      <div
        *ngFor="let piece of pieces; trackBy: trackByIndex"
        class="confetti-piece"
        [style.left.%]="piece.x"
        [style.background-color]="piece.color"
        [style.animation-delay.ms]="piece.delay"
        [style.animation-duration.s]="piece.duration"
        [style.width.px]="piece.size"
        [style.height.px]="piece.size * 0.4"
      ></div>
    </div>
  `,
  styles: [`
    .confetti-container {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
      z-index: 9999;
      overflow: hidden;
    }

    .confetti-piece {
      position: absolute;
      top: -20px;
      opacity: 0;
      animation: confetti-fall linear forwards;
    }

    @keyframes confetti-fall {
      0% {
        opacity: 1;
        top: -20px;
        transform: translateX(0) rotateZ(0deg) rotateY(0deg);
      }
      25% {
        opacity: 1;
        transform: translateX(30px) rotateZ(90deg) rotateY(180deg);
      }
      50% {
        opacity: 1;
        transform: translateX(-20px) rotateZ(180deg) rotateY(360deg);
      }
      75% {
        opacity: 0.8;
        transform: translateX(40px) rotateZ(270deg) rotateY(540deg);
      }
      100% {
        opacity: 0;
        top: 100vh;
        transform: translateX(-10px) rotateZ(360deg) rotateY(720deg);
      }
    }
  `]
})
export class ConfettiComponent implements OnChanges, OnDestroy {
  @Input() active = false;
  trackByIndex = (i: number) => i;
  @Input() pieceCount = 100;
  @Input() duration = 4000; // ms before auto-cleanup

  pieces: ConfettiPiece[] = [];
  private timeout: any;

  private colors = [
    '#10b981', // green
    '#6366f1', // indigo
    '#8b5cf6', // purple
    '#f59e0b', // amber
    '#ef4444', // red
    '#3b82f6', // blue
    '#ec4899', // pink
    '#14b8a6', // teal
  ];

  ngOnChanges(changes: SimpleChanges) {
    if (changes['active']) {
      if (this.active) {
        this.generateConfetti();
        this.timeout = setTimeout(() => {
          this.pieces = [];
        }, this.duration);
      } else {
        this.pieces = [];
        if (this.timeout) {
          clearTimeout(this.timeout);
        }
      }
    }
  }

  ngOnDestroy() {
    if (this.timeout) {
      clearTimeout(this.timeout);
    }
  }

  private generateConfetti() {
    this.pieces = [];
    for (let i = 0; i < this.pieceCount; i++) {
      this.pieces.push({
        id: i,
        x: Math.random() * 100,
        color: this.colors[Math.floor(Math.random() * this.colors.length)],
        delay: Math.random() * 500,
        duration: 2.5 + Math.random() * 2,
        size: 8 + Math.random() * 8
      });
    }
  }
}
