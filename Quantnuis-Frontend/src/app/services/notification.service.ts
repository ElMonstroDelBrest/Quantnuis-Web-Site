import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

export interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message?: string;
  duration?: number;
  action?: {
    label: string;
    callback: () => void;
  };
}

@Injectable({
  providedIn: 'root'
})
export class NotificationService {
  private notifications$ = new BehaviorSubject<Notification[]>([]);

  getNotifications(): Observable<Notification[]> {
    return this.notifications$.asObservable();
  }

  private show(notification: Omit<Notification, 'id'>): string {
    const id = this.generateId();
    const newNotification: Notification = {
      ...notification,
      id,
      duration: notification.duration ?? this.getDefaultDuration(notification.type)
    };

    const current = this.notifications$.value;
    this.notifications$.next([...current, newNotification]);

    // Auto-dismiss
    if (newNotification.duration && newNotification.duration > 0) {
      setTimeout(() => this.dismiss(id), newNotification.duration);
    }

    return id;
  }

  success(title: string, message?: string, action?: Notification['action']): string {
    return this.show({ type: 'success', title, message, action });
  }

  error(title: string, message?: string, action?: Notification['action']): string {
    return this.show({ type: 'error', title, message, action, duration: 8000 });
  }

  warning(title: string, message?: string, action?: Notification['action']): string {
    return this.show({ type: 'warning', title, message, action });
  }

  info(title: string, message?: string, action?: Notification['action']): string {
    return this.show({ type: 'info', title, message, action });
  }

  dismiss(id: string): void {
    const current = this.notifications$.value;
    this.notifications$.next(current.filter(n => n.id !== id));
  }

  dismissAll(): void {
    this.notifications$.next([]);
  }

  private generateId(): string {
    return `notif-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  private getDefaultDuration(type: Notification['type']): number {
    switch (type) {
      case 'error': return 8000;
      case 'warning': return 6000;
      case 'success': return 4000;
      case 'info': return 5000;
      default: return 5000;
    }
  }
}
