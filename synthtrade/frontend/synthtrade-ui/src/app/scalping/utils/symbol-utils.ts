/**
 * TASK-1118.C: Symbol normalization utility for provider-neutral symbol comparison.
 *
 * OKX uses instId format: BTC-EUR
 * Session state uses: BTCEUR
 * WS events may use either format depending on source.
 *
 * Always normalize before comparing symbols across different sources.
 */

export class SymbolUtils {
  /**
   * Normalize any symbol format to uppercase without separators.
   * BTC-EUR → BTCEUR, BTC/EUR → BTCEUR, btceur → BTCEUR
   */
  static normalize(s: string): string {
    return s.toUpperCase().replace(/[-/]/g, '');
  }

  /**
   * Check if two symbols represent the same instrument.
   */
  static equals(a: string, b: string): boolean {
    return SymbolUtils.normalize(a) === SymbolUtils.normalize(b);
  }
}