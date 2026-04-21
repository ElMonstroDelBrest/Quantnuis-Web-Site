import { Component, OnInit, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { ToastComponent } from './components/toast/toast.component';
import { OfflineBannerComponent } from './components/offline-banner/offline-banner.component';
import { WarmupService } from './services/warmup.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, ToastComponent, OfflineBannerComponent],
  template: `
    <app-offline-banner></app-offline-banner>
    <router-outlet></router-outlet>
    <app-toast></app-toast>
  `,
  styles: []
})
export class App implements OnInit {
  private warmup = inject(WarmupService);

  ngOnInit() {
    this.warmup.warmLambda();
  }
}
