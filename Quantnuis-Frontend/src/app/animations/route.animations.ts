import {
  trigger,
  transition,
  style,
  animate,
  query
} from '@angular/animations';

// Component-level entry animation (cards, lists, etc.)
export const fadeIn = trigger('fadeIn', [
  transition(':enter', [
    style({ opacity: 0, transform: 'translateY(10px)' }),
    animate('250ms ease-out', style({ opacity: 1, transform: 'translateY(0)' }))
  ])
]);

// Slide from right (panels, drawers)
export const slideInRight = trigger('slideInRight', [
  transition(':enter', [
    style({ opacity: 0, transform: 'translateX(30px)' }),
    animate('250ms ease-out', style({ opacity: 1, transform: 'translateX(0)' }))
  ]),
  transition(':leave', [
    animate('180ms ease-in', style({ opacity: 0, transform: 'translateX(-20px)' }))
  ])
]);

// Scale in (modals, popovers)
export const scaleIn = trigger('scaleIn', [
  transition(':enter', [
    style({ opacity: 0, transform: 'scale(0.95)' }),
    animate('200ms cubic-bezier(0.34, 1.56, 0.64, 1)', style({ opacity: 1, transform: 'scale(1)' }))
  ]),
  transition(':leave', [
    animate('140ms ease-in', style({ opacity: 0, transform: 'scale(0.95)' }))
  ])
]);

// Expand/collapse (accordions)
export const expandCollapse = trigger('expandCollapse', [
  transition(':enter', [
    style({ height: 0, opacity: 0, overflow: 'hidden' }),
    animate('220ms ease-out', style({ height: '*', opacity: 1 }))
  ]),
  transition(':leave', [
    style({ height: '*', opacity: 1, overflow: 'hidden' }),
    animate('180ms ease-in', style({ height: 0, opacity: 0 }))
  ])
]);

// Stagger list items
export const staggerList = trigger('staggerList', [
  transition('* => *', [
    query(':enter', [
      style({ opacity: 0, transform: 'translateY(10px)' }),
      animate('250ms ease-out', style({ opacity: 1, transform: 'translateY(0)' }))
    ], { optional: true })
  ])
]);
