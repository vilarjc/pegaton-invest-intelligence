import sys
sys.path.insert(0, '.')
from backend.app.core.fear_greed_engine import FearGreedEngine
engine = FearGreedEngine()
result = engine.get_score()
print('Fear & Greed Score:', result['score'])
print('Action:', result['action'], result['action_emoji'])
print('Timestamp:', result['timestamp'])
print('Cached:', result['cacheado'])
print('Factors:')
for name, data in result['factores'].items():
    print(f'  {name}: score={data.get("score")}, peso={data.get("peso")}')