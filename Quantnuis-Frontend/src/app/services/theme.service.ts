import { Injectable, signal } from '@angular/core';

export type Theme = 'dark' | 'light';

const STORAGE_KEY = 'quantnuis-theme';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly _theme = signal<Theme>('dark');
  readonly theme = this._theme.asReadonly();

  constructor() {
    const saved = this.readSavedTheme();
    const initial: Theme = saved ?? (this.prefersLight() ? 'light' : 'dark');
    this.apply(initial);
  }

  toggle(): void {
    this.apply(this._theme() === 'dark' ? 'light' : 'dark');
  }

  set(theme: Theme): void {
    this.apply(theme);
  }

  private apply(theme: Theme): void {
    this._theme.set(theme);
    if (typeof document !== 'undefined') {
      document.documentElement.setAttribute('data-theme', theme);
    }
    if (typeof localStorage !== 'undefined') {
      try { localStorage.setItem(STORAGE_KEY, theme); } catch { /* storage indisponible */ }
    }
  }

  private readSavedTheme(): Theme | null {
    if (typeof localStorage === 'undefined') return null;
    try {
      const value = localStorage.getItem(STORAGE_KEY);
      return value === 'dark' || value === 'light' ? value : null;
    } catch {
      return null;
    }
  }

  private prefersLight(): boolean {
    if (typeof window === 'undefined' || !window.matchMedia) return false;
    return window.matchMedia('(prefers-color-scheme: light)').matches;
  }
}
