import { FormatNumberPipe } from './format-number.pipe';

describe('FormatNumberPipe', () => {
  const pipe = new FormatNumberPipe();

  it('should return "—" for null', () => {
    expect(pipe.transform(null)).toBe('—');
  });

  it('should format numbers below 1000 as-is', () => {
    expect(pipe.transform(999)).toBe('999');
  });

  it('should format thousands with K suffix', () => {
    expect(pipe.transform(1500)).toBe('1.5K');
  });

  it('should format millions with M suffix', () => {
    expect(pipe.transform(2_500_000)).toBe('2.5M');
  });

  it('should format exact thousands without decimal', () => {
    expect(pipe.transform(2000)).toBe('2K');
  });
});
