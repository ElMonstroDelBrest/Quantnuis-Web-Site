import { Component, OnDestroy, ElementRef, ViewChild, ChangeDetectorRef, NgZone } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DbGaugeComponent } from '../db-gauge/db-gauge.component';

@Component({
  selector: 'app-live-audio',
  standalone: true,
  imports: [CommonModule, DbGaugeComponent],
  template: `
    <div class="live-audio-container" [class.active]="isListening" [class.danger]="currentDb > threshold">
      <!-- Header -->
      <div class="live-header">
        <div class="live-badge" [class.recording]="isListening">
          <span class="rec-dot"></span>
          <span>{{ isListening ? 'LIVE' : 'ANALYSE TEMPS RÉEL' }}</span>
        </div>
        <button class="btn-close" *ngIf="isListening" (click)="stopListening()">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>

      <!-- Idle State -->
      <div class="idle-state" *ngIf="!isListening && !error && !needsHttps">
        <div class="mic-icon-wrapper">
          <div class="mic-pulse"></div>
          <div class="mic-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
              <line x1="12" y1="19" x2="12" y2="23"/>
              <line x1="8" y1="23" x2="16" y2="23"/>
            </svg>
          </div>
        </div>
        <h3>Analyse en temps réel</h3>
        <p>Activez le microphone pour mesurer le niveau sonore ambiant</p>
        <button class="btn-start" (click)="startListening()">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
          </svg>
          Activer le micro
        </button>
      </div>

      <!-- HTTPS Required State -->
      <div class="https-state" *ngIf="needsHttps && !isListening">
        <div class="https-icon">🔒</div>
        <h3>Connexion sécurisée requise</h3>
        <p>L'accès au microphone nécessite HTTPS. Utilisez le mode démo pour tester la fonctionnalité.</p>
        <button class="btn-demo-mic" (click)="startDemoMode()">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="5 3 19 12 5 21 5 3"/>
          </svg>
          Lancer le mode démo
        </button>
      </div>

      <!-- Error State -->
      <div class="error-state" *ngIf="error">
        <div class="error-icon">⚠️</div>
        <h3>Accès refusé</h3>
        <p>{{ error }}</p>
        <button class="btn-retry" (click)="startListening()">Réessayer</button>
      </div>

      <!-- Listening State -->
      <div class="listening-state" *ngIf="isListening">
        <!-- Spectrogram Canvas -->
        <canvas #spectrumCanvas class="spectrum-canvas"></canvas>

        <!-- Gauge -->
        <div class="gauge-wrapper">
          <app-db-gauge [value]="currentDb" [threshold]="threshold"></app-db-gauge>
        </div>

        <!-- Status -->
        <div class="status-display">
          <div class="status-item">
            <span class="status-label">Pic</span>
            <span class="status-value peak">{{ peakDb }} dB</span>
          </div>
          <div class="status-item">
            <span class="status-label">Moyenne</span>
            <span class="status-value avg">{{ avgDb }} dB</span>
          </div>
          <div class="status-item">
            <span class="status-label">Statut</span>
            <span class="status-value" [class.safe]="currentDb <= threshold" [class.danger]="currentDb > threshold">
              {{ currentDb > threshold ? 'BRUYANT' : 'NORMAL' }}
            </span>
          </div>
        </div>

        <!-- Classification -->
        <div class="classification" [class]="getNoiseClass()">
          <span class="class-icon">{{ getNoiseIcon() }}</span>
          <span class="class-text">{{ getNoiseLabel() }}</span>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .live-audio-container {
      background: linear-gradient(145deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.95));
      border: 2px solid rgba(99, 102, 241, 0.3);
      border-radius: 24px;
      padding: 1.5rem;
      margin: 2rem 0;
      transition: all 0.4s var(--ease-out-expo);
      position: relative;
      overflow: hidden;
    }

    .live-audio-container::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 3px;
      background: linear-gradient(90deg, #6366f1, #8b5cf6, #a855f7);
      opacity: 0;
      transition: opacity 0.3s ease;
    }

    .live-audio-container.active::before {
      opacity: 1;
      animation: scan 2s linear infinite;
    }

    .live-audio-container.active {
      border-color: var(--accent);
      box-shadow: 0 0 40px rgba(99, 102, 241, 0.3);
    }

    .live-audio-container.danger {
      border-color: var(--danger);
      box-shadow: 0 0 40px rgba(239, 68, 68, 0.3);
    }

    .live-audio-container.danger::before {
      background: linear-gradient(90deg, #ef4444, #f87171, #ef4444);
    }

    @keyframes scan {
      0% { transform: translateX(-100%); }
      100% { transform: translateX(100%); }
    }

    .live-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.5rem;
    }

    .live-badge {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      background: rgba(99, 102, 241, 0.1);
      border: 1px solid rgba(99, 102, 241, 0.3);
      padding: 0.5rem 1rem;
      border-radius: 100px;
      font-size: 0.75rem;
      font-weight: 600;
      letter-spacing: 0.1em;
      color: var(--accent-light);
    }

    .live-badge.recording {
      background: rgba(239, 68, 68, 0.1);
      border-color: rgba(239, 68, 68, 0.5);
      color: var(--danger-lighter);
    }

    .rec-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: rgba(255, 255, 255, 0.3);
    }

    .live-badge.recording .rec-dot {
      background: var(--danger);
      animation: pulse-rec 1s ease-in-out infinite;
    }

    @keyframes pulse-rec {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.3; }
    }

    .btn-close {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      background: rgba(255, 255, 255, 0.1);
      border: none;
      color: rgba(255, 255, 255, 0.6);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s ease;
    }

    .btn-close:hover {
      background: var(--danger);
      color: white;
    }

    .btn-close svg {
      width: 16px;
      height: 16px;
    }

    /* Idle State */
    .idle-state {
      text-align: center;
      padding: 2rem 0;
    }

    .mic-icon-wrapper {
      position: relative;
      width: 100px;
      height: 100px;
      margin: 0 auto 1.5rem;
    }

    .mic-pulse {
      position: absolute;
      inset: 0;
      background: radial-gradient(circle, rgba(99, 102, 241, 0.3) 0%, transparent 70%);
      border-radius: 50%;
      animation: mic-pulse 2s ease-in-out infinite;
    }

    @keyframes mic-pulse {
      0%, 100% { transform: scale(0.8); opacity: 0.5; }
      50% { transform: scale(1.2); opacity: 1; }
    }

    .mic-icon {
      position: absolute;
      inset: 15px;
      background: var(--accent-dark);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: var(--shadow-btn-intense);
    }

    .mic-icon svg {
      width: 36px;
      height: 36px;
      color: white;
    }

    .idle-state h3 {
      font-size: 1.25rem;
      font-weight: 700;
      color: white;
      margin: 0 0 0.5rem;
    }

    .idle-state p {
      color: rgba(255, 255, 255, 0.5);
      font-size: 0.9rem;
      margin: 0 0 1.5rem;
    }

    .btn-start {
      display: inline-flex;
      align-items: center;
      gap: 0.75rem;
      background: var(--accent-dark);
      color: white;
      border: none;
      padding: 1rem 2rem;
      border-radius: 14px;
      font-weight: 600;
      font-size: 1rem;
      cursor: pointer;
      transition: all 0.3s var(--ease-out-expo);
      box-shadow: var(--shadow-card-accent);
    }

    .btn-start:hover {
      transform: translateY(-2px);
      box-shadow: var(--shadow-card-accent-hover);
    }

    .btn-start svg {
      width: 20px;
      height: 20px;
    }

    /* Error State */
    .error-state {
      text-align: center;
      padding: 2rem 0;
    }

    .error-icon {
      font-size: 3rem;
      margin-bottom: 1rem;
    }

    .error-state h3 {
      font-size: 1.25rem;
      font-weight: 700;
      color: var(--danger);
      margin: 0 0 0.5rem;
    }

    .error-state p {
      color: rgba(255, 255, 255, 0.5);
      font-size: 0.9rem;
      margin: 0 0 1.5rem;
    }

    .btn-retry {
      background: rgba(239, 68, 68, 0.1);
      border: 1px solid rgba(239, 68, 68, 0.3);
      color: var(--danger-lighter);
      padding: 0.75rem 1.5rem;
      border-radius: 10px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .btn-retry:hover {
      background: rgba(239, 68, 68, 0.2);
    }

    /* HTTPS State */
    .https-state {
      text-align: center;
      padding: 2rem 0;
    }

    .https-icon {
      font-size: 3rem;
      margin-bottom: 1rem;
    }

    .https-state h3 {
      font-size: 1.25rem;
      font-weight: 700;
      color: var(--warning);
      margin: 0 0 0.5rem;
    }

    .https-state p {
      color: rgba(255, 255, 255, 0.5);
      font-size: 0.9rem;
      margin: 0 0 1.5rem;
      max-width: 300px;
      margin-left: auto;
      margin-right: auto;
    }

    .btn-demo-mic {
      display: inline-flex;
      align-items: center;
      gap: 0.75rem;
      background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
      color: white;
      border: none;
      padding: 1rem 2rem;
      border-radius: 14px;
      font-weight: 600;
      font-size: 1rem;
      cursor: pointer;
      transition: all 0.3s var(--ease-out-expo);
      box-shadow: var(--shadow-sm);
    }

    .btn-demo-mic:hover {
      transform: translateY(-2px);
      box-shadow: var(--shadow-md);
    }

    .btn-demo-mic svg {
      width: 20px;
      height: 20px;
    }

    /* Listening State */
    .listening-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 1.5rem;
    }

    .spectrum-canvas {
      width: 100%;
      height: 80px;
      border-radius: var(--radius-md);
      background: rgba(0, 0, 0, 0.3);
    }

    .gauge-wrapper {
      display: flex;
      justify-content: center;
    }

    .status-display {
      display: flex;
      gap: 2rem;
      padding: 1rem 1.5rem;
      background: rgba(0, 0, 0, 0.3);
      border-radius: var(--radius-md);
    }

    .status-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.25rem;
    }

    .status-label {
      font-size: 0.7rem;
      font-weight: 600;
      letter-spacing: 0.05em;
      color: rgba(255, 255, 255, 0.4);
      text-transform: uppercase;
    }

    .status-value {
      font-size: 1.1rem;
      font-weight: 700;
      font-family: 'SF Mono', monospace;
      color: white;
    }

    .status-value.peak { color: var(--warning); }
    .status-value.avg { color: var(--accent); }
    .status-value.safe { color: var(--success); }
    .status-value.danger { color: var(--danger); }

    .classification {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.75rem 1.5rem;
      border-radius: 100px;
      font-weight: 600;
    }

    .classification.quiet {
      background: rgba(16, 185, 129, 0.15);
      color: var(--success-light);
      border: 1px solid rgba(16, 185, 129, 0.3);
    }

    .classification.moderate {
      background: rgba(245, 158, 11, 0.15);
      color: #fcd34d;
      border: 1px solid rgba(245, 158, 11, 0.3);
    }

    .classification.loud {
      background: rgba(239, 68, 68, 0.15);
      color: var(--danger-lighter);
      border: 1px solid rgba(239, 68, 68, 0.3);
    }

    .classification.extreme {
      background: rgba(239, 68, 68, 0.25);
      color: var(--danger);
      border: 1px solid rgba(239, 68, 68, 0.5);
      animation: danger-pulse 1s ease-in-out infinite;
    }

    @keyframes danger-pulse {
      0%, 100% { transform: scale(1); }
      50% { transform: scale(1.02); }
    }

    .class-icon {
      font-size: 1.25rem;
    }

    .class-text {
      font-size: 0.85rem;
      letter-spacing: 0.05em;
    }

    @media (max-width: 600px) {
      .status-display {
        flex-wrap: wrap;
        gap: 1rem;
        justify-content: center;
      }

      .gauge-wrapper {
        transform: scale(0.85);
      }
    }
  `]
})
export class LiveAudioComponent implements OnDestroy {
  @ViewChild('spectrumCanvas') canvasRef!: ElementRef<HTMLCanvasElement>;

  isListening = false;
  error: string | null = null;
  currentDb = 0;
  peakDb = 0;
  avgDb = 0;
  threshold = 80;
  needsHttps = false;
  private isDemoMode = false;

  private audioContext?: AudioContext;
  private analyser?: AnalyserNode;
  private microphone?: MediaStreamAudioSourceNode;
  private stream?: MediaStream;
  private animationId?: number;
  private dataArray?: Uint8Array<ArrayBuffer>;
  private dbHistory: number[] = [];

  constructor(private cdr: ChangeDetectorRef, private ngZone: NgZone) {
    // On tente toujours d'accéder au micro - si ça échoue, on propose le mode démo
    this.needsHttps = false;
  }

  async startListening() {
    this.error = null;

    try {
      // Toujours tenter de demander l'accès au microphone
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: false, // We want to measure actual noise
          autoGainControl: false
        }
      });

      this.audioContext = new AudioContext();
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 256;
      this.analyser.smoothingTimeConstant = 0.8;

      this.microphone = this.audioContext.createMediaStreamSource(this.stream);
      this.microphone.connect(this.analyser);

      this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);

      this.isListening = true;
      this.peakDb = 0;
      this.dbHistory = [];

      // Start visualization
      setTimeout(() => this.visualize(), 100);

    } catch (err: any) {
      if (err.name === 'NotAllowedError') {
        this.error = 'Veuillez autoriser l\'accès au microphone dans les paramètres de votre navigateur.';
      } else if (err.name === 'NotFoundError') {
        this.error = 'Aucun microphone détecté sur cet appareil.';
      } else {
        // Autre erreur (HTTP, API non disponible, etc.) - proposer le mode démo
        this.error = 'Microphone non disponible. Utilisez le mode démo ci-dessous.';
        this.needsHttps = true;
      }
    }
  }

  startDemoMode() {
    this.isDemoMode = true;
    this.isListening = true;
    this.error = null;
    this.peakDb = 0;
    this.dbHistory = [];
    this.dataArray = new Uint8Array(128);

    // Start demo visualization
    setTimeout(() => this.visualizeDemo(), 100);
  }

  private visualizeDemo() {
    if (!this.isListening || !this.isDemoMode) return;

    this.animationId = requestAnimationFrame(() => this.visualizeDemo());

    // Simulate realistic audio data
    const time = Date.now() / 1000;
    for (let i = 0; i < this.dataArray!.length; i++) {
      const base = Math.sin(time * 2 + i * 0.1) * 30 + 60;
      const noise = Math.random() * 50;
      const bassBoost = i < 20 ? Math.sin(time * 4) * 40 + 50 : 0;
      this.dataArray![i] = Math.min(255, Math.max(0, base + noise + bassBoost));
    }

    // Calculate simulated dB
    const sum = this.dataArray!.reduce((a, b) => a + b, 0);
    const avg = sum / this.dataArray!.length;
    this.currentDb = Math.round(35 + (avg / 255) * 70 + Math.sin(time * 3) * 10);

    // Update peak
    if (this.currentDb > this.peakDb) {
      this.peakDb = this.currentDb;
    }

    // Calculate rolling average
    this.dbHistory.push(this.currentDb);
    if (this.dbHistory.length > 50) {
      this.dbHistory.shift();
    }
    this.avgDb = Math.round(this.dbHistory.reduce((a, b) => a + b, 0) / this.dbHistory.length);

    // Draw spectrum
    this.drawSpectrum();

    // Force Angular change detection
    this.ngZone.run(() => this.cdr.detectChanges());
  }

  stopListening() {
    this.isListening = false;
    this.isDemoMode = false;

    if (this.animationId) {
      cancelAnimationFrame(this.animationId);
    }

    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
    }

    if (this.audioContext) {
      this.audioContext.close();
    }

    this.currentDb = 0;
    this.peakDb = 0;
    this.avgDb = 0;
  }

  ngOnDestroy() {
    this.stopListening();
  }

  private visualize() {
    if (!this.isListening || !this.analyser || !this.dataArray) return;

    this.animationId = requestAnimationFrame(() => this.visualize());

    // Get frequency data
    this.analyser.getByteFrequencyData(this.dataArray);

    // Calculate dB level
    const sum = this.dataArray.reduce((a, b) => a + b, 0);
    const avg = sum / this.dataArray.length;

    // Convert to approximate dB (scaled for demonstration)
    // Real dB calculation would require calibration
    this.currentDb = Math.round(20 + (avg / 255) * 100);

    // Update peak
    if (this.currentDb > this.peakDb) {
      this.peakDb = this.currentDb;
    }

    // Calculate rolling average
    this.dbHistory.push(this.currentDb);
    if (this.dbHistory.length > 50) {
      this.dbHistory.shift();
    }
    this.avgDb = Math.round(this.dbHistory.reduce((a, b) => a + b, 0) / this.dbHistory.length);

    // Draw spectrum
    this.drawSpectrum();
  }

  private drawSpectrum() {
    if (!this.canvasRef || !this.dataArray) return;

    const canvas = this.canvasRef.nativeElement;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size
    if (canvas.width !== canvas.offsetWidth * 2) {
      canvas.width = canvas.offsetWidth * 2;
      canvas.height = canvas.offsetHeight * 2;
    }

    const width = canvas.width;
    const height = canvas.height;

    // Clear with fade
    ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
    ctx.fillRect(0, 0, width, height);

    const barCount = this.dataArray.length;
    const barWidth = width / barCount;

    for (let i = 0; i < barCount; i++) {
      const value = this.dataArray[i];
      const percent = value / 255;
      const barHeight = percent * height * 0.9;

      const x = i * barWidth;
      const y = height - barHeight;

      // Color based on level
      let color: string;
      if (this.currentDb > this.threshold) {
        color = `rgba(239, 68, 68, ${0.6 + percent * 0.4})`;
      } else if (this.currentDb > this.threshold * 0.75) {
        color = `rgba(245, 158, 11, ${0.6 + percent * 0.4})`;
      } else {
        color = `rgba(99, 102, 241, ${0.6 + percent * 0.4})`;
      }

      ctx.fillStyle = color;
      ctx.fillRect(x, y, barWidth - 1, barHeight);

      // Glow for peaks
      if (percent > 0.8) {
        ctx.shadowColor = color;
        ctx.shadowBlur = 10;
        ctx.fillRect(x, y, barWidth - 1, barHeight);
        ctx.shadowBlur = 0;
      }
    }
  }

  getNoiseClass(): string {
    if (this.currentDb < 50) return 'quiet';
    if (this.currentDb < 70) return 'moderate';
    if (this.currentDb < 85) return 'loud';
    return 'extreme';
  }

  getNoiseIcon(): string {
    if (this.currentDb < 50) return '🔇';
    if (this.currentDb < 70) return '🔈';
    if (this.currentDb < 85) return '🔉';
    return '🔊';
  }

  getNoiseLabel(): string {
    if (this.currentDb < 50) return 'Environnement calme';
    if (this.currentDb < 70) return 'Bruit modéré';
    if (this.currentDb < 85) return 'Bruit élevé';
    return 'Niveau dangereux !';
  }
}
