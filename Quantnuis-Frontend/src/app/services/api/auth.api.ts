import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Ec2Api } from './ec2.api';

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

@Injectable({ providedIn: 'root' })
export class AuthApi extends Ec2Api {

  login(email: string, password: string): Observable<LoginResponse> {
    const formData = new FormData();
    formData.append('username', email);
    formData.append('password', password);
    return this.http.post<LoginResponse>(`${this.baseUrl}/token`, formData);
  }

  register(credentials: { email: string; password: string; username?: string }): Observable<any> {
    return this.http.post(`${this.baseUrl}/register`, credentials);
  }
}
