import { HttpInterceptorFn, HttpErrorResponse, HttpRequest, HttpHandlerFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError, timer, retry } from 'rxjs';
import { NotificationService } from './services/notification.service';
import { TokenStorage } from './services/token.storage';
import { SKIP_ERROR_RETRY } from './services/warmup.service';

// Configuration du retry
const RETRY_CONFIG = {
  maxRetries: 3,
  initialDelay: 1000, // 1 seconde
  maxDelay: 4000,     // 4 secondes max
  retryableStatuses: [0, 408, 500, 502, 503, 504] // Network error, timeout, server errors
};

// Vérifie si l'erreur est retryable
function isRetryable(error: HttpErrorResponse): boolean {
  // Ne pas retry les requêtes POST/PUT/DELETE (sauf si idempotent)
  // Pour l'instant, on ne retry que les erreurs réseau et serveur
  return RETRY_CONFIG.retryableStatuses.includes(error.status);
}

// Calcule le délai avec exponential backoff
function getRetryDelay(retryCount: number): number {
  const delay = RETRY_CONFIG.initialDelay * Math.pow(2, retryCount);
  return Math.min(delay, RETRY_CONFIG.maxDelay);
}

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const router = inject(Router);
  const notificationService = inject(NotificationService);
  const tokenStorage = inject(TokenStorage);
  const skipRetry = req.context.get(SKIP_ERROR_RETRY);

  return next(req).pipe(
    retry({
      count: skipRetry ? 0 : RETRY_CONFIG.maxRetries,
      delay: (error: HttpErrorResponse, retryCount: number) => {
        if (!isRetryable(error)) {
          return throwError(() => error);
        }
        const delay = getRetryDelay(retryCount - 1);
        console.log(`Retry ${retryCount}/${RETRY_CONFIG.maxRetries} après ${delay}ms...`);
        return timer(delay);
      }
    }),
    catchError((error: HttpErrorResponse) => {
      let errorMessage = 'Une erreur est survenue';

      // Ne pas traiter les erreurs de requêtes annulées
      if (error.status === 0 && error.error instanceof ProgressEvent) {
        errorMessage = 'Impossible de contacter le serveur. Vérifiez votre connexion.';
        notificationService.error('Erreur de connexion', errorMessage);
        return throwError(() => error);
      }

      switch (error.status) {
        case 400:
          errorMessage = extractErrorMessage(error) || 'Requête invalide';
          notificationService.error('Erreur', errorMessage);
          break;

        case 401:
          // Token expiré ou invalide
          const currentUrl = router.url;
          if (!currentUrl.includes('/login') && !currentUrl.includes('/register')) {
            notificationService.warning(
              'Session expirée',
              'Veuillez vous reconnecter.',
              {
                label: 'Connexion',
                callback: () => router.navigate(['/login'])
              }
            );
            tokenStorage.clear();
            router.navigate(['/login']);
          }
          break;

        case 403:
          errorMessage = 'Accès non autorisé';
          notificationService.error('Accès refusé', errorMessage);
          break;

        case 404:
          // 404 are silently handled by the calling service
          break;

        case 409:
          errorMessage = extractErrorMessage(error) || 'Conflit de données';
          notificationService.error('Conflit', errorMessage);
          break;

        case 422:
          errorMessage = extractErrorMessage(error) || 'Données invalides';
          notificationService.error('Validation', errorMessage);
          break;

        case 429:
          errorMessage = 'Trop de requêtes. Veuillez patienter.';
          notificationService.warning('Limite atteinte', errorMessage);
          break;

        case 500:
          errorMessage = 'Erreur serveur. Veuillez réessayer plus tard.';
          notificationService.error('Erreur serveur', errorMessage);
          break;

        case 502:
        case 503:
        case 504:
          errorMessage = 'Service temporairement indisponible.';
          notificationService.warning('Service indisponible', errorMessage, {
            label: 'Réessayer',
            callback: () => window.location.reload()
          });
          break;

        default:
          if (error.status >= 500) {
            errorMessage = 'Erreur serveur inattendue';
          } else if (error.status >= 400) {
            errorMessage = extractErrorMessage(error) || 'Erreur de requête';
          }
          notificationService.error('Erreur', errorMessage);
      }

      return throwError(() => error);
    })
  );
};

function extractErrorMessage(error: HttpErrorResponse): string | null {
  if (error.error) {
    // FastAPI error format
    if (typeof error.error.detail === 'string') {
      return error.error.detail;
    }
    // FastAPI validation errors
    if (Array.isArray(error.error.detail)) {
      return error.error.detail.map((e: any) => e.msg || e.message).join('. ');
    }
    // Generic message field
    if (error.error.message) {
      return error.error.message;
    }
    // Error as string
    if (typeof error.error === 'string') {
      return error.error;
    }
  }
  return null;
}
