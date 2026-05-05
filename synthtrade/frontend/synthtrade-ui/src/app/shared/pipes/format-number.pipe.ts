import { Pipe, PipeTransform } from '@angular/core';

@Pipe({ name: 'formatNumber', standalone: true, pure: true })
export class FormatNumberPipe implements PipeTransform {
  transform(value: number | null): string {
    if (value === null || value === undefined) return '—';
    if (value >= 1_000_000) return `${this.trim(value / 1_000_000)}M`;
    if (value >= 1_000) return `${this.trim(value / 1_000)}K`;
    return `${value}`;
  }

  private trim(n: number): string {
    return n % 1 === 0 ? `${n}` : `${parseFloat(n.toFixed(1))}`;
  }
}
