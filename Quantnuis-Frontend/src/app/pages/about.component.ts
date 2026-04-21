import { Component, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-about',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule],
  template: `
    <div class="about-page">

      <!-- Page header -->
      <header class="page-header">
        <div class="page-header-inner">
          <span class="overline">À PROPOS · QUANTNUIS</span>
          <h1>Un projet étudiant de détection audio des véhicules bruyants.</h1>
          <p class="editorial-prose lede">
            Quantnuis est un projet de recherche appliquée conduit à ENSTA Bretagne (Brest).
            Il vise à automatiser la surveillance des nuisances sonores routières par
            apprentissage automatique sur des enregistrements audio urbains.
          </p>
        </div>
      </header>

      <!-- §A1 · Contexte -->
      <section class="paper-section" aria-labelledby="contexte-heading">
        <div class="paper-section-inner">
          <span class="section-label">§A1 · Contexte</span>
          <h2 id="contexte-heading">Pourquoi ce projet ?</h2>
          <p class="editorial-prose">
            L'exposition prolongée au bruit routier est reconnue comme un facteur de risque
            pour la santé publique (troubles du sommeil, maladies cardiovasculaires). Le
            décret n° 2022-125 fixe un seuil de 85 dB à deux mètres pour les véhicules en
            circulation, mais les contrôles restent ponctuels et nécessitent la présence
            d'agents équipés de sonomètres. Les Zones à Faibles Émissions (ZFE) renforcent
            le besoin d'outils de surveillance objective.
          </p>
          <p class="editorial-prose">
            Ce projet est développé en 2025–2026 dans le cadre d'un projet de 2e année
            du cycle ingénieur à ENSTA Bretagne par une équipe de quatre étudiants,
            sous la direction du Dr Dorian Cazau. L'objectif est de produire un prototype
            fonctionnel capable de classifier automatiquement des extraits audio de trois
            secondes selon deux questions binaires : y a-t-il un véhicule ? est-il bruyant
            au sens réglementaire ?
          </p>
        </div>
      </section>

      <!-- §A2 · Équipe -->
      <section class="paper-section" aria-labelledby="equipe-heading">
        <div class="paper-section-inner">
          <span class="section-label">§A2 · Équipe</span>
          <h2 id="equipe-heading">Contributeurs.</h2>

          <div class="team-list" role="list">

            <div class="team-row" role="listitem">
              <div class="avatar" aria-hidden="true">NB</div>
              <div class="team-info">
                <span class="team-name">Nathan Boué</span>
                <span class="team-role">2A · ENSTA Bretagne · Cycle ingénieur</span>
              </div>
            </div>

            <div class="team-row" role="listitem">
              <div class="avatar" aria-hidden="true">DG</div>
              <div class="team-info">
                <span class="team-name">Daniel Gherasim</span>
                <span class="team-role">2A · ENSTA Bretagne · Cycle ingénieur</span>
              </div>
            </div>

            <div class="team-row" role="listitem">
              <div class="avatar" aria-hidden="true">NM</div>
              <div class="team-info">
                <span class="team-name">Nour Mourtada</span>
                <span class="team-role">2A · ENSTA Bretagne · Cycle ingénieur</span>
              </div>
            </div>

            <div class="team-row" role="listitem">
              <div class="avatar" aria-hidden="true">OP</div>
              <div class="team-info">
                <span class="team-name">Owen Perdigues</span>
                <span class="team-role">2A · ENSTA Bretagne · Cycle ingénieur</span>
              </div>
            </div>

            <div class="team-row team-row--supervisor" role="listitem">
              <div class="avatar" aria-hidden="true">DC</div>
              <div class="team-info">
                <span class="team-name">Dorian Cazau</span>
                <span class="team-role">
                  Encadrant · ENSTA Bretagne — direction scientifique et encadrement du projet.
                </span>
              </div>
            </div>

          </div>
        </div>
      </section>

      <!-- §A3 · Stack technique -->
      <section class="paper-section" aria-labelledby="stack-heading">
        <div class="paper-section-inner">
          <span class="section-label">§A3 · Stack technique</span>
          <h2 id="stack-heading">Technologies employées.</h2>

          <table class="paper-table" aria-label="Stack technique">
            <thead>
              <tr>
                <th scope="col">Couche</th>
                <th scope="col">Technologie</th>
                <th scope="col">Rôle</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Modèles IA</td>
                <td>TensorFlow 2.15 · Python 3.11</td>
                <td>Réseaux de neurones convolutifs (CNN / CRNN) pour la classification audio</td>
              </tr>
              <tr>
                <td>Features audio</td>
                <td>Librosa</td>
                <td>Extraction de mel-spectrogrammes, MFCC, features spectrales et harmoniques</td>
              </tr>
              <tr>
                <td>API d'inférence</td>
                <td>FastAPI · Docker</td>
                <td>Endpoint REST POST /predict, conteneurisé et déployé sur AWS Lambda</td>
              </tr>
              <tr>
                <td>API applicative</td>
                <td>FastAPI · PostgreSQL · Nginx</td>
                <td>Authentification JWT, historique, gestion utilisateurs (EC2)</td>
              </tr>
              <tr>
                <td>Frontend</td>
                <td>Angular 21 · TypeScript</td>
                <td>Interface SPA standalone, dark / light theme, composants autonomes</td>
              </tr>
              <tr>
                <td>Infra cloud</td>
                <td>AWS Lambda · EC2 · S3 · CloudFront</td>
                <td>Inférence serverless, serveur applicatif, stockage statique et audio</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- §A4 · Remerciements -->
      <section class="paper-section" aria-labelledby="remerciements-heading">
        <div class="paper-section-inner">
          <span class="section-label">§A4 · Remerciements</span>
          <h2 id="remerciements-heading">Remerciements.</h2>
          <p class="editorial-prose">
            L'équipe remercie ENSTA Bretagne pour l'accueil et les ressources informatiques
            mises à disposition, ainsi que Dorian Cazau pour son encadrement et ses retours
            tout au long du projet.
          </p>
        </div>
      </section>

      <!-- §A5 · Dépôt & ressources -->
      <section class="paper-section" aria-labelledby="depot-heading">
        <div class="paper-section-inner">
          <span class="section-label">§A5 · Dépôt &amp; ressources</span>
          <h2 id="depot-heading">Code source.</h2>
          <p class="editorial-prose">
            Le code source du projet (frontend, backend, scripts d'entraînement)
            est disponible sur GitHub.
          </p>
          <div class="cta-row">
            <a
              href="https://github.com/ElMonstroDelBrest/Quantnuis-Web-Site"
              target="_blank"
              rel="noopener noreferrer"
              class="cta-outlined"
            >
              Voir sur GitHub ↗
            </a>
          </div>
          <p class="licence-note">Licence : à confirmer (TBD).</p>
        </div>
      </section>

    </div>
  `,
  styles: [`
    .about-page {
      min-height: calc(100vh - 64px);
    }

    /* ===== PAGE HEADER ===== */
    .page-header {
      border-bottom: 1px solid var(--border-color);
      padding: 4rem 1.5rem 3rem;
    }

    .page-header-inner {
      max-width: 880px;
      margin: 0 auto;
    }

    .page-header .overline {
      margin-bottom: 1rem;
    }

    .page-header h1 {
      font-family: var(--font-serif);
      font-size: clamp(1.75rem, 3vw + 0.5rem, 2.5rem);
      font-weight: 600;
      letter-spacing: -0.015em;
      line-height: 1.15;
      color: var(--text-primary);
      margin-bottom: 1.25rem;
      max-width: 720px;
    }

    .lede {
      max-width: 640px;
    }

    /* ===== PAPER SECTIONS ===== */
    .paper-section {
      border-top: 1px solid var(--border-color);
    }

    .paper-section:nth-of-type(even) {
      background: var(--overlay-weak);
    }

    .paper-section-inner {
      max-width: 880px;
      margin: 0 auto;
      padding: 4rem 1.5rem;
    }

    .paper-section-inner .section-label {
      margin-bottom: 0.75rem;
    }

    .paper-section-inner h2 {
      font-family: var(--font-serif);
      font-size: clamp(1.25rem, 1.8vw + 0.7rem, 1.65rem);
      font-weight: 600;
      letter-spacing: -0.015em;
      color: var(--text-primary);
      margin-bottom: 1.25rem;
      line-height: 1.25;
      max-width: 680px;
    }

    .editorial-prose {
      font-family: var(--font-serif);
      font-size: 1.05rem;
      line-height: 1.7;
      color: var(--text-secondary);
      max-width: 680px;
      margin-bottom: 1rem;
    }

    .editorial-prose:last-child {
      margin-bottom: 0;
    }

    /* ===== TEAM LIST ===== */
    .team-list {
      display: flex;
      flex-direction: column;
      gap: 0;
      margin-top: 0.5rem;
    }

    .team-row {
      display: flex;
      align-items: flex-start;
      gap: 1.25rem;
      padding: 1.25rem 0;
      border-top: 1px solid var(--border-color);
    }

    .team-row:first-child {
      border-top: none;
      padding-top: 0;
    }

    .avatar {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background: var(--accent-subtle-bg);
      border: 1px solid var(--border-color-hover);
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: var(--font-sans);
      font-size: 0.75rem;
      font-weight: 700;
      color: var(--accent);
      letter-spacing: 0.04em;
      flex-shrink: 0;
    }

    .avatar--anon {
      background: var(--bg-surface);
      color: var(--text-tertiary);
    }

    .team-info {
      display: flex;
      flex-direction: column;
      gap: 0.3rem;
      padding-top: 0.1rem;
    }

    .team-name {
      font-family: var(--font-sans);
      font-size: 0.95rem;
      font-weight: 600;
      color: var(--text-primary);
    }

    .team-role {
      font-family: var(--font-sans);
      font-size: 0.875rem;
      color: var(--text-secondary);
      line-height: 1.55;
    }

    /* ===== PAPER TABLE ===== */
    .paper-table {
      width: 100%;
      max-width: 780px;
      border-collapse: collapse;
      font-family: var(--font-sans);
      font-size: 0.875rem;
      margin-top: 0.5rem;
    }

    .paper-table thead th {
      text-align: left;
      font-size: 0.72rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--text-tertiary);
      padding: 0 1rem 0.75rem 0;
      border-bottom: 1px solid var(--border-color);
    }

    .paper-table thead th:last-child {
      padding-right: 0;
    }

    .paper-table tbody tr {
      border-bottom: 1px solid var(--border-color);
    }

    .paper-table tbody tr:last-child {
      border-bottom: none;
    }

    .paper-table tbody td {
      padding: 0.85rem 1rem 0.85rem 0;
      color: var(--text-secondary);
      vertical-align: top;
      line-height: 1.5;
    }

    .paper-table tbody td:last-child {
      padding-right: 0;
    }

    .paper-table tbody td:first-child {
      color: var(--text-primary);
      font-weight: 600;
      white-space: nowrap;
    }

    .paper-table tbody td:nth-child(2) {
      font-family: var(--font-mono);
      font-size: 0.8rem;
      color: var(--text-secondary);
      white-space: nowrap;
    }

    /* ===== CTA ROW ===== */
    .cta-row {
      margin: 1.5rem 0 0.75rem;
    }

    .cta-outlined {
      display: inline-flex;
      align-items: center;
      padding: 0.5rem 1rem;
      background: transparent;
      border: 1px solid var(--border-color-hover);
      border-radius: var(--radius-sm);
      color: var(--text-primary);
      font-family: var(--font-sans);
      font-size: 0.875rem;
      font-weight: 500;
      text-decoration: none;
      transition: border-color 0.15s ease, background-color 0.15s ease, color 0.15s ease;
    }

    .cta-outlined:hover {
      border-color: var(--accent);
      background: var(--accent-subtle-bg);
      color: var(--accent);
    }

    .licence-note {
      font-family: var(--font-sans);
      font-size: 0.8rem;
      color: var(--text-tertiary);
      margin: 0;
    }

    /* ===== RESPONSIVE ===== */
    @media (max-width: 768px) {
      .page-header {
        padding: 2.5rem 1.25rem 2rem;
      }

      .paper-section-inner {
        padding: 2.5rem 1.25rem;
      }

      .paper-table tbody td:nth-child(2) {
        white-space: normal;
      }

      .paper-table tbody td:first-child {
        white-space: normal;
      }
    }

    @media (max-width: 600px) {
      .paper-table {
        display: block;
        overflow-x: auto;
      }
    }

    @media (max-width: 480px) {
      .page-header {
        padding: 2rem 1rem 1.75rem;
      }

      .paper-section-inner {
        padding: 2rem 1rem;
      }
    }
  `]
})
export class AboutComponent {}
