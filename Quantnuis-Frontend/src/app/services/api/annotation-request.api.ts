import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Ec2Api } from './ec2.api';

export interface AnnotationRequestResponse {
  id: number;
  filename: string;
  model_type: string;
  status: string;
  created_at: string;
}

@Injectable({ providedIn: 'root' })
export class AnnotationRequestApi extends Ec2Api {

  submit(audio: File, annotationsCsv: Blob, model: string): Observable<AnnotationRequestResponse> {
    const formData = new FormData();
    formData.append('audio', audio);
    formData.append('annotations', annotationsCsv, 'annotations.csv');
    formData.append('model', model);
    return this.http.post<AnnotationRequestResponse>(`${this.baseUrl}/annotation-requests`, formData);
  }

  getMy(): Observable<AnnotationRequestResponse[]> {
    return this.http.get<AnnotationRequestResponse[]>(`${this.baseUrl}/annotation-requests/my`);
  }
}
