import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { S3AudioApi, S3AudioFile, S3AudioListResponse, S3PresignedUrlResponse, S3FileExistsResponse } from './api/s3-audio.api';

export type { S3AudioFile, S3AudioListResponse } from './api/s3-audio.api';

@Injectable({ providedIn: 'root' })
export class S3AudioService {

  constructor(private s3AudioApi: S3AudioApi) {}

  listAudioFiles(prefix?: string, maxFiles?: number): Observable<S3AudioListResponse> {
    return this.s3AudioApi.listAudioFiles(prefix, maxFiles);
  }

  getPresignedUrl(key: string, expiration?: number): Observable<S3PresignedUrlResponse> {
    return this.s3AudioApi.getPresignedUrl(key, expiration);
  }

  fileExists(key: string): Observable<S3FileExistsResponse> {
    return this.s3AudioApi.fileExists(key);
  }

  async downloadAudioFile(key: string): Promise<File> {
    return this.s3AudioApi.downloadAudioFile(key);
  }
}
