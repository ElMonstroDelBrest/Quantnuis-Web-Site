import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { HttpParams } from '@angular/common/http';
import { Ec2Api } from './ec2.api';

export interface AnnotationRequest {
  id: number;
  filename: string;
  model_type: string;
  status: 'pending' | 'approved' | 'rejected';
  annotation_count: number;
  total_duration: number;
  created_at: string;
  reviewed_at: string | null;
  reviewed_by_email: string | null;
  admin_note: string | null;
  submitted_by_email: string;
  annotations?: any[];
}

export interface AdminUser {
  id: number;
  email: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
}

export interface AdminStats {
  total: number;
  pending: number;
  approved: number;
  rejected: number;
}

export type ReviewAction = 'approve' | 'reject';

@Injectable({ providedIn: 'root' })
export class AdminApi extends Ec2Api {

  getAnnotationRequests(status: string = 'pending'): Observable<AnnotationRequest[]> {
    const params = new HttpParams().set('status_filter', status);
    return this.http.get<AnnotationRequest[]>(`${this.baseUrl}/admin/annotation-requests`, { params });
  }

  getAnnotationRequestDetails(requestId: number): Observable<AnnotationRequest> {
    return this.http.get<AnnotationRequest>(`${this.baseUrl}/admin/annotation-requests/${requestId}`);
  }

  reviewAnnotationRequest(requestId: number, action: ReviewAction, note?: string): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(`${this.baseUrl}/admin/annotation-requests/${requestId}/review`, { action, note });
  }

  getAnnotationRequestsStats(): Observable<AdminStats> {
    return this.http.get<AdminStats>(`${this.baseUrl}/admin/annotation-requests/stats`);
  }

  getAllUsers(): Observable<AdminUser[]> {
    return this.http.get<AdminUser[]>(`${this.baseUrl}/admin/users`);
  }

  makeUserAdmin(userId: number): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(`${this.baseUrl}/admin/users/${userId}/make-admin`, {});
  }
}
