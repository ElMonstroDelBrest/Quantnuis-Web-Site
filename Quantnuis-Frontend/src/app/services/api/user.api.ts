import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Ec2Api } from './ec2.api';

export interface UserProfile {
  id: number;
  email: string;
  username?: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
  token?: string;
}

export interface UserStats {
  total_analyses: number;
  noisy_detections: number;
  last_analysis_date: string | null;
}

export interface AnalysisHistoryEntry {
  id: number;
  filename: string;
  has_noisy_vehicle: boolean;
  confidence: number;
  max_decibels: number;
  created_at: string;
}

@Injectable({ providedIn: 'root' })
export class UserApi extends Ec2Api {

  getProfile(): Observable<UserProfile> {
    return this.http.get<UserProfile>(`${this.baseUrl}/users/me`);
  }

  getStats(): Observable<UserStats> {
    return this.http.get<UserStats>(`${this.baseUrl}/stats`);
  }

  getHistory(): Observable<AnalysisHistoryEntry[]> {
    return this.http.get<AnalysisHistoryEntry[]>(`${this.baseUrl}/history`);
  }
}
