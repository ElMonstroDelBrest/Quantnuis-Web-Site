import { Injectable } from '@angular/core';
import { HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Ec2Api } from './ec2.api';

export interface S3AudioFile {
  key: string;
  filename: string;
  size: number;
  size_formatted: string;
  last_modified: string | null;
}

export interface S3AudioListResponse {
  files: S3AudioFile[];
  count: number;
  bucket: string;
}

export interface S3PresignedUrlResponse {
  url: string;
  key: string;
  expires_in: number;
}

export interface S3FileExistsResponse {
  exists: boolean;
  key: string;
}

@Injectable({ providedIn: 'root' })
export class S3AudioApi extends Ec2Api {

  listAudioFiles(prefix?: string, maxFiles?: number): Observable<S3AudioListResponse> {
    let params = new HttpParams();
    if (prefix) params = params.set('prefix', prefix);
    if (maxFiles) params = params.set('max_files', maxFiles.toString());
    return this.http.get<S3AudioListResponse>(`${this.baseUrl}/s3-audio/files`, { params });
  }

  getPresignedUrl(key: string, expiration?: number): Observable<S3PresignedUrlResponse> {
    let params = new HttpParams().set('key', key);
    if (expiration) params = params.set('expiration', expiration.toString());
    return this.http.get<S3PresignedUrlResponse>(`${this.baseUrl}/s3-audio/presigned-url`, { params });
  }

  fileExists(key: string): Observable<S3FileExistsResponse> {
    const params = new HttpParams().set('key', key);
    return this.http.get<S3FileExistsResponse>(`${this.baseUrl}/s3-audio/file-exists`, { params });
  }

  async downloadAudioFile(key: string): Promise<File> {
    const response = await this.getPresignedUrl(key).toPromise();
    if (!response) {
      throw new Error('Impossible de generer l\'URL presignee');
    }

    const fileResponse = await fetch(response.url);
    if (!fileResponse.ok) {
      throw new Error(`Erreur lors du telechargement: ${fileResponse.status}`);
    }

    const blob = await fileResponse.blob();
    const filename = key.split('/').pop() || 'audio.wav';
    const mimeType = this.getMimeType(filename);
    return new File([blob], filename, { type: mimeType });
  }

  private getMimeType(filename: string): string {
    const ext = filename.toLowerCase().split('.').pop();
    const mimeTypes: Record<string, string> = {
      'wav': 'audio/wav',
      'mp3': 'audio/mpeg',
      'ogg': 'audio/ogg',
      'flac': 'audio/flac',
      'm4a': 'audio/mp4',
      'mp4': 'audio/mp4'
    };
    return mimeTypes[ext || ''] || 'audio/wav';
  }
}
