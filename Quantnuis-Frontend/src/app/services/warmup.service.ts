import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpContext, HttpContextToken } from '@angular/common/http';
import { catchError, of, timeout } from 'rxjs';
import { environment } from '../../environments/environment';

// HttpContext token reconnu par l'error.interceptor pour désactiver le retry
export const SKIP_ERROR_RETRY = new HttpContextToken<boolean>(() => false);

@Injectable({ providedIn: 'root' })
export class WarmupService {
  private http = inject(HttpClient);
  private warmed = false;

  warmLambda(): void {
    if (this.warmed) return;
    this.warmed = true;

    // En dev, inutile de pinger : lambdaUrl pointe sur localhost et
    // déclenche du bruit CSP sans intérêt.
    if (!environment.production) return;

    this.http.get(`${environment.lambdaUrl}/health`, {
      context: new HttpContext().set(SKIP_ERROR_RETRY, true)
    })
      .pipe(
        timeout(30000),
        catchError(() => of(null))
      )
      .subscribe();
  }
}
