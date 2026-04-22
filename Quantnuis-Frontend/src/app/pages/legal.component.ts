import { Component, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';

@Component({
  selector: 'app-legal',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule],
  template: `
    <div class="legal-page">
      <div class="legal-container">

        <!-- Header -->
        <header class="legal-header">
          <span class="section-label">Informations légales</span>
          <h1>{{ pageTitle }}</h1>
          <p class="last-update">Dernière mise à jour : Janvier 2026</p>
        </header>

        <!-- Mentions Légales -->
        <section *ngIf="section === 'mentions'" class="legal-section">

          <div class="legal-sub">
            <h2>1. Éditeur du site</h2>
            <p><strong>Nom du projet :</strong> Quantnuis</p>
            <p><strong>Nature :</strong> Projet universitaire à but éducatif et de recherche</p>
            <p><strong>Établissement :</strong> ENSTA Bretagne · Campus de Brest</p>
            <p><strong>Contact :</strong> <a href="mailto:georgedanielgherasim@gmail.com">georgedanielgherasim&#64;gmail.com</a></p>
          </div>

          <div class="legal-sub">
            <h2>2. Hébergement</h2>
            <p><strong>Hébergeur :</strong> Amazon Web Services (AWS)</p>
            <p><strong>Service :</strong> Amazon CloudFront (origine S3 statique) et AWS Lambda pour l'inférence</p>
            <p><strong>Région :</strong> eu-west-3 (Paris)</p>
          </div>

          <div class="legal-sub">
            <h2>3. Propriété intellectuelle</h2>
            <p>
              Ce projet est développé dans un cadre universitaire. Le code source est disponible
              sous licence open source (licence à confirmer). Les technologies utilisées (TensorFlow,
              Angular, Python) sont la propriété de leurs détenteurs respectifs.
            </p>
          </div>

          <div class="legal-sub">
            <h2>4. Responsabilité</h2>
            <p>
              Quantnuis est un projet à but éducatif et de démonstration. Les résultats d'analyse
              sont fournis à titre indicatif et ne constituent pas une expertise officielle.
              L'équipe décline toute responsabilité quant à l'utilisation des résultats.
            </p>
          </div>

        </section>

        <!-- Politique de confidentialité -->
        <section *ngIf="section === 'privacy'" class="legal-section">

          <div class="legal-sub">
            <h2>1. Collecte des données</h2>
            <p>
              Quantnuis collecte uniquement les données nécessaires au fonctionnement du service :
            </p>
            <ul>
              <li><strong>Compte utilisateur :</strong> adresse email et mot de passe (haché)</li>
              <li><strong>Fichiers audio :</strong> traités en temps réel, non stockés après analyse</li>
              <li><strong>Historique :</strong> résultats d'analyses pour les utilisateurs connectés</li>
            </ul>
          </div>

          <div class="legal-sub">
            <h2>2. Utilisation des données</h2>
            <p>Vos données sont utilisées exclusivement pour :</p>
            <ul>
              <li>authentification et gestion de votre compte ;</li>
              <li>analyse des fichiers audio soumis ;</li>
              <li>amélioration du service (données anonymisées).</li>
            </ul>
          </div>

          <div class="legal-sub">
            <h2>3. Stockage et sécurité</h2>
            <p><strong>Chiffrement :</strong> toutes les communications sont chiffrées (HTTPS).</p>
            <p><strong>Fichiers audio :</strong> supprimés immédiatement après analyse.</p>
            <p><strong>Mots de passe :</strong> hachés avec bcrypt, jamais stockés en clair.</p>
          </div>

          <div class="legal-sub">
            <h2>4. Vos droits (RGPD)</h2>
            <p>Conformément au RGPD, vous disposez des droits suivants :</p>
            <ul>
              <li><strong>Accès :</strong> obtenir une copie de vos données ;</li>
              <li><strong>Rectification :</strong> corriger vos informations ;</li>
              <li><strong>Suppression :</strong> demander l'effacement de votre compte ;</li>
              <li><strong>Portabilité :</strong> exporter vos données.</li>
            </ul>
            <p>
              Pour exercer ces droits, contactez-nous à
              <a href="mailto:georgedanielgherasim@gmail.com">georgedanielgherasim&#64;gmail.com</a>.
            </p>
          </div>

        </section>

        <!-- Conditions d'utilisation -->
        <section *ngIf="section === 'terms'" class="legal-section">

          <div class="legal-sub">
            <h2>1. Acceptation des conditions</h2>
            <p>
              En utilisant Quantnuis, vous acceptez les présentes conditions d'utilisation.
              Si vous n'acceptez pas ces conditions, veuillez ne pas utiliser le service.
            </p>
          </div>

          <div class="legal-sub">
            <h2>2. Description du service</h2>
            <p>
              Quantnuis est une plateforme d'analyse de nuisances sonores utilisant
              l'intelligence artificielle. Le service permet de :
            </p>
            <ul>
              <li>analyser des fichiers audio pour détecter la présence de véhicules ;</li>
              <li>estimer le niveau sonore et identifier les véhicules bruyants ;</li>
              <li>consulter l'historique des analyses (utilisateurs connectés).</li>
            </ul>
          </div>

          <div class="legal-sub">
            <h2>3. Utilisation acceptable</h2>
            <p>Vous vous engagez à :</p>
            <ul>
              <li>ne pas soumettre de contenus illégaux ou malveillants ;</li>
              <li>ne pas tenter de compromettre la sécurité du service ;</li>
              <li>ne pas utiliser le service à des fins commerciales sans autorisation ;</li>
              <li>respecter les droits d'auteur des fichiers audio soumis.</li>
            </ul>
          </div>

          <div class="legal-sub">
            <h2>4. Limitation de responsabilité</h2>
            <p>
              Les résultats fournis par Quantnuis sont à titre <strong>indicatif uniquement</strong>.
              Ils ne constituent pas une mesure officielle et ne peuvent être utilisés comme
              preuve légale. Le service est un outil de recherche et de démonstration.
            </p>
          </div>

          <div class="legal-sub">
            <h2>5. Modifications</h2>
            <p>
              Nous nous réservons le droit de modifier ces conditions à tout moment.
              Les utilisateurs seront informés des changements majeurs par email.
            </p>
          </div>

        </section>

      </div>
    </div>
  `,
  styles: [`
    .legal-page {
      min-height: calc(100vh - 64px);
      padding: 4rem 1.5rem;
      background: var(--bg-page);
    }

    .legal-container {
      max-width: 720px;
      margin: 0 auto;
    }

    /* ===== HEADER ===== */
    .legal-header {
      margin-bottom: 3rem;
      padding-bottom: 2rem;
      border-bottom: 1px solid var(--border-color);
    }

    .legal-header .section-label {
      margin-bottom: 0.75rem;
    }

    .legal-header h1 {
      font-family: var(--font-serif);
      font-size: clamp(1.75rem, 3vw + 0.5rem, 2.25rem);
      font-weight: 600;
      letter-spacing: -0.015em;
      color: var(--text-primary);
      margin-bottom: 0.5rem;
    }

    .last-update {
      font-family: var(--font-sans);
      font-size: 0.85rem;
      color: var(--text-tertiary);
      margin: 0;
    }

    /* ===== LEGAL SECTION ===== */
    .legal-section {
      display: flex;
      flex-direction: column;
      gap: 0;
    }

    /* ===== LEGAL SUB-SECTIONS ===== */
    .legal-sub {
      padding: 2rem 0;
      border-top: 1px solid var(--border-color);
    }

    .legal-sub:first-child {
      border-top: none;
      padding-top: 0;
    }

    .legal-sub h2 {
      font-family: var(--font-sans);
      font-size: 0.95rem;
      font-weight: 600;
      color: var(--text-primary);
      margin-bottom: 0.85rem;
      letter-spacing: -0.01em;
    }

    .legal-sub p {
      font-family: var(--font-sans);
      font-size: 0.9rem;
      color: var(--text-secondary);
      line-height: 1.7;
      margin-bottom: 0.65rem;
    }

    .legal-sub p:last-child {
      margin-bottom: 0;
    }

    .legal-sub ul {
      font-family: var(--font-sans);
      font-size: 0.9rem;
      color: var(--text-secondary);
      line-height: 1.7;
      margin-bottom: 0.65rem;
      padding-left: 1.25rem;
    }

    .legal-sub li {
      margin-bottom: 0.35rem;
    }

    .legal-sub a {
      color: var(--accent);
      text-decoration: none;
    }

    .legal-sub a:hover {
      color: var(--accent-hover);
      text-decoration: underline;
    }

    /* ===== RESPONSIVE ===== */
    @media (max-width: 768px) {
      .legal-page {
        padding: 2.5rem 1.25rem;
      }
    }

    @media (max-width: 480px) {
      .legal-page {
        padding: 2rem 1rem;
      }
    }
  `]
})
export class LegalComponent {
  section: 'mentions' | 'privacy' | 'terms' = 'mentions';
  pageTitle = 'Mentions légales';

  constructor(private route: ActivatedRoute) {
    this.route.data.subscribe(data => {
      this.section = data['section'] || 'mentions';
      this.updateTitle();
    });
  }

  private updateTitle() {
    switch (this.section) {
      case 'mentions':
        this.pageTitle = 'Mentions légales';
        break;
      case 'privacy':
        this.pageTitle = 'Politique de confidentialité';
        break;
      case 'terms':
        this.pageTitle = "Conditions d'utilisation";
        break;
    }
  }
}
