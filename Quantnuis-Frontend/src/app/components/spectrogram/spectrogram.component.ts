import { Component, ElementRef, ViewChild, Input, OnDestroy, OnChanges, SimpleChanges, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-spectrogram',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule],
  template: `
    <div class="spectrogram-container" [class.active]="active">
      <div class="spectrogram-header">
        <span class="spectrogram-label">ANALYSE SPECTRALE</span>
        <span class="spectrogram-status" [class.live]="active">
          <span class="status-dot"></span>
          {{ active ? 'LIVE' : 'STANDBY' }}
        </span>
      </div>
      <canvas #canvas class="spectrogram-canvas"></canvas>
      <div class="frequency-labels">
        <span>20 Hz</span>
        <span>500 Hz</span>
        <span>2 kHz</span>
        <span>8 kHz</span>
        <span>20 kHz</span>
      </div>
    </div>
  `,
  styles: [`
    .spectrogram-container {
      background: rgba(0, 0, 0, 0.4);
      border: 1px solid rgba(99, 102, 241, 0.3);
      border-radius: var(--radius-lg);
      padding: 1rem;
      margin: 1.5rem 0;
      transition: all 0.3s ease;
    }

    .spectrogram-container.active {
      border-color: rgba(99, 102, 241, 0.5);
    }

    .spectrogram-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.75rem;
    }

    .spectrogram-label {
      font-size: 0.7rem;
      font-weight: 600;
      letter-spacing: 0.1em;
      color: rgba(255, 255, 255, 0.5);
      text-transform: uppercase;
    }

    .spectrogram-status {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.7rem;
      font-weight: 600;
      letter-spacing: 0.05em;
      color: rgba(255, 255, 255, 0.4);
    }

    .spectrogram-status.live {
      color: var(--accent-light);
    }

    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: rgba(255, 255, 255, 0.3);
    }

    .spectrogram-status.live .status-dot {
      background: var(--accent-light);
      animation: pulse-dot 1s ease-in-out infinite;
    }

    @keyframes pulse-dot {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.5; transform: scale(1.2); }
    }

    .spectrogram-canvas {
      width: 100%;
      height: 120px;
      border-radius: 8px;
      background: linear-gradient(180deg,
        rgba(0, 0, 0, 0.6) 0%,
        rgba(10, 10, 30, 0.8) 100%
      );
    }

    .frequency-labels {
      display: flex;
      justify-content: space-between;
      margin-top: 0.5rem;
      font-size: 0.65rem;
      color: rgba(255, 255, 255, 0.3);
    }
  `]
})
export class SpectrogramComponent implements OnChanges, OnDestroy {
  @ViewChild('canvas', { static: true }) canvasRef!: ElementRef<HTMLCanvasElement>;

  @Input() active = false;
  @Input() audioFile?: File;

  private ctx!: CanvasRenderingContext2D;
  private animationId: number | null = null;
  private audioContext?: AudioContext;
  private analyser?: AnalyserNode;
  private dataArray?: Uint8Array<ArrayBuffer>;
  private source?: AudioBufferSourceNode;

  private accentColor = [99, 102, 241]; // indigo RGB
  private smoothed?: Float32Array; // smoothed values for gravity fall

  ngOnChanges(changes: SimpleChanges) {
    if (changes['active']) {
      if (this.active) {
        this.startVisualization();
      } else {
        this.stopVisualization();
      }
    }
  }

  ngOnDestroy() {
    this.stopVisualization();
  }

  private async startVisualization() {
    const canvas = this.canvasRef.nativeElement;
    this.ctx = canvas.getContext('2d')!;

    // Set canvas size
    canvas.width = canvas.offsetWidth * 2;
    canvas.height = canvas.offsetHeight * 2;

    // If we have an audio file, analyze it
    if (this.audioFile) {
      await this.analyzeFile();
    } else {
      // Demo mode with simulated data
      this.startDemoMode();
    }
  }

  private async analyzeFile() {
    try {
      this.audioContext = new AudioContext();
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 256;

      const bufferLength = this.analyser.frequencyBinCount;
      this.dataArray = new Uint8Array(bufferLength);
      this.smoothed = new Float32Array(bufferLength);

      const arrayBuffer = await this.audioFile!.arrayBuffer();
      const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);

      this.source = this.audioContext.createBufferSource();
      this.source.buffer = audioBuffer;
      this.source.connect(this.analyser);
      this.analyser.connect(this.audioContext.destination);

      // Mute the output (we just want to visualize)
      const gainNode = this.audioContext.createGain();
      gainNode.gain.value = 0.1; // Low volume
      this.analyser.connect(gainNode);
      gainNode.connect(this.audioContext.destination);

      this.source.start();
      this.drawSpectrum();
    } catch {
      // Fallback to demo mode
      this.startDemoMode();
    }
  }

  private startDemoMode() {
    const bufferLength = 64;
    this.dataArray = new Uint8Array(bufferLength);
    this.smoothed = new Float32Array(bufferLength);
    this.drawDemoSpectrum();
  }

  private drawSpectrum() {
    if (!this.active) return;

    this.animationId = requestAnimationFrame(() => this.drawSpectrum());

    if (this.analyser && this.dataArray) {
      this.analyser.getByteFrequencyData(this.dataArray);
      this.applySmoothing(this.dataArray);
      this.renderBars(this.dataArray);
    }
  }

  private drawDemoSpectrum() {
    if (!this.active) return;

    this.animationId = requestAnimationFrame(() => this.drawDemoSpectrum());

    // Simulate a car engine spectrum (realistic frequency profile)
    // Engine fundamental ~80-200 Hz, harmonics up to ~2 kHz, noise floor above
    const time = Date.now() / 1000;
    const len = this.dataArray!.length;

    for (let i = 0; i < len; i++) {
      const freq = (i / len) * 20000; // map bin to ~0-20kHz

      // Engine fundamental + harmonics (peaked around 100-400 Hz)
      const engine = Math.exp(-((Math.log2(Math.max(freq, 20)) - Math.log2(150)) ** 2) / 2) * 180;
      // Exhaust rumble (wide band 50-800 Hz)
      const exhaust = freq < 800 ? Math.exp(-freq / 400) * 120 : 0;
      // Road/tire noise (broadband, low level)
      const road = Math.exp(-freq / 3000) * 40;
      // Harmonic peaks at engine multiples (~150, 300, 450, 600 Hz)
      let harmonics = 0;
      for (let h = 1; h <= 4; h++) {
        const hFreq = 150 * h;
        harmonics += Math.exp(-((freq - hFreq) ** 2) / (2000 * h)) * (120 / h);
      }

      // Slow modulation: engine RPM variation (smooth, not random)
      const rpm = Math.sin(time * 0.6) * 0.15 + 1.0;
      // Per-bin micro-variation (deterministic, smooth)
      const micro = Math.sin(time * 2.5 + i * 1.7) * 0.08 + 1.0;

      const raw = (engine + exhaust + road + harmonics) * rpm * micro;
      this.dataArray![i] = Math.min(255, Math.max(0, raw));
    }

    // Apply smoothing: bars rise fast (0.6), fall slowly (0.92)
    this.applySmoothing(this.dataArray!);
    this.renderBars(this.dataArray!);
  }

  private applySmoothing(dataArray: Uint8Array) {
    if (!this.smoothed || this.smoothed.length !== dataArray.length) {
      this.smoothed = new Float32Array(dataArray.length);
    }
    for (let i = 0; i < dataArray.length; i++) {
      const raw = dataArray[i];
      if (raw > this.smoothed[i]) {
        // Rise fast
        this.smoothed[i] += (raw - this.smoothed[i]) * 0.6;
      } else {
        // Fall slowly (gravity)
        this.smoothed[i] += (raw - this.smoothed[i]) * 0.08;
      }
      dataArray[i] = Math.round(this.smoothed[i]);
    }
  }

  private renderBars(dataArray: Uint8Array) {
    const canvas = this.canvasRef.nativeElement;
    const ctx = this.ctx;
    const width = canvas.width;
    const height = canvas.height;

    // Clear canvas fully
    ctx.clearRect(0, 0, width, height);

    const [r, g, b] = this.accentColor;
    const barCount = dataArray.length;
    const barWidth = width / barCount;
    const barSpacing = 2;

    for (let i = 0; i < barCount; i++) {
      const value = dataArray[i];
      const percent = value / 255;
      const barHeight = percent * height * 0.9;

      const x = i * barWidth;
      const y = height - barHeight;

      // Monochrome gradient: transparent at base → full accent at top
      const gradient = ctx.createLinearGradient(x, height, x, y);
      gradient.addColorStop(0, `rgba(${r},${g},${b},0.1)`);
      gradient.addColorStop(1, `rgba(${r},${g},${b},${0.3 + percent * 0.7})`);

      ctx.fillStyle = gradient;

      // Draw bar with rounded top
      const radius = Math.min(barWidth / 2 - barSpacing, 4);
      ctx.beginPath();
      ctx.roundRect(x + barSpacing / 2, y, barWidth - barSpacing, barHeight, [radius, radius, 0, 0]);
      ctx.fill();
    }
  }

  private stopVisualization() {
    if (this.animationId) {
      cancelAnimationFrame(this.animationId);
      this.animationId = null;
    }

    if (this.source) {
      try {
        this.source.stop();
      } catch {}
    }

    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = undefined;
    }
  }
}
