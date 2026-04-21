import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { HttpParams } from '@angular/common/http';
import { Ec2Api } from './ec2.api';

export type ReviewStatus = 'pending' | 'confirmed' | 'corrected';

export interface AudioReview {
  id: number;
  s3_key: string;
  car_detected: boolean;
  car_confidence: number;
  car_probability: number;
  is_noisy: boolean | null;
  noisy_confidence: number | null;
  noisy_probability: number | null;
  review_status: ReviewStatus;
  reviewer_comment: string | null;
  analyzed_at: string;
  reviewed_at: string | null;
  audio_url: string | null;
}

export interface AudioReviewListResponse {
  reviews: AudioReview[];
  total: number;
  page: number;
  page_size: number;
}

export interface AudioReviewStats {
  total: number;
  pending: number;
  confirmed: number;
  corrected: number;
  accuracy_rate: number | null;
}

export interface AudioReviewValidation {
  status: 'confirmed' | 'corrected';
  comment?: string;
}

export interface ScanResult {
  message: string;
  new_files: number;
  total_s3?: number;
  already_analyzed?: number;
}

@Injectable({ providedIn: 'root' })
export class AudioReviewApi extends Ec2Api {

  scanNewFiles(): Observable<ScanResult> {
    return this.http.post<ScanResult>(`${this.baseUrl}/audio-reviews/scan`, {});
  }

  listReviews(status: string = 'all', page: number = 1, pageSize: number = 20): Observable<AudioReviewListResponse> {
    const params = new HttpParams()
      .set('status_filter', status)
      .set('page', page)
      .set('page_size', pageSize);
    return this.http.get<AudioReviewListResponse>(`${this.baseUrl}/audio-reviews`, { params });
  }

  getStats(): Observable<AudioReviewStats> {
    return this.http.get<AudioReviewStats>(`${this.baseUrl}/audio-reviews/stats`);
  }

  validateReview(reviewId: number, validation: AudioReviewValidation): Observable<{ message: string }> {
    return this.http.patch<{ message: string }>(`${this.baseUrl}/audio-reviews/${reviewId}`, validation);
  }
}
