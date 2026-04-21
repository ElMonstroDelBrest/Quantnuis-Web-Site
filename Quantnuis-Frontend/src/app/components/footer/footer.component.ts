import { Component, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-footer',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule, RouterLink],
  template: `
    <footer class="footer">
      <div class="footer-content">
        <span class="footer-affiliation">
          ENSTA Bretagne · Campus de Brest
        </span>
        <div class="footer-links">
          <a href="https://github.com/ElMonstroDelBrest/Quantnuis-Web-Site" target="_blank" rel="noopener">GitHub ↗</a>
          <a routerLink="/about">À propos</a>
          <span class="footer-copy">&copy; {{ currentYear }} Quantnuis</span>
        </div>
      </div>
    </footer>
  `,
  styles: [`
    .footer {
      border-top: 1px solid var(--border-color);
      padding: 1.25rem 1.5rem;
      margin-top: auto;
    }

    .footer-content {
      max-width: 1200px;
      margin: 0 auto;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 1rem;
    }

    .footer-affiliation {
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 0.75rem;
      color: var(--text-tertiary);
      letter-spacing: 0.02em;
    }

    .footer-links {
      display: flex;
      align-items: center;
      gap: 1.5rem;
    }

    .footer-links a {
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 0.78rem;
      color: var(--text-tertiary);
      text-decoration: none;
      transition: color 0.15s ease;
    }

    .footer-links a:hover { color: var(--text-secondary); }

    .footer-copy {
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 0.78rem;
      color: var(--text-tertiary);
    }

    @media (max-width: 600px) {
      .footer { padding: 1rem; }
      .footer-content {
        flex-direction: column;
        gap: 0.5rem;
        text-align: center;
      }
      .footer-links { flex-wrap: wrap; justify-content: center; gap: 1rem; }
    }
  `]
})
export class FooterComponent {
  currentYear = new Date().getFullYear();
}
