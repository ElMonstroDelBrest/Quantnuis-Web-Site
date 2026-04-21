import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { AdminApi, AnnotationRequest, AdminUser, AdminStats, ReviewAction } from './api/admin.api';

export type { AnnotationRequest, AdminUser, AdminStats, ReviewAction } from './api/admin.api';

@Injectable({ providedIn: 'root' })
export class AdminService {

  constructor(private adminApi: AdminApi) {}

  getStats(): Observable<AdminStats> {
    return this.adminApi.getAnnotationRequestsStats();
  }

  getAnnotationRequests(status: string = 'pending'): Observable<AnnotationRequest[]> {
    return this.adminApi.getAnnotationRequests(status);
  }

  getAnnotationRequestDetails(requestId: number): Observable<AnnotationRequest> {
    return this.adminApi.getAnnotationRequestDetails(requestId);
  }

  reviewAnnotationRequest(requestId: number, action: ReviewAction, note?: string): Observable<{ message: string }> {
    return this.adminApi.reviewAnnotationRequest(requestId, action, note);
  }

  getAllUsers(): Observable<AdminUser[]> {
    return this.adminApi.getAllUsers();
  }

  makeUserAdmin(userId: number): Observable<{ message: string }> {
    return this.adminApi.makeUserAdmin(userId);
  }
}
