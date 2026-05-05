import { Pipe, PipeTransform } from '@angular/core';

@Pipe({ name: 'signedNumber', standalone: true, pure: true })
export class SignedNumberPipe implements PipeTransform {
  transform(value: number | null): string {
    if (value === null || value === undefined) return '—';
    const formatted = Math.abs(value).toFixed(2);
    return value >= 0 ? `+${formatted}` : `-${formatted}`;
  }
}
