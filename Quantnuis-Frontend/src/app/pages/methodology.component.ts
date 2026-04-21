import { Component, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-methodology',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule],
  template: `
    <div class="methodology-page">

      <!-- Page header -->
      <header class="page-header">
        <div class="page-header-inner">
          <span class="overline">MÉTHODOLOGIE · PIPELINE DE DÉTECTION</span>
          <h1>Classification audio en cascade pour la détection de véhicules bruyants.</h1>
          <p class="editorial-prose lede">
            Le pipeline repose sur deux modèles de réseaux de neurones convolutifs appliqués
            séquentiellement à des mel-spectrogrammes extraits d'extraits audio de trois
            secondes. Le premier modèle isole les passages contenant un véhicule ; le second
            estime si le niveau sonore dépasse le seuil réglementaire.
          </p>
        </div>
      </header>

      <!-- §M1 · Problème -->
      <section class="paper-section" aria-labelledby="probleme-heading">
        <div class="paper-section-inner">
          <span class="section-label">§M1 · Problème</span>
          <h2 id="probleme-heading">Détecter un véhicule bruyant depuis un enregistrement audio est un problème difficile.</h2>
          <p class="editorial-prose">
            Un enregistrement audio urbain contient une superposition de sources sonores
            hétérogènes : voix, vent, klaxons, musique, bruits de pas. Isoler la contribution
            d'un seul véhicule et juger si elle dépasse un seuil de pression acoustique requiert
            soit une instrumentation de mesure précise (sonomètre étalonné), soit un modèle
            capable d'apprendre des représentations spectrales discriminantes à partir d'exemples
            annotés.
          </p>
          <p class="editorial-prose">
            Le cadre légal français fournit un seuil opérationnel : le décret n° 2022-125
            interdit aux véhicules de dépasser 85 dB à deux mètres en conditions d'accélération.
            Dans les Zones à Faibles Émissions (ZFE) et face aux plaintes de riverains, les
            collectivités manquent d'outils de surveillance continue. Les agents habilités à
            effectuer des mesures sont peu nombreux et ne peuvent assurer qu'une présence
            ponctuelle. C'est ce manque que Quantnuis cherche à combler.
          </p>
        </div>
      </section>

      <!-- §M2 · Approche -->
      <section class="paper-section" aria-labelledby="approche-heading">
        <div class="paper-section-inner">
          <span class="section-label">§M2 · Approche</span>
          <h2 id="approche-heading">Pourquoi une architecture en cascade plutôt qu'un modèle unique ?</h2>
          <p class="editorial-prose">
            Un classifieur binaire unique entraîné directement sur la question « ce son est-il
            un véhicule bruyant ? » souffre d'un déséquilibre de classes sévère : la grande
            majorité des extraits audio urbains ne contiennent pas de véhicule. De plus, un
            modèle monolithique doit apprendre simultanément deux discriminations de nature
            différente — présence d'un véhicule (reconnaissance d'objet acoustique) et niveau
            sonore (estimation d'intensité relative).
          </p>
          <p class="editorial-prose">
            La cascade découple ces deux tâches. Le premier modèle (CarDetector) est entraîné
            exclusivement sur la présence ou l'absence d'un véhicule, avec un jeu de données
            pouvant inclure des véhicules silencieux. Il filtre les faux positifs dus aux bruits
            ambiants non véhiculaires. Le second modèle (NoisyCarDetector) ne voit que les
            extraits ayant passé le filtre : il peut se spécialiser sur les différences spectrales
            entre un véhicule conforme et un véhicule bruyant, indépendamment du contexte sonore
            ambiant.
          </p>
        </div>
      </section>

      <!-- §M3 · Architecture -->
      <section class="paper-section" aria-labelledby="architecture-heading">
        <div class="paper-section-inner">
          <span class="section-label">§M3 · Architecture</span>
          <h2 id="architecture-heading">Pipeline en deux étages.</h2>

          <figure class="pipeline-figure">
            <svg
              class="pipeline-svg"
              viewBox="-70 0 410 440"
              xmlns="http://www.w3.org/2000/svg"
              role="img"
              aria-label="Diagramme de l'architecture en cascade : Audio brut → Feature extraction → CarDetector CNN → NoisyCarDetector CNN → Verdict"
            >
              <!-- Node 1: Audio brut -->
              <rect class="node-rect" x="30" y="10" width="280" height="64" rx="4"/>
              <text x="170" y="37" text-anchor="middle" class="node-title">AUDIO BRUT</text>
              <text x="170" y="57" text-anchor="middle" class="node-sub">WAV · 16 kHz · extrait de 3 s</text>

              <!-- Arrow 1→2 -->
              <line class="arrow" x1="170" y1="74" x2="170" y2="100"/>
              <polygon class="arrowhead" points="164,96 170,106 176,96"/>

              <!-- Node 2: Feature extraction -->
              <rect class="node-rect" x="30" y="106" width="280" height="64" rx="4"/>
              <text x="170" y="133" text-anchor="middle" class="node-title">EXTRACTION DE FEATURES</text>
              <text x="170" y="153" text-anchor="middle" class="node-sub">Mel-spectrogramme · 128 bandes · 173 frames</text>

              <!-- Arrow 2→3 -->
              <line class="arrow" x1="170" y1="170" x2="170" y2="196"/>
              <polygon class="arrowhead" points="164,192 170,202 176,192"/>

              <!-- Node 3: CarDetector -->
              <rect class="node-rect" x="30" y="202" width="280" height="64" rx="4"/>
              <text x="170" y="229" text-anchor="middle" class="node-title">CARDETECTOR</text>
              <text x="170" y="249" text-anchor="middle" class="node-sub">CRNN · Détection de présence véhicule</text>

              <!-- Branching label: aucun véhicule (pipeline exit if no car detected) -->
              <line class="arrow arrow--branch" x1="30" y1="234" x2="-10" y2="234"/>
              <polygon class="arrowhead" points="-14,230 -22,234 -14,238" fill="currentColor"/>
              <text x="-28" y="230" text-anchor="end" class="branch-label">aucun</text>
              <text x="-28" y="244" text-anchor="end" class="branch-label">véhicule</text>
              <text x="-28" y="258" text-anchor="end" class="branch-label">détecté</text>

              <!-- Arrow 3→4 -->
              <line class="arrow" x1="170" y1="266" x2="170" y2="292"/>
              <polygon class="arrowhead" points="164,288 170,298 176,288"/>

              <!-- Node 4: NoisyCarDetector -->
              <rect class="node-rect" x="30" y="298" width="280" height="64" rx="4"/>
              <text x="170" y="325" text-anchor="middle" class="node-title">NOISYCARDETECTOR</text>
              <text x="170" y="345" text-anchor="middle" class="node-sub">CNN · Estimation du niveau sonore</text>

              <!-- Arrow 4→5 -->
              <line class="arrow" x1="170" y1="362" x2="170" y2="388"/>
              <polygon class="arrowhead" points="164,384 170,394 176,384"/>

              <!-- Node 5: Verdict -->
              <rect class="node-rect node-rect--verdict" x="30" y="394" width="280" height="36" rx="4"/>
              <text x="170" y="416" text-anchor="middle" class="node-title node-title--verdict">VERDICT · niveau ≥ 85 dB à 2 m ?</text>
            </svg>
            <figcaption>
              Figure 1. Architecture en cascade — CarDetector (CRNN) puis NoisyCarDetector (CNN).
              Chaque modèle est entraîné indépendamment sur des features mel-spectrogrammes
              extraites d'extraits audio de 3 s. Si CarDetector ne détecte pas de véhicule,
              NoisyCarDetector n'est pas sollicité.
            </figcaption>
          </figure>
        </div>
      </section>

      <!-- §M4 · Données -->
      <section class="paper-section" aria-labelledby="donnees-heading">
        <div class="paper-section-inner">
          <span class="section-label">§M4 · Données</span>
          <h2 id="donnees-heading">Jeu de données.</h2>
          <p class="editorial-prose">
            Les modèles sont entraînés sur des enregistrements réels de véhicules en milieu
            urbain, annotés manuellement. Le jeu d'entraînement du NoisyCarDetector contient
            environ 47 000 échantillons équilibrés par sur-échantillonnage SMOTE (chiffres
            précis à confirmer). Le dataset du CarDetector couvre environ 28 800 échantillons
            en validation croisée 5 folds. La durée totale d'audio annoté représente
            approximativement 12 heures d'enregistrements urbains.
          </p>
          <p class="editorial-prose">
            Les features d'entrée sont des mel-spectrogrammes de dimension (128, 173, 1) :
            128 bandes mel et 173 frames temporelles couvrant 3 à 4 secondes à 22 050 Hz
            avec un hop length de 512 échantillons. Avant entraînement, les spectrogrammes
            sont convertis en dB puis normalisés par les statistiques du jeu d'entraînement
            (moyenne −30,82 dB, écart-type 12,15 dB pour NoisyCarDetector ; valeurs à
            vérifier pour CarDetector).
          </p>
          <!-- NOTE: ces chiffres proviennent des accordéons de l'ancienne page — à confirmer par l'auteur -->
        </div>
      </section>

      <!-- §M5 · Entraînement -->
      <section class="paper-section" aria-labelledby="entrainement-heading">
        <div class="paper-section-inner">
          <span class="section-label">§M5 · Entraînement</span>
          <h2 id="entrainement-heading">Configuration d'entraînement.</h2>

          <dl class="train-list" aria-label="Paramètres d'entraînement">

            <div class="train-row">
              <dt>Architecture CarDetector</dt>
              <dd>CRNN — 3 blocs Conv2D (16 → 32 → 64 filtres), BatchNorm + Dropout, couche GRU (128 unités), Dense (64) → Sigmoid</dd>
            </div>

            <div class="train-row">
              <dt>Architecture NoisyCarDetector</dt>
              <dd>CNN — 4 blocs Conv2D (32 → 64 → 128 → 256 filtres), BatchNorm + Dropout progressif (0,2 → 0,4), Global Average Pooling, Dense (128) → Sigmoid</dd>
            </div>

            <div class="train-row">
              <dt>Optimiseur</dt>
              <dd>Adam, learning rate 1 × 10⁻³</dd>
            </div>

            <div class="train-row">
              <dt>Taille de batch</dt>
              <dd>32</dd>
            </div>

            <div class="train-row">
              <dt>Époques</dt>
              <dd>Jusqu'à 100, avec early stopping (patience = 10)</dd>
            </div>

            <div class="train-row">
              <dt>Réduction du learning rate</dt>
              <dd>ReduceLROnPlateau — facteur 0,5, patience 5</dd>
            </div>

            <div class="train-row">
              <dt>Validation</dt>
              <dd>Validation croisée 5 folds ; split 20 % sur chaque fold</dd>
            </div>

            <div class="train-row">
              <dt>Augmentation de données</dt>
              <dd>Shift temporel, bruit gaussien, SpecAugment (CarDetector)</dd>
            </div>

          </dl>

          <p class="train-note">
            Les scripts d'entraînement complets sont disponibles dans le dépôt GitHub.
          </p>
        </div>
      </section>

      <!-- §M6 · Évaluation -->
      <section class="paper-section" aria-labelledby="evaluation-heading">
        <div class="paper-section-inner">
          <span class="section-label">§M6 · Évaluation</span>
          <h2 id="evaluation-heading">Métriques de performance.</h2>
          <p class="editorial-prose">
            Les métriques ci-dessous sont mesurées en validation croisée 5 folds sur le
            jeu de test de chaque modèle, avec le seuil de décision par défaut à 0,5.
          </p>

          <!-- NOTE: valeurs placeholders — à remplacer par les résultats définitifs -->
          <table class="paper-table metrics-table" aria-label="Métriques de performance des modèles">
            <thead>
              <tr>
                <th scope="col">Modèle</th>
                <th scope="col">Précision</th>
                <th scope="col">Rappel</th>
                <th scope="col">F1</th>
                <th scope="col">Seuil</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>CarDetector</td>
                <!-- placeholder -->
                <td>—</td>
                <td>—</td>
                <td>0,73 ± 0,03</td>
                <td>0,5</td>
              </tr>
              <tr>
                <td>NoisyCarDetector</td>
                <!-- placeholder -->
                <td>—</td>
                <td>—</td>
                <td>0,99 ± 0,001</td>
                <td>0,5</td>
              </tr>
            </tbody>
          </table>
          <p class="table-note">
            Précision et rappel individuels à compléter. Les scores F1 ci-dessus proviennent
            de la validation croisée 5 folds (valeurs à confirmer par l'auteur).
          </p>
        </div>
      </section>

      <!-- §M7 · Limitations & perspectives -->
      <section class="paper-section" aria-labelledby="limitations-heading">
        <div class="paper-section-inner">
          <span class="section-label">§M7 · Limitations &amp; perspectives</span>
          <h2 id="limitations-heading">Limites actuelles et directions futures.</h2>
          <p class="editorial-prose">
            Le dataset d'entraînement est de taille modeste et issu d'environnements urbains
            spécifiques. Les conditions météorologiques (pluie, vent), la densité de circulation
            et les types de revêtement routier ne sont pas équilibrés dans les données. Ces
            biais peuvent affecter les performances sur des enregistrements pris dans des
            contextes différents.
          </p>
          <p class="editorial-prose">
            Par ailleurs, le modèle n'effectue pas de mesure directe du niveau de pression
            acoustique (SPL) en dBSPL : il estime une classification binaire à partir de
            représentations spectrales relatives. Le seuil de 85 dB est donc un proxy appris
            sur des données annotées, non une mesure physique calibrée. Des travaux futurs
            pourraient explorer des architectures fondées sur l'apprentissage auto-supervisé
            (SSL) pour améliorer la généralisation sur de nouvelles conditions acoustiques,
            ainsi qu'une collecte de données plus diversifiée couvrant plusieurs villes et
            saisons.
          </p>
        </div>
      </section>

      <!-- §M8 · Code & ressources -->
      <section class="paper-section" aria-labelledby="ressources-heading">
        <div class="paper-section-inner">
          <span class="section-label">§M8 · Code &amp; ressources</span>
          <h2 id="ressources-heading">Dépôt et documentation.</h2>
          <p class="editorial-prose">
            Les poids des modèles, les scripts d'entraînement, le code du backend et de
            l'interface sont disponibles dans le dépôt public du projet.
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
          <p class="ressources-tags">
            Mots-clés : classification audio CNN · mel-spectrogram · vehicle noise detection ·
            cascade architecture · CRNN · TensorFlow · ENSTA Bretagne
          </p>
        </div>
      </section>

    </div>
  `,
  styles: [`
    .methodology-page {
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
      max-width: 680px;
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

    /* ===== PIPELINE FIGURE ===== */
    .pipeline-figure {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: 0.65rem;
      margin: 0.5rem 0 0;
    }

    .pipeline-figure {
      display: flex;
      flex-direction: column;
      align-items: center;
      margin: 1rem auto 0;
      max-width: 720px;
    }

    .pipeline-svg {
      width: 100%;
      max-width: 620px;
    }

    .pipeline-svg .node-rect {
      fill: var(--bg-elevated);
      stroke: var(--border-strong);
      stroke-width: 1.25;
    }

    .pipeline-svg .node-rect--verdict {
      stroke: var(--accent);
      stroke-width: 1.75;
      fill: var(--accent-subtle-bg);
    }

    .pipeline-svg .arrow {
      stroke: var(--text-tertiary);
      stroke-width: 1.25;
    }

    .pipeline-svg .arrow--branch {
      stroke-dasharray: 4 3;
    }

    .pipeline-svg .arrowhead {
      fill: var(--text-tertiary);
    }

    .pipeline-svg .node-title {
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.08em;
      fill: var(--text-primary);
    }

    .pipeline-svg .node-title--verdict {
      fill: var(--accent);
    }

    .pipeline-svg .node-sub {
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 10px;
      letter-spacing: 0.02em;
      fill: var(--text-secondary);
    }

    .pipeline-svg .branch-label {
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 10px;
      fill: var(--text-tertiary);
      font-style: italic;
    }

    .pipeline-figure figcaption {
      margin-top: 1rem;
      max-width: 620px;
      text-align: center;
    }

    /* ===== TRAINING PARAMETERS LIST ===== */
    .train-list {
      display: flex;
      flex-direction: column;
      gap: 0;
      max-width: 720px;
      margin-top: 0.5rem;
      margin-bottom: 1.5rem;
    }

    .train-row {
      display: grid;
      grid-template-columns: 220px 1fr;
      gap: 1rem;
      padding: 0.85rem 0;
      border-top: 1px solid var(--border-color);
    }

    .train-row:first-child {
      border-top: none;
      padding-top: 0;
    }

    .train-row dt {
      font-family: var(--font-sans);
      font-size: 0.82rem;
      font-weight: 600;
      color: var(--text-primary);
      line-height: 1.5;
    }

    .train-row dd {
      margin: 0;
      font-family: var(--font-sans);
      font-size: 0.875rem;
      color: var(--text-secondary);
      line-height: 1.55;
    }

    .train-note {
      font-family: var(--font-sans);
      font-size: 0.85rem;
      color: var(--text-tertiary);
      margin: 0;
    }

    /* ===== PAPER TABLE ===== */
    .paper-table {
      width: 100%;
      max-width: 640px;
      border-collapse: collapse;
      font-family: var(--font-sans);
      font-size: 0.875rem;
      margin-top: 1.25rem;
      font-variant-numeric: tabular-nums;
    }

    .paper-table thead th {
      text-align: left;
      font-size: 0.72rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--text-tertiary);
      padding: 0 1.25rem 0.75rem 0;
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
      padding: 0.85rem 1.25rem 0.85rem 0;
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
    }

    .table-note {
      font-family: var(--font-sans);
      font-size: 0.8rem;
      color: var(--text-tertiary);
      margin-top: 0.75rem;
      margin-bottom: 0;
      font-style: italic;
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

    .ressources-tags {
      font-family: var(--font-sans);
      font-size: 0.8rem;
      color: var(--text-tertiary);
      line-height: 1.6;
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

      .train-row {
        grid-template-columns: 1fr;
        gap: 0.25rem;
      }

      .train-row dt {
        font-size: 0.8rem;
        color: var(--text-tertiary);
        font-weight: 600;
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
export class MethodologyComponent {}
