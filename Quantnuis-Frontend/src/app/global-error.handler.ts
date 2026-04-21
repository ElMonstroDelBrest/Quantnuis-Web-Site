import { ErrorHandler, Injectable, NgZone, inject } from '@angular/core';
import { NotificationService } from './services/notification.service';

@Injectable()
export class GlobalErrorHandler implements ErrorHandler {
  private notificationService = inject(NotificationService);
  private ngZone = inject(NgZone);

  handleError(error: any): void {
    // Log l'erreur dans la console pour le debug
    console.error('Global Error:', error);

    // Extraire le message d'erreur
    let message = 'Une erreur inattendue est survenue';

    if (error instanceof Error) {
      message = error.message;
    } else if (typeof error === 'string') {
      message = error;
    } else if (error?.rejection?.message) {
      // Promise rejection
      message = error.rejection.message;
    }

    // Éviter d'afficher les erreurs de chargement de chunks (navigation normale)
    if (message.includes('Loading chunk') || message.includes('ChunkLoadError')) {
      this.ngZone.run(() => {
        this.notificationService.warning(
          'Mise à jour disponible',
          'Veuillez rafraîchir la page pour obtenir la dernière version.',
          {
            label: 'Rafraîchir',
            callback: () => window.location.reload()
          }
        );
      });
      return;
    }

    // Éviter les erreurs de cancel de navigation
    if (message.includes('Navigation ID') || message.includes('Navigation cancelled')) {
      return;
    }

    // Afficher la notification d'erreur
    this.ngZone.run(() => {
      this.notificationService.error(
        'Erreur',
        this.sanitizeErrorMessage(message)
      );
    });
  }

  private sanitizeErrorMessage(message: string): string {
    // Nettoyer les messages techniques pour l'utilisateur
    if (message.includes('Http failure')) {
      return 'Erreur de connexion au serveur';
    }
    if (message.includes('Unknown Error') || message.includes('0 Unknown Error')) {
      return 'Impossible de contacter le serveur';
    }
    if (message.includes('timeout')) {
      return 'La requête a expiré. Veuillez réessayer.';
    }

    // Limiter la longueur du message
    if (message.length > 150) {
      return message.substring(0, 147) + '...';
    }

    return message;
  }
}
