import { Injectable } from '@angular/core';
import { Observable, combineLatest, map } from 'rxjs';
import { UserApi, UserStats, AnalysisHistoryEntry } from './api/user.api';

export interface DashboardData {
  stats: UserStats;
  history: AnalysisHistoryEntry[];
}

@Injectable({ providedIn: 'root' })
export class DashboardService {

  constructor(private userApi: UserApi) {}

  loadDashboardData(): Observable<DashboardData> {
    return combineLatest([
      this.userApi.getStats(),
      this.userApi.getHistory()
    ]).pipe(
      map(([stats, history]) => ({ stats, history: history || [] }))
    );
  }

  getStats(): Observable<UserStats> {
    return this.userApi.getStats();
  }

  getHistory(): Observable<AnalysisHistoryEntry[]> {
    return this.userApi.getHistory();
  }
}
