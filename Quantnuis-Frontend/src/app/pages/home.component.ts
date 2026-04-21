import { Component, ChangeDetectorRef, NgZone, ViewChild, ElementRef, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AudioAnalysisService, AnalysisResult } from '../services/audio-analysis.service';
import { SoundService } from '../services/sound.service';
import { HomeHeroComponent } from './home/home-hero.component';
import { HomeUploadComponent } from './home/home-upload.component';
import { HomePickerComponent } from './home/home-picker.component';
import { HomePipelineComponent, PipelineStep } from './home/home-pipeline.component';
import { HomeResultComponent } from './home/home-result.component';

type PickerMode = 'picker' | 'upload';

const CITATION_TEXT = `@misc{quantnuis2026,
  author      = {Boué, Nathan and Gherasim, Daniel and Mourtada, Nour and Perdigues, Owen and Cazau, Dorian},
  title       = {Quantnuis: Classification audio en cascade pour la détection de véhicules bruyants},
  year        = {2026},
  institution = {ENSTA Bretagne},
  url         = {https://github.com/ElMonstroDelBrest/Quantnuis-Web-Site}
}`;

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, HomeHeroComponent, HomeUploadComponent, HomePickerComponent, HomePipelineComponent, HomeResultComponent],
  template: `
    <div class="home-page">

      <!-- Hero -->
      <app-home-hero (ctaClicked)="scrollToAnalyzer()"></app-home-hero>

      <!-- §1 — Résumé -->
      <section class="paper-section" aria-labelledby="resume-heading">
        <div class="paper-section-inner">
          <span class="section-label">§1 · Résumé</span>
          <h2 id="resume-heading">
            Un pipeline à deux étages pour mesurer le bruit des véhicules en ville.
          </h2>
          <p class="editorial-prose">
            L'exposition continue au bruit routier constitue un problème de santé publique.
            Le décret n° 2022-125 fixe un seuil de 85 dB à deux mètres pour les véhicules en
            circulation, mais les mesures restent ponctuelles et manuelles. Quantnuis automatise
            la détection à partir d'audio urbain via deux réseaux de neurones : un premier modèle
            isole les extraits contenant un véhicule, un second estime si le niveau sonore dépasse
            le seuil réglementaire.
          </p>
        </div>
      </section>

      <!-- §2 — Démonstration -->
      <section class="paper-section" id="demonstration" aria-labelledby="demo-heading">
        <div class="paper-section-inner">
          <span class="section-label">§2 · Démonstration</span>
          <h2 id="demo-heading">Analysez un extrait distribué sur place.</h2>
          <p class="demo-lede">
            Chaque extrait ci-dessous a été enregistré dans des conditions urbaines réelles.
            Sélectionnez-en un pour l'écouter, puis lancez l'analyse pour visualiser la décision.
          </p>

          <div #analyzerAnchor class="analyzer-content">
            <!-- Selection d'audio (picker) -->
            <app-home-picker
              *ngIf="!isAnalyzing && !result && mode === 'picker'"
              (fileSelected)="onFileSelected($event)"
              (analyzeClicked)="analyze()"
              (uploadRequested)="switchToUpload()"
            ></app-home-picker>

            <!-- Upload libre (fallback) -->
            <ng-container *ngIf="!isAnalyzing && !result && mode === 'upload'">
              <button class="back-to-picker" (click)="switchToPicker()" type="button" aria-label="Revenir à la liste d'extraits">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>
                </svg>
                <span>Revenir aux extraits proposés</span>
              </button>
              <app-home-upload
                (fileSelected)="onFileSelected($event)"
                (analyzeClicked)="analyze()"
                (demoClicked)="switchToPicker()"
                (fileRemoved)="reset()"
              ></app-home-upload>
            </ng-container>

            <!-- Pipeline + Result -->
            <ng-container *ngIf="isAnalyzing || result">
              <app-home-pipeline
                [steps]="pipelineSteps"
                [isAnalyzing]="isAnalyzing"
                [fileName]="selectedFile?.name || ''"
                [audioFile]="selectedFile || undefined"
              ></app-home-pipeline>

              <app-home-result
                [result]="result"
                (resetClicked)="reset()"
              ></app-home-result>
            </ng-container>
          </div>
        </div>
      </section>

      <!-- §3 — Contexte & approche -->
      <section class="paper-section context-section" aria-labelledby="context-heading">
        <div class="paper-section-inner">
          <span class="section-label">§3 · Contexte &amp; approche</span>

          <div class="context-inner">
            <div class="context-block">
              <h2 id="context-heading">Le bruit des véhicules est une nuisance mesurable, mal contrôlée.</h2>
              <p class="editorial-prose">
                Le décret n° 2022-125 impose un seuil de 85 dB à deux mètres pour les véhicules
                en circulation. Les mesures ponctuelles effectuées par les agents restent rares
                et manuelles. Quantnuis automatise la détection à partir d'enregistrements audio
                pour rendre possible une surveillance continue et objective.
              </p>
            </div>

            <div class="context-block">
              <h2>Deux modèles en cascade, entraînés sur des données terrain.</h2>
              <p class="editorial-prose">
                Le premier réseau de neurones isole les extraits contenant un véhicule. Le second
                estime si son niveau sonore dépasse le seuil réglementaire. Cette architecture
                évite les faux positifs sur du bruit urbain ambiant et permet d'interpréter
                chaque décision indépendamment.
              </p>
            </div>
          </div>
        </div>
      </section>

      <!-- §4 — Mesures -->
      <section class="paper-section" aria-labelledby="stats-heading">
        <div class="paper-section-inner">
          <span class="section-label">§4 · Mesures</span>
          <h2 id="stats-heading">Chiffres clés.</h2>

          <dl class="context-stats" aria-label="Chiffres clés">
            <div class="stat">
              <dt>Dataset d'entraînement</dt>
              <dd>12 h<span class="stat-unit">d'audio urbain annoté</span></dd>
            </div>
            <div class="stat">
              <dt>Features extraites</dt>
              <dd>180<span class="stat-unit">→ 40 optimisées</span></dd>
            </div>
            <div class="stat">
              <dt>Précision validation</dt>
              <dd>94 %<span class="stat-unit">sur jeu de test</span></dd>
            </div>
            <div class="stat">
              <dt>Latence d'inférence</dt>
              <dd>≈ 3 s<span class="stat-unit">AWS Lambda</span></dd>
            </div>
          </dl>
        </div>
      </section>

      <!-- §5 — Citation -->
      <section class="paper-section" aria-labelledby="citation-heading">
        <div class="paper-section-inner">
          <span class="section-label">§5 · Citation</span>
          <h2 id="citation-heading">Référencer ce projet.</h2>

          <div class="citation-block">
            <div class="citation-toolbar" aria-label="Actions citation">
              <button
                type="button"
                class="btn-copy"
                (click)="copyCitation()"
                [attr.aria-label]="copied ? 'Copié !' : 'Copier la référence BibTeX'"
              >
                <svg *ngIf="!copied" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true" width="13" height="13">
                  <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                </svg>
                <svg *ngIf="copied" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true" width="13" height="13">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
                <span>{{ copied ? 'Copié !' : 'Copier' }}</span>
              </button>
            </div>
            <pre class="citation-code" aria-label="Référence BibTeX">{{ citationText }}</pre>
          </div>
        </div>
      </section>

    </div>
  `,
  styles: [`
    .home-page { min-height: calc(100vh - 64px); }

    /* ===== PAPER SECTIONS ===== */
    .paper-section {
      border-top: 1px solid var(--border-color);
      position: relative;
    }
    /* Alternate subtle tint for visual rhythm (research paper feel) */
    .paper-section:nth-of-type(even) {
      background: var(--overlay-weak);
    }
    /* Section numbering ornament on the left gutter, visible on wide screens */
    @media (min-width: 980px) {
      .paper-section-inner {
        position: relative;
      }
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
      font-family: 'Newsreader', 'Charter', 'Georgia', serif;
      font-size: clamp(1.25rem, 1.8vw + 0.7rem, 1.65rem);
      font-weight: 600;
      letter-spacing: -0.015em;
      color: var(--text-primary);
      margin-bottom: 1.25rem;
      line-height: 1.25;
      max-width: 680px;
    }

    .editorial-prose {
      font-family: 'Newsreader', 'Charter', 'Georgia', serif;
      font-size: 1.05rem;
      line-height: 1.7;
      color: var(--text-secondary);
      max-width: 680px;
      margin-bottom: 0;
    }

    .demo-lede {
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 0.975rem;
      color: var(--text-secondary);
      line-height: 1.6;
      max-width: 680px;
      margin-bottom: 2rem;
    }

    /* ===== ANALYZER BLOCK ===== */
    .analyzer-content {
      scroll-margin-top: 80px;
    }

    .back-to-picker {
      display: inline-flex; align-items: center; gap: 0.5rem;
      background: none; border: none;
      color: var(--text-secondary); font-size: 0.85rem;
      cursor: pointer; padding: 0.375rem 0.5rem;
      margin-bottom: 1rem;
      border-radius: var(--radius-sm);
      font-family: 'Inter', system-ui, sans-serif;
    }
    .back-to-picker svg { width: 15px; height: 15px; }
    .back-to-picker:hover { color: var(--accent); }
    .back-to-picker:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

    /* ===== CONTEXT SECTION ===== */
    .context-inner {
      display: grid;
      grid-template-columns: 1fr;
      gap: 3rem;
    }

    .context-block h2 {
      max-width: 560px;
    }

    /* ===== STATS ===== */
    .context-stats {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 0;
      margin: 0;
      padding-top: 2rem;
      border-top: 1px solid var(--border-color);
    }

    .stat {
      padding: 0 1.25rem;
      border-left: 1px solid var(--border-color);
    }
    .stat:first-child { padding-left: 0; border-left: none; }

    .stat dt {
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 0.7rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--text-tertiary);
      margin-bottom: 0.4rem;
    }

    .stat dd {
      margin: 0;
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 1.4rem;
      font-weight: 700;
      color: var(--text-primary);
      letter-spacing: -0.02em;
      font-variant-numeric: tabular-nums;
      display: flex;
      align-items: baseline;
      gap: 0.5rem;
      flex-wrap: wrap;
    }

    .stat-unit {
      font-size: 0.72rem;
      font-weight: 500;
      color: var(--text-tertiary);
      letter-spacing: 0;
    }

    /* ===== CITATION BLOCK ===== */
    .citation-block {
      position: relative;
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      overflow: hidden;
      max-width: 680px;
    }

    .citation-toolbar {
      display: flex;
      justify-content: flex-end;
      padding: 0.5rem 0.75rem;
      border-bottom: 1px solid var(--border-color);
      background: var(--overlay-weak);
    }

    .btn-copy {
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      padding: 0.3rem 0.65rem;
      background: transparent;
      border: 1px solid var(--border-color-hover);
      border-radius: var(--radius-sm);
      color: var(--text-secondary);
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 0.75rem;
      font-weight: 500;
      cursor: pointer;
      transition: color 0.15s ease, border-color 0.15s ease, background 0.15s ease;
    }
    .btn-copy:hover { color: var(--text-primary); border-color: var(--border-strong); background: var(--bg-surface-hover); }

    .citation-code {
      font-family: ui-monospace, 'Cascadia Code', 'Source Code Pro', Menlo, Monaco, 'Courier New', monospace;
      font-size: 0.82rem;
      line-height: 1.7;
      color: var(--text-secondary);
      padding: 1.25rem 1.5rem;
      margin: 0;
      overflow-x: auto;
      white-space: pre;
    }

    /* ===== RESPONSIVE ===== */
    @media (min-width: 768px) {
      .context-inner {
        grid-template-columns: 1fr 1fr;
        gap: 3.5rem;
      }
    }

    @media (max-width: 768px) {
      .paper-section-inner { padding: 2.5rem 1.25rem; }
      .context-stats {
        grid-template-columns: 1fr 1fr;
        gap: 1.25rem 0;
      }
      .stat {
        padding: 0 1rem;
        border-left: 1px solid var(--border-color);
      }
      .stat:nth-child(odd) { padding-left: 0; border-left: none; }
    }

    @media (max-width: 480px) {
      .paper-section-inner { padding: 2rem 1rem; }
      .context-stats {
        grid-template-columns: 1fr;
        gap: 1.25rem;
      }
      .stat {
        padding: 0;
        border-left: none;
        border-top: 1px solid var(--border-color);
        padding-top: 1rem;
      }
      .stat:first-child { border-top: none; padding-top: 0; }
    }
  `]
})
export class HomeComponent implements AfterViewInit {
  @ViewChild('analyzerAnchor') analyzerAnchor?: ElementRef<HTMLDivElement>;

  selectedFile: File | null = null;
  isAnalyzing = false;
  result: AnalysisResult | null = null;
  mode: PickerMode = 'picker';
  copied = false;
  citationText = CITATION_TEXT;

  pipelineSteps: PipelineStep[] = [
    { id: 'upload', label: 'Reception du fichier audio', icon: '', status: 'waiting' },
    { id: 'extract', label: 'Calcul du spectrogramme mel', icon: '', status: 'waiting' },
    { id: 'car', label: 'Detection de vehicule (IA #1)', icon: '', status: 'waiting' },
    { id: 'noise', label: 'Analyse du niveau sonore (IA #2)', icon: '', status: 'waiting' },
    { id: 'result', label: 'Classification finale', icon: '', status: 'waiting' }
  ];

  constructor(
    private audioService: AudioAnalysisService,
    private cdr: ChangeDetectorRef,
    private ngZone: NgZone,
    private soundService: SoundService
  ) {}

  ngAfterViewInit() {}

  switchToUpload() { this.mode = 'upload'; }

  switchToPicker() {
    this.mode = 'picker';
    this.selectedFile = null;
  }

  scrollToAnalyzer() {
    this.analyzerAnchor?.nativeElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  onFileSelected(file: File) { this.selectedFile = file; }

  analyze() {
    if (!this.selectedFile) return;

    this.soundService.playStart();
    this.isAnalyzing = true;
    this.result = null;
    this.resetPipeline();
    this.simulatePipeline();

    this.audioService.analyzeFile(this.selectedFile).subscribe({
      next: (res) => {
        this.ngZone.run(() => {
          this.completePipeline(res);
          this.result = res;
          this.isAnalyzing = false;
          if (!res.hasNoisyVehicle) {
            this.soundService.playFanfare();
          } else {
            this.soundService.playAlert();
          }
          this.cdr.detectChanges();
        });
      },
      error: () => {
        this.ngZone.run(() => {
          this.pipelineSteps.forEach(s => {
            if (s.status === 'processing') s.status = 'error';
          });
          this.pipelineSteps = [...this.pipelineSteps];
          this.isAnalyzing = false;
          this.cdr.detectChanges();
        });
      }
    });
  }

  reset() {
    this.selectedFile = null;
    this.result = null;
    this.isAnalyzing = false;
    this.resetPipeline();
  }

  copyCitation() {
    navigator.clipboard.writeText(CITATION_TEXT).then(() => {
      this.copied = true;
      this.cdr.detectChanges();
      setTimeout(() => {
        this.copied = false;
        this.cdr.detectChanges();
      }, 2000);
    }).catch(() => {
      // Fallback: ignore silently if clipboard not available
    });
  }

  private resetPipeline() {
    this.pipelineSteps.forEach(step => { step.status = 'waiting'; step.result = undefined; });
    this.pipelineSteps = [...this.pipelineSteps];
  }

  private simulatePipeline() {
    const delays = [0, 300, 800, 1500, 2200];
    this.pipelineSteps.forEach((step, index) => {
      setTimeout(() => {
        if (this.isAnalyzing) {
          if (index > 0) { this.pipelineSteps[index - 1].status = 'completed'; this.soundService.playStepComplete(); }
          step.status = 'processing';
          this.pipelineSteps = [...this.pipelineSteps];
          this.soundService.playTick();
          this.cdr.detectChanges();
        }
      }, delays[index]);
    });
  }

  private completePipeline(res: AnalysisResult) {
    this.pipelineSteps[0].status = 'completed';
    this.pipelineSteps[0].result = this.selectedFile?.name;
    this.pipelineSteps[1].status = 'completed';
    this.pipelineSteps[1].result = 'Spectrogramme mel extrait';
    this.pipelineSteps[2].status = 'completed';
    this.pipelineSteps[2].result = res.carDetected ? 'Vehicule detecte' : 'Aucun vehicule';
    this.pipelineSteps[3].status = 'completed';
    this.pipelineSteps[3].result = 'Niveau sonore classe';
    this.pipelineSteps[4].status = 'completed';
    this.pipelineSteps[4].result = res.hasNoisyVehicle ? 'BRUYANT' : 'CONFORME';
    this.pipelineSteps = [...this.pipelineSteps];
  }
}
