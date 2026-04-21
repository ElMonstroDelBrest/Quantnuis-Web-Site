import { Injectable } from '@angular/core';
import { Observable, catchError, of } from 'rxjs';
import { LambdaApi } from './lambda.api';

export interface AnalysisResult {
  hasNoisyVehicle: boolean;
  carDetected: boolean;
  confidence: number;
  message: string;
}

@Injectable({ providedIn: 'root' })
export class AudioAnalysisApi extends LambdaApi {

  analyzeFile(file: File): Observable<AnalysisResult> {
    const formData = new FormData();
    formData.append('file', file);

    return this.http.post<AnalysisResult>(`${this.baseUrl}/predict`, formData).pipe(
      catchError(() => of({
        hasNoisyVehicle: false,
        carDetected: false,
        confidence: 0,
        message: "Erreur de connexion au serveur d'analyse."
      }))
    );
  }
}
