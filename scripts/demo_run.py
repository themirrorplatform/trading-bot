import os, sys
from datetime import datetime

# Ensure package path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from trading_bot.core.runner import BotRunner

bar = {
    "symbol": "MES",
    "ts": datetime.now().isoformat(),
    "o": 100.0,
    "h": 101.0,
    "l": 99.5,
    "c": 100.5,
    "v": 1000,
}

runner = BotRunner()
res = runner.run_once(bar)
print(res)
