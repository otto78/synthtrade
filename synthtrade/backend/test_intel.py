import asyncio
import sys
sys.path.insert(0, '.')

async def test():
    from app.scalping.intelligence.signal_score_engine import SignalScoreEngine
    engine = SignalScoreEngine(symbol='BTCUSDT')
    snapshot = await engine.get_snapshot()
    score = snapshot.signal_score
    if score is None:
        print('ERROR: signal_score is None')
        return
    print(f'Score: {score.total}')
    print(f'Bias: {score.bias}')
    print(f'Tradeable: {score.tradeable}')
    print(f'Signal strength: {score.signal_strength}')
    print(f'Breakdown: {score.breakdown}')
    print()
    print(f'FundingRate: {snapshot.funding_rate}')
    print(f'OpenInterest: {snapshot.open_interest}')
    print(f'LongShort: {snapshot.long_short_ratio}')
    print(f'FearGreed: {snapshot.fear_greed}')
    print(f'Sentiment: {snapshot.sentiment}')
    print(f'Whale: {snapshot.whale}')
    print(f'Onchain: {snapshot.onchain}')
    print(f'CVD: {snapshot.cvd}')

asyncio.run(test())