import { RelativeTimePipe } from './relative-time.pipe';

describe('RelativeTimePipe', () => {
  const pipe = new RelativeTimePipe();

  it('should return "—" for null', () => {
    expect(pipe.transform(null)).toBe('—');
  });

  it('should return seconds ago', () => {
    const d = new Date(Date.now() - 30_000).toISOString();
    expect(pipe.transform(d)).toBe('30s ago');
  });

  it('should return minutes ago', () => {
    const d = new Date(Date.now() - 2 * 60_000).toISOString();
    expect(pipe.transform(d)).toBe('2m ago');
  });

  it('should return hours ago', () => {
    const d = new Date(Date.now() - 3 * 3_600_000).toISOString();
    expect(pipe.transform(d)).toBe('3h ago');
  });

  it('should return days ago', () => {
    const d = new Date(Date.now() - 2 * 86_400_000).toISOString();
    expect(pipe.transform(d)).toBe('2d ago');
  });
});
