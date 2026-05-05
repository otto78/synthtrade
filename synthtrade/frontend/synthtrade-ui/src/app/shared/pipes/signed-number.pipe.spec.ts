import { SignedNumberPipe } from './signed-number.pipe';

describe('SignedNumberPipe', () => {
  const pipe = new SignedNumberPipe();

  it('should return "—" for null', () => {
    expect(pipe.transform(null)).toBe('—');
  });

  it('should prefix positive numbers with +', () => {
    expect(pipe.transform(3.5)).toBe('+3.50');
  });

  it('should keep minus sign for negative numbers', () => {
    expect(pipe.transform(-2.1)).toBe('-2.10');
  });

  it('should show +0.00 for zero', () => {
    expect(pipe.transform(0)).toBe('+0.00');
  });
});
