import { Component, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-not-found',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="not-found-page">
      <div class="not-found-container">
        <div class="illustration">
          <div class="error-code">404</div>
        </div>

        <div class="content">
          <h1>Page introuvable</h1>
          <p>La page que vous recherchez n'existe pas ou a été déplacée.</p>

          <div class="actions">
            <a routerLink="/" class="btn-back">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
                <polyline points="9 22 9 12 15 12 15 22"/>
              </svg>
              Retour à l'accueil
            </a>
          </div>
        </div>

        <div class="suggestions">
          <h3>Peut-être cherchiez-vous :</h3>
          <div class="links">
            <a routerLink="/about">À propos</a>
            <a routerLink="/methodology">Méthodologie</a>
            <a routerLink="/dashboard">Dashboard</a>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .not-found-page {
      min-height: 80vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 2rem;
    }

    .not-found-container {
      text-align: center;
      max-width: 480px;
      animation: fadeInUp 0.5s var(--ease-out-expo) both;
    }

    @keyframes fadeInUp {
      from { opacity: 0; transform: translateY(12px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .illustration { margin-bottom: 2rem; }

    .error-code {
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 6rem;
      font-weight: 800;
      color: var(--text-primary);
      opacity: 0.12;
      line-height: 1;
      letter-spacing: -0.04em;
    }

    .content h1 {
      font-family: 'Newsreader', 'Charter', 'Georgia', serif;
      font-size: 1.75rem;
      font-weight: 600;
      color: var(--text-primary);
      margin-bottom: 0.75rem;
      letter-spacing: -0.015em;
    }

    .content p {
      font-size: 1rem;
      color: var(--text-secondary);
      line-height: 1.6;
      margin-bottom: 2rem;
    }

    .actions {
      display: flex;
      gap: 1rem;
      justify-content: center;
    }

    .btn-back {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.55rem 1.15rem;
      background: transparent;
      border: 1px solid var(--border-color-hover);
      border-radius: var(--radius-sm);
      color: var(--text-primary);
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 0.875rem;
      font-weight: 500;
      text-decoration: none;
      transition: border-color 0.15s ease, background 0.15s ease, color 0.15s ease;
    }
    .btn-back:hover {
      border-color: var(--accent);
      background: var(--accent-subtle-bg);
      color: var(--accent);
    }
    .btn-back svg { width: 16px; height: 16px; }

    .suggestions {
      margin-top: 2.5rem;
      padding-top: 1.5rem;
      border-top: 1px solid var(--border-color);
    }

    .suggestions h3 {
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--text-tertiary);
      margin-bottom: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.1em;
    }

    .links {
      display: flex;
      gap: 1.5rem;
      justify-content: center;
      flex-wrap: wrap;
    }

    .links a {
      font-family: 'Inter', system-ui, sans-serif;
      color: var(--text-secondary);
      text-decoration: none;
      font-size: 0.875rem;
      transition: color 0.15s ease;
    }

    .links a:hover { color: var(--accent); }

    @media (max-width: 480px) {
      .error-code { font-size: 4.5rem; }
      .content h1 { font-size: 1.4rem; }
    }
  `]
})
export class NotFoundComponent {}
