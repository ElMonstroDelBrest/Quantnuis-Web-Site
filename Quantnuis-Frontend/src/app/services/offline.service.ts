import { Injectable, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { BehaviorSubject, Observable, fromEvent, merge } from 'rxjs';
import { map, distinctUntilChanged } from 'rxjs/operators';

@Injectable({
  providedIn: 'root'
})
export class OfflineService {
  private isOnline$ = new BehaviorSubject<boolean>(navigator.onLine);
  private destroyRef = inject(DestroyRef);

  constructor() {
    const online$ = fromEvent(window, 'online').pipe(map(() => true));
    const offline$ = fromEvent(window, 'offline').pipe(map(() => false));

    merge(online$, offline$).pipe(
      distinctUntilChanged(),
      takeUntilDestroyed(this.destroyRef)
    ).subscribe(isOnline => {
      this.isOnline$.next(isOnline);
    });
  }

  getOnlineStatus(): Observable<boolean> {
    return this.isOnline$.asObservable().pipe(distinctUntilChanged());
  }

  isOnline(): boolean {
    return this.isOnline$.value;
  }

  isOffline(): boolean {
    return !this.isOnline$.value;
  }
}
