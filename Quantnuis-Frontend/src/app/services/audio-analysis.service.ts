import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { AudioAnalysisApi, AnalysisResult } from './api/audio-analysis.api';

export type { AnalysisResult } from './api/audio-analysis.api';

@Injectable({ providedIn: 'root' })
export class AudioAnalysisService {

  constructor(private audioAnalysisApi: AudioAnalysisApi) {}

  analyzeFile(file: File): Observable<AnalysisResult> {
    return this.audioAnalysisApi.analyzeFile(file);
  }
}
