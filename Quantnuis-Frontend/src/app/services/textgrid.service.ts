import { Injectable } from '@angular/core';

// ============================================================================
// INTERFACES
// ============================================================================

export interface TextGridInterval {
  xmin: number;
  xmax: number;
  text: string;
}

export interface TextGridTier {
  name: string;
  type: 'IntervalTier' | 'TextTier';
  xmin: number;
  xmax: number;
  intervals: TextGridInterval[];
}

export interface TextGrid {
  xmin: number;
  xmax: number;
  tiers: TextGridTier[];
}

export interface AnnotationWithTier {
  id: number;
  startTime: number;
  endTime: number;
  label: string;
  tier: string;
  aiModel?: 'car_detector' | 'noisy_car_detector';
  note?: string;
  confidence?: number;
}

// ============================================================================
// SERVICE
// ============================================================================

@Injectable({
  providedIn: 'root'
})
export class TextGridService {

  // Default tier configuration for Quantnuis
  readonly defaultTiers = [
    { name: 'Evenement', description: 'Type d\'evenement (vehicule, bruit, silence)' },
    { name: 'Intensite', description: 'Niveau sonore (fort, moyen, faible)' },
    { name: 'Confiance', description: 'Niveau de confiance (0-100%)' },
    { name: 'Notes', description: 'Commentaires libres' }
  ];

  // Controlled vocabulary for each tier
  readonly vocabularies: Record<string, string[]> = {
    'Evenement': ['vehicule', 'vehicule_bruyant', 'silence', 'bruit_ambiant', 'klaxon', 'freinage', 'acceleration'],
    'Intensite': ['fort', 'moyen', 'faible', 'tres_fort', 'imperceptible'],
    'Confiance': ['100', '90', '80', '70', '60', '50', 'incertain']
  };

  constructor() {}

  // ============================================================================
  // TEXTGRID EXPORT
  // ============================================================================

  /**
   * Export annotations to Praat TextGrid format
   */
  exportToTextGrid(
    annotations: AnnotationWithTier[],
    duration: number,
    tierNames?: string[]
  ): string {
    const tiers = tierNames || this.extractTierNames(annotations);
    const textGrid = this.buildTextGrid(annotations, duration, tiers);
    return this.serializeTextGrid(textGrid);
  }

  /**
   * Build TextGrid structure from annotations
   */
  private buildTextGrid(
    annotations: AnnotationWithTier[],
    duration: number,
    tierNames: string[]
  ): TextGrid {
    const tiers: TextGridTier[] = tierNames.map(tierName => {
      const tierAnnotations = annotations.filter(a => a.tier === tierName);
      const intervals = this.buildIntervals(tierAnnotations, duration);

      return {
        name: tierName,
        type: 'IntervalTier',
        xmin: 0,
        xmax: duration,
        intervals
      };
    });

    return {
      xmin: 0,
      xmax: duration,
      tiers
    };
  }

  /**
   * Build intervals for a tier, filling gaps with empty intervals
   */
  private buildIntervals(annotations: AnnotationWithTier[], duration: number): TextGridInterval[] {
    const sorted = [...annotations].sort((a, b) => a.startTime - b.startTime);
    const intervals: TextGridInterval[] = [];
    let currentTime = 0;

    for (const ann of sorted) {
      // Add empty interval if there's a gap
      if (ann.startTime > currentTime + 0.001) {
        intervals.push({
          xmin: currentTime,
          xmax: ann.startTime,
          text: ''
        });
      }

      // Add annotation interval
      intervals.push({
        xmin: ann.startTime,
        xmax: ann.endTime,
        text: ann.label
      });

      currentTime = ann.endTime;
    }

    // Add final empty interval if needed
    if (currentTime < duration - 0.001) {
      intervals.push({
        xmin: currentTime,
        xmax: duration,
        text: ''
      });
    }

    return intervals;
  }

  /**
   * Serialize TextGrid to Praat format string
   */
  private serializeTextGrid(textGrid: TextGrid): string {
    let output = 'File type = "ooTextFile"\n';
    output += 'Object class = "TextGrid"\n\n';
    output += `xmin = ${textGrid.xmin}\n`;
    output += `xmax = ${textGrid.xmax}\n`;
    output += 'tiers? <exists>\n';
    output += `size = ${textGrid.tiers.length}\n`;
    output += 'item []:\n';

    textGrid.tiers.forEach((tier, index) => {
      output += `    item [${index + 1}]:\n`;
      output += `        class = "${tier.type}"\n`;
      output += `        name = "${tier.name}"\n`;
      output += `        xmin = ${tier.xmin}\n`;
      output += `        xmax = ${tier.xmax}\n`;
      output += `        intervals: size = ${tier.intervals.length}\n`;

      tier.intervals.forEach((interval, iIndex) => {
        output += `        intervals [${iIndex + 1}]:\n`;
        output += `            xmin = ${interval.xmin}\n`;
        output += `            xmax = ${interval.xmax}\n`;
        output += `            text = "${this.escapeTextGridString(interval.text)}"\n`;
      });
    });

    return output;
  }

  /**
   * Escape special characters for TextGrid format
   */
  private escapeTextGridString(text: string): string {
    return text
      .replace(/\\/g, '\\\\')
      .replace(/"/g, '\\"')
      .replace(/\n/g, '\\n');
  }

  // ============================================================================
  // TEXTGRID IMPORT
  // ============================================================================

  /**
   * Parse Praat TextGrid format
   */
  parseTextGrid(content: string): TextGrid {
    const lines = content.split('\n').map(l => l.trim());
    let lineIndex = 0;

    // Skip header
    while (lineIndex < lines.length && !lines[lineIndex].startsWith('xmin')) {
      lineIndex++;
    }

    // Parse global xmin/xmax
    const xmin = this.parseNumberLine(lines[lineIndex++]);
    const xmax = this.parseNumberLine(lines[lineIndex++]);

    // Skip to tiers
    while (lineIndex < lines.length && !lines[lineIndex].startsWith('size')) {
      lineIndex++;
    }
    const tierCount = this.parseNumberLine(lines[lineIndex++]);

    // Skip "item []:"
    while (lineIndex < lines.length && !lines[lineIndex].includes('item [')) {
      lineIndex++;
    }

    const tiers: TextGridTier[] = [];

    for (let t = 0; t < tierCount; t++) {
      // Find next "item ["
      while (lineIndex < lines.length && !lines[lineIndex].includes('item [')) {
        lineIndex++;
      }
      lineIndex++;

      // Parse tier
      const tier = this.parseTier(lines, lineIndex);
      tiers.push(tier.tier);
      lineIndex = tier.nextIndex;
    }

    return { xmin, xmax, tiers };
  }

  /**
   * Parse a single tier
   */
  private parseTier(lines: string[], startIndex: number): { tier: TextGridTier; nextIndex: number } {
    let lineIndex = startIndex;

    // Parse tier properties
    const tierClass = this.parseStringLine(lines[lineIndex++]) as 'IntervalTier' | 'TextTier';
    const tierName = this.parseStringLine(lines[lineIndex++]);
    const tierXmin = this.parseNumberLine(lines[lineIndex++]);
    const tierXmax = this.parseNumberLine(lines[lineIndex++]);

    // Find intervals count
    while (lineIndex < lines.length && !lines[lineIndex].includes('size')) {
      lineIndex++;
    }
    const intervalCount = this.parseNumberLine(lines[lineIndex++]);

    const intervals: TextGridInterval[] = [];

    for (let i = 0; i < intervalCount; i++) {
      // Find next "intervals ["
      while (lineIndex < lines.length && !lines[lineIndex].includes('intervals [')) {
        lineIndex++;
      }
      lineIndex++;

      // Parse interval
      const xmin = this.parseNumberLine(lines[lineIndex++]);
      const xmax = this.parseNumberLine(lines[lineIndex++]);
      const text = this.parseStringLine(lines[lineIndex++]);

      intervals.push({ xmin, xmax, text });
    }

    return {
      tier: {
        name: tierName,
        type: tierClass,
        xmin: tierXmin,
        xmax: tierXmax,
        intervals
      },
      nextIndex: lineIndex
    };
  }

  /**
   * Parse a number from a line like "xmin = 0.123"
   */
  private parseNumberLine(line: string): number {
    const match = line.match(/=\s*([0-9.-]+)/);
    return match ? parseFloat(match[1]) : 0;
  }

  /**
   * Parse a string from a line like 'name = "tier1"'
   */
  private parseStringLine(line: string): string {
    const match = line.match(/=\s*"([^"]*)"/);
    if (match) {
      return this.unescapeTextGridString(match[1]);
    }
    return '';
  }

  /**
   * Unescape TextGrid string
   */
  private unescapeTextGridString(text: string): string {
    return text
      .replace(/\\n/g, '\n')
      .replace(/\\"/g, '"')
      .replace(/\\\\/g, '\\');
  }

  /**
   * Convert TextGrid to Quantnuis annotations
   */
  textGridToAnnotations(textGrid: TextGrid): AnnotationWithTier[] {
    const annotations: AnnotationWithTier[] = [];
    let id = Date.now();

    for (const tier of textGrid.tiers) {
      for (const interval of tier.intervals) {
        // Skip empty intervals
        if (!interval.text || interval.text.trim() === '') continue;

        annotations.push({
          id: id++,
          startTime: interval.xmin,
          endTime: interval.xmax,
          label: interval.text,
          tier: tier.name
        });
      }
    }

    return annotations;
  }

  // ============================================================================
  // UTILITY METHODS
  // ============================================================================

  /**
   * Extract unique tier names from annotations
   */
  extractTierNames(annotations: AnnotationWithTier[]): string[] {
    const tierSet = new Set(annotations.map(a => a.tier || 'Evenement'));
    return Array.from(tierSet);
  }

  /**
   * Convert simple annotations to multi-tier format
   */
  convertToMultiTier(
    annotations: Array<{
      id: number;
      startTime: number;
      endTime: number;
      label: string;
      aiModel: 'car_detector' | 'noisy_car_detector';
      note?: string;
      qualityScore?: number;
    }>
  ): AnnotationWithTier[] {
    const result: AnnotationWithTier[] = [];

    for (const ann of annotations) {
      // Main event tier
      result.push({
        id: ann.id,
        startTime: ann.startTime,
        endTime: ann.endTime,
        label: this.mapLabelToVocabulary(ann.label),
        tier: 'Evenement',
        aiModel: ann.aiModel,
        note: ann.note
      });

      // Confidence tier (if available)
      if (ann.qualityScore !== undefined) {
        result.push({
          id: ann.id + 0.1,
          startTime: ann.startTime,
          endTime: ann.endTime,
          label: String(Math.round(ann.qualityScore)),
          tier: 'Confiance'
        });
      }

      // Notes tier (if available)
      if (ann.note && ann.note.trim()) {
        result.push({
          id: ann.id + 0.2,
          startTime: ann.startTime,
          endTime: ann.endTime,
          label: ann.note,
          tier: 'Notes'
        });
      }
    }

    return result;
  }

  /**
   * Map Quantnuis labels to controlled vocabulary
   */
  private mapLabelToVocabulary(label: string): string {
    const mapping: Record<string, string> = {
      'car': 'vehicule',
      'noisy_car': 'vehicule_bruyant',
      'noise': 'bruit_ambiant',
      'other': 'autre'
    };
    return mapping[label] || label;
  }

  /**
   * Get vocabulary suggestions for a tier
   */
  getVocabularySuggestions(tier: string, partial: string): string[] {
    const vocab = this.vocabularies[tier] || [];
    if (!partial) return vocab.slice(0, 10);

    const lower = partial.toLowerCase();
    return vocab
      .filter(v => v.toLowerCase().includes(lower))
      .slice(0, 10);
  }

  /**
   * Validate label against controlled vocabulary
   */
  isValidLabel(tier: string, label: string): boolean {
    const vocab = this.vocabularies[tier];
    if (!vocab) return true; // No vocabulary = any label allowed
    return vocab.includes(label.toLowerCase());
  }

  // ============================================================================
  // FILE DOWNLOAD HELPERS
  // ============================================================================

  /**
   * Download TextGrid file
   */
  downloadTextGrid(content: string, filename: string): void {
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename.endsWith('.TextGrid') ? filename : `${filename}.TextGrid`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  /**
   * Read TextGrid file from File object
   */
  async readTextGridFile(file: File): Promise<TextGrid> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        try {
          const content = reader.result as string;
          const textGrid = this.parseTextGrid(content);
          resolve(textGrid);
        } catch (error) {
          reject(new Error('Invalid TextGrid file format'));
        }
      };
      reader.onerror = () => reject(reader.error);
      reader.readAsText(file);
    });
  }
}
