import { Component, ChangeDetectionStrategy, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-home-hero',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule, RouterLink],
  template: `
    <header class="hero">
      <div class="hero-inner">

        <!-- Left column: text -->
        <div class="hero-text">
          <span class="overline">PROJET DE RECHERCHE · ENSTA BRETAGNE · 2025–2026</span>

          <h1 class="hero-title">
            Détection automatique de véhicules bruyants
          </h1>

          <p class="hero-lede editorial-prose">
            Une cascade de deux modèles d'apprentissage supervisé identifie, dans un enregistrement
            audio urbain, la présence d'un véhicule puis estime si son niveau sonore dépasse le seuil
            réglementaire de 85 dB à deux mètres.
          </p>

          <div class="hero-byline">
            <span>Nathan Boué · Daniel Gherasim · Nour Mourtada · Owen Perdigues</span><br>
            <span>2A · ENSTA Bretagne · Encadrant : Dorian Cazau</span><br>
            <span>Dernière mise à jour · Avril 2026</span>
          </div>

          <div class="hero-actions">
            <button type="button" class="cta-outlined" (click)="scrollToDropzone()">
              Démonstration ↓
            </button>
            <a routerLink="/methodology" class="cta-text">
              Méthodologie ↗
            </a>
          </div>
        </div>

        <!-- Right column: pipeline figure -->
        <figure class="hero-figure">
          <svg
            class="pipeline-svg"
            viewBox="0 0 260 340"
            xmlns="http://www.w3.org/2000/svg"
            role="img"
            aria-label="Diagramme de l'architecture en cascade : Audio brut → CarDetector CNN → NoisyCarDetector CNN → Verdict"
          >
            <!-- Node 1: Audio brut -->
            <rect class="node-rect" x="30" y="10" width="200" height="56" rx="4"/>
            <text x="130" y="34" text-anchor="middle" class="node-title">AUDIO BRUT</text>
            <text x="130" y="52" text-anchor="middle" class="node-sub">WAV · 16 kHz</text>

            <!-- Arrow 1→2 -->
            <line class="arrow" x1="130" y1="66" x2="130" y2="92"/>
            <polygon class="arrowhead" points="124,88 130,98 136,88"/>

            <!-- Node 2: CarDetector -->
            <rect class="node-rect" x="30" y="98" width="200" height="56" rx="4"/>
            <text x="130" y="122" text-anchor="middle" class="node-title">CARDETECTOR</text>
            <text x="130" y="140" text-anchor="middle" class="node-sub">CNN · Détection de véhicule</text>

            <!-- Arrow 2→3 -->
            <line class="arrow" x1="130" y1="154" x2="130" y2="180"/>
            <polygon class="arrowhead" points="124,176 130,186 136,176"/>

            <!-- Node 3: NoisyCarDetector -->
            <rect class="node-rect" x="30" y="186" width="200" height="56" rx="4"/>
            <text x="130" y="210" text-anchor="middle" class="node-title">NOISYCARDETECTOR</text>
            <text x="130" y="228" text-anchor="middle" class="node-sub">CNN · Niveau sonore</text>

            <!-- Arrow 3→4 -->
            <line class="arrow" x1="130" y1="242" x2="130" y2="268"/>
            <polygon class="arrowhead" points="124,264 130,274 136,264"/>

            <!-- Node 4: Verdict (emphasized) -->
            <rect class="node-rect node-rect--verdict" x="30" y="274" width="200" height="56" rx="4"/>
            <text x="130" y="298" text-anchor="middle" class="node-title node-title--verdict">VERDICT</text>
            <text x="130" y="316" text-anchor="middle" class="node-sub">≥ 85 dB à 2 m ?</text>
          </svg>
          <figcaption>
            Figure 1. Architecture en cascade du pipeline de détection.
          </figcaption>
        </figure>

      </div>
    </header>
  `,
  styles: [`
    .hero {
      padding: 4rem 1.5rem 3rem;
      border-bottom: 1px solid var(--border-color);
    }

    .hero-inner {
      max-width: 960px;
      margin: 0 auto;
      display: grid;
      grid-template-columns: 1.4fr 1fr;
      gap: 3rem;
      align-items: start;
    }

    /* Left column */
    .hero-text {
      display: flex;
      flex-direction: column;
    }

    .overline {
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 0.72rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--text-tertiary);
      margin-bottom: 1rem;
      display: block;
    }

    .hero-title {
      font-family: 'Newsreader', 'Charter', 'Georgia', serif;
      font-size: clamp(2rem, 3.5vw + 0.5rem, 2.75rem);
      font-weight: 600;
      letter-spacing: -0.015em;
      line-height: 1.15;
      color: var(--text-primary);
      margin: 0 0 1.25rem;
    }

    .hero-lede {
      font-family: 'Newsreader', 'Charter', 'Georgia', serif;
      font-size: 1.05rem;
      line-height: 1.65;
      color: var(--text-secondary);
      max-width: 540px;
      margin: 0 0 1.5rem;
    }

    .hero-byline {
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 0.82rem;
      color: var(--text-secondary);
      line-height: 1.8;
      margin-bottom: 1.5rem;
    }

    .hero-byline span { display: inline; }

    /* Actions */
    .hero-actions {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 1rem;
    }

    .cta-outlined {
      display: inline-flex;
      align-items: center;
      padding: 0.5rem 1rem;
      background: transparent;
      border: 1px solid var(--border-color-hover);
      border-radius: var(--radius-sm);
      color: var(--text-primary);
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 0.875rem;
      font-weight: 500;
      cursor: pointer;
      transition: border-color 0.15s ease, background-color 0.15s ease, color 0.15s ease;
    }
    .cta-outlined:hover {
      border-color: var(--accent);
      background: var(--accent-subtle-bg);
      color: var(--accent);
    }

    .cta-text {
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--text-secondary);
      text-decoration: none;
      border-bottom: 1px solid transparent;
      transition: color 0.15s ease, border-color 0.15s ease;
      padding-bottom: 1px;
    }
    .cta-text:hover {
      color: var(--text-primary);
      border-bottom-color: var(--border-color-hover);
    }

    /* Right column: figure */
    .hero-figure {
      display: flex;
      flex-direction: column;
      align-items: center;
      margin: 0;
      padding-top: 0.5rem;
    }

    .pipeline-svg {
      width: 100%;
      max-width: 360px;
      color: var(--text-primary);
    }

    /* Rectangle nodes — paper-like filled boxes */
    .pipeline-svg .node-rect {
      fill: var(--bg-elevated);
      stroke: var(--border-strong);
      stroke-width: 1;
    }
    .pipeline-svg .node-rect--verdict {
      stroke: var(--accent);
      stroke-width: 1.5;
      fill: var(--accent-subtle-bg);
    }

    /* Arrow lines */
    .pipeline-svg .arrow {
      stroke: var(--text-tertiary);
      stroke-width: 1;
    }
    .pipeline-svg .arrowhead {
      fill: var(--text-tertiary);
    }

    /* SVG text styles */
    .pipeline-svg .node-title {
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 10.5px;
      font-weight: 700;
      letter-spacing: 0.08em;
      fill: var(--text-primary);
      text-transform: uppercase;
    }
    .pipeline-svg .node-title--verdict {
      fill: var(--accent);
    }

    .pipeline-svg .node-sub {
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 8.5px;
      letter-spacing: 0.03em;
      fill: var(--text-secondary);
    }

    figcaption {
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 0.8rem;
      font-style: italic;
      color: var(--text-tertiary);
      margin-top: 0.65rem;
      text-align: center;
      max-width: 260px;
      line-height: 1.5;
    }

    /* Mobile stacking */
    @media (max-width: 900px) {
      .hero-inner {
        grid-template-columns: 1fr;
        gap: 2rem;
      }
      .hero { padding: 2.5rem 1.25rem 2rem; }
      .hero-lede { max-width: 100%; }
      .hero-figure {
        padding-top: 0;
        border-top: 1px solid var(--border-color);
        padding-top: 1.5rem;
      }
    }

    @media (max-width: 480px) {
      .hero { padding: 2rem 1rem 1.75rem; }
      .hero-title { font-size: clamp(1.75rem, 6vw, 2.25rem); }
    }
  `]
})
export class HomeHeroComponent {
  @Output() ctaClicked = new EventEmitter<void>();

  scrollToDropzone() {
    this.ctaClicked.emit();
  }
}
