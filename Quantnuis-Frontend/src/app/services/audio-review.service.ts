import { Injectable } from '@angular/core';
import { Observable, combineLatest, map } from 'rxjs';
import {
  AudioReviewApi,
  AudioReview, AudioReviewListResponse, AudioReviewStats,
  AudioReviewValidation, ScanResult, ReviewStatus,
} from './api/audio-review.api';

export type { AudioReview, AudioReviewListResponse, AudioReviewStats, AudioReviewValidation, ScanResult, ReviewStatus } from './api/audio-review.api';

export interface ReviewPageData {
  reviews: AudioReview[];
  stats: AudioReviewStats;
  total: number;
  page: number;
  pageSize: number;
}

@Injectable({ providedIn: 'root' })
export class AudioReviewService {

  constructor(private audioReviewApi: AudioReviewApi) {}

  scanNewFiles(): Observable<ScanResult> {
    return this.audioReviewApi.scanNewFiles();
  }

  listReviews(status: string = 'all', page: number = 1, pageSize: number = 20): Observable<AudioReviewListResponse> {
    return this.audioReviewApi.listReviews(status, page, pageSize);
  }

  getStats(): Observable<AudioReviewStats> {
    return this.audioReviewApi.getStats();
  }

  validateReview(reviewId: number, validation: AudioReviewValidation): Observable<{ message: string }> {
    return this.audioReviewApi.validateReview(reviewId, validation);
  }

  loadReviewPage(status: string = 'all', page: number = 1, pageSize: number = 20): Observable<ReviewPageData> {
    return combineLatest([
      this.audioReviewApi.listReviews(status, page, pageSize),
      this.audioReviewApi.getStats(),
    ]).pipe(
      map(([list, stats]) => ({
        reviews: list.reviews,
        stats,
        total: list.total,
        page: list.page,
        pageSize: list.page_size,
      }))
    );
  }
}
