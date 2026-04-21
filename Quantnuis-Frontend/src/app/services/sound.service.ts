import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class SoundService {
  private audioContext?: AudioContext;
  private enabled = true;

  constructor() {
    // Initialize on first user interaction
  }

  private getContext(): AudioContext {
    if (!this.audioContext) {
      this.audioContext = new AudioContext();
    }
    return this.audioContext;
  }

  setEnabled(enabled: boolean) {
    this.enabled = enabled;
  }

  // Success sound - ascending chime (for CONFORME result)
  playSuccess() {
    if (!this.enabled) return;

    const ctx = this.getContext();
    const now = ctx.currentTime;

    // Create a pleasant ascending arpeggio
    const frequencies = [523.25, 659.25, 783.99, 1046.50]; // C5, E5, G5, C6
    const duration = 0.15;

    frequencies.forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'sine';
      osc.frequency.value = freq;

      gain.gain.setValueAtTime(0, now + i * duration);
      gain.gain.linearRampToValueAtTime(0.3, now + i * duration + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.01, now + i * duration + duration);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now + i * duration);
      osc.stop(now + i * duration + duration + 0.1);
    });
  }

  // Alert sound - descending tone (for BRUYANT result)
  playAlert() {
    if (!this.enabled) return;

    const ctx = this.getContext();
    const now = ctx.currentTime;

    // Create an alert sound
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(880, now);
    osc.frequency.exponentialRampToValueAtTime(220, now + 0.5);

    gain.gain.setValueAtTime(0.2, now);
    gain.gain.exponentialRampToValueAtTime(0.01, now + 0.5);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start(now);
    osc.stop(now + 0.6);
  }

  // Processing blip - short tick sound (for pipeline steps)
  playTick() {
    if (!this.enabled) return;

    const ctx = this.getContext();
    const now = ctx.currentTime;

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = 'sine';
    osc.frequency.value = 1200;

    gain.gain.setValueAtTime(0.15, now);
    gain.gain.exponentialRampToValueAtTime(0.01, now + 0.08);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start(now);
    osc.stop(now + 0.1);
  }

  // Step complete - satisfying click
  playStepComplete() {
    if (!this.enabled) return;

    const ctx = this.getContext();
    const now = ctx.currentTime;

    // Two-tone click
    [800, 1000].forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'sine';
      osc.frequency.value = freq;

      gain.gain.setValueAtTime(0.2, now + i * 0.03);
      gain.gain.exponentialRampToValueAtTime(0.01, now + i * 0.03 + 0.1);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now + i * 0.03);
      osc.stop(now + i * 0.03 + 0.15);
    });
  }

  // Analysis start - swoosh up
  playStart() {
    if (!this.enabled) return;

    const ctx = this.getContext();
    const now = ctx.currentTime;

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = 'sine';
    osc.frequency.setValueAtTime(200, now);
    osc.frequency.exponentialRampToValueAtTime(800, now + 0.3);

    gain.gain.setValueAtTime(0.15, now);
    gain.gain.linearRampToValueAtTime(0.2, now + 0.1);
    gain.gain.exponentialRampToValueAtTime(0.01, now + 0.4);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start(now);
    osc.stop(now + 0.5);
  }

  // Celebratory fanfare - for confetti moments
  playFanfare() {
    if (!this.enabled) return;

    const ctx = this.getContext();
    const now = ctx.currentTime;

    // Triumphant fanfare
    const notes = [
      { freq: 523.25, time: 0, duration: 0.15 },      // C5
      { freq: 659.25, time: 0.12, duration: 0.15 },   // E5
      { freq: 783.99, time: 0.24, duration: 0.15 },   // G5
      { freq: 1046.50, time: 0.36, duration: 0.4 },   // C6 (hold)
    ];

    notes.forEach(note => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'triangle';
      osc.frequency.value = note.freq;

      gain.gain.setValueAtTime(0, now + note.time);
      gain.gain.linearRampToValueAtTime(0.25, now + note.time + 0.02);
      gain.gain.setValueAtTime(0.25, now + note.time + note.duration - 0.05);
      gain.gain.exponentialRampToValueAtTime(0.01, now + note.time + note.duration);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now + note.time);
      osc.stop(now + note.time + note.duration + 0.1);
    });
  }

  // Click feedback for buttons
  playClick() {
    if (!this.enabled) return;

    const ctx = this.getContext();
    const now = ctx.currentTime;

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = 'sine';
    osc.frequency.value = 600;

    gain.gain.setValueAtTime(0.1, now);
    gain.gain.exponentialRampToValueAtTime(0.01, now + 0.05);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start(now);
    osc.stop(now + 0.06);
  }
}
