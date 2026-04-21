import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, switchMap, tap } from 'rxjs';
import { Router } from '@angular/router';
import { TokenStorage } from '../token.storage';
import { AuthApi, LoginResponse } from '../api/auth.api';
import { UserApi, UserProfile } from '../api/user.api';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private currentUserSubject = new BehaviorSubject<UserProfile | null>(null);
  public currentUser$ = this.currentUserSubject.asObservable();

  constructor(
    private tokenStorage: TokenStorage,
    private authApi: AuthApi,
    private userApi: UserApi,
    private router: Router
  ) {
    this.loadUser();
  }

  // ============= User State Management =============

  private loadUser() {
    const token = this.tokenStorage.getToken();
    if (token) {
      const cachedUser = this.tokenStorage.getUser();
      this.currentUserSubject.next(cachedUser ? { ...cachedUser, token } : { token } as any);
      this.validateToken();
    }
  }

  private validateToken() {
    this.userApi.getProfile().subscribe({
      next: (user) => {
        const token = this.tokenStorage.getToken();
        this.currentUserSubject.next({ ...user, token } as any);
        this.tokenStorage.saveUser(user);
      },
      error: (err) => {
        if (err.status === 401) {
          this.tokenStorage.clear();
          this.currentUserSubject.next(null);
        }
      }
    });
  }

  // ============= Public API =============

  getToken(): string | null {
    return this.tokenStorage.getToken();
  }

  isAuthenticated(): boolean {
    return !!this.getToken();
  }

  isAdmin(): boolean {
    return this.currentUserSubject.value?.is_admin === true;
  }

  getCurrentUser(): UserProfile | null {
    return this.currentUserSubject.value;
  }

  // ============= Auth Actions =============

  register(credentials: { email: string; password: string; username?: string }): Observable<any> {
    return this.authApi.register(credentials);
  }

  login(credentials: { email: string; password: string }): Observable<UserProfile> {
    return this.authApi.login(credentials.email, credentials.password).pipe(
      tap((response: LoginResponse) => {
        this.tokenStorage.saveToken(response.access_token);
        this.currentUserSubject.next({ token: response.access_token } as any);
      }),
      switchMap((response: LoginResponse) =>
        this.userApi.getProfile().pipe(
          tap((user: UserProfile) => {
            this.currentUserSubject.next({ ...user, token: response.access_token } as any);
            this.tokenStorage.saveUser(user);
          })
        )
      )
    );
  }

  logout() {
    this.tokenStorage.clear();
    this.currentUserSubject.next(null);
    this.router.navigate(['/login']);
  }

  getUserProfile(): Observable<UserProfile> {
    return this.userApi.getProfile().pipe(
      tap(user => {
        const current = this.currentUserSubject.value;
        const updatedUser = { ...current, ...user };
        this.currentUserSubject.next(updatedUser);
        this.tokenStorage.saveUser(user);
      })
    );
  }
}
