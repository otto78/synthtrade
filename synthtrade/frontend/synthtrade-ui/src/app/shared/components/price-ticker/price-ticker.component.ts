import { ChangeDetectionStrategy, Component, effect, input, signal } from '@angular/core';
import { NgClass } from '@angular/common';

@Component({
  selector: 'app-price-ticker',
  standalone: true,
  imports: [NgClass],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <span class="price" [ngClass]="flashClass()" (animationend)="clearFlash()">
      {{ formatPrice() }}
    </span>
  `,
  styles: [`
    .price { font-family: monospace; }
    .flash-up   { animation: price-up   0.6s ease; }
    .flash-down { animation: price-down 0.6s ease; }
    @keyframes price-up   { 0%,100%{color:var(--text-primary,#eee)} 40%{color:var(--color-buy,#0ECB81)} }
    @keyframes price-down { 0%,100%{color:var(--text-primary,#eee)} 40%{color:var(--color-sell,#F6465D)} }
  `]
})
export class PriceTickerComponent {
  price = input.required<number>();
  decimals = input<number>(2);

  flashClass = signal('');
  private prev: number | null = null;

  constructor() {
    effect(() => {
      const current = this.price();
      if (this.prev !== null) {
        this.flashClass.set(current > this.prev ? 'flash-up' : current < this.prev ? 'flash-down' : '');
      }
      this.prev = current;
    });
  }

  clearFlash(): void {
    this.flashClass.set('');
  }

  formatPrice(): string {
    return this.price().toLocaleString('en-US', {
      minimumFractionDigits: this.decimals(),
      maximumFractionDigits: this.decimals(),
    });
  }
}
