# Dashboard API Notes

## Backtest Mainline

Dashboard backtest endpoints now use the unified project backtest mainline:

- `backtest_framework.py` - core engine
- `unified_backtest.py` - market/strategy entry
- `parameter_optimizer.py` - parameter search
- `dashboard/enhanced_backtest.py` - dashboard API adapter

## Supported endpoints

- `POST /api/enhanced/backtest`
- `POST /api/backtest/optimize`
- `POST /api/backtest/walkforward`
- `GET /api/enhanced/markets`
- `GET /api/enhanced/strategies`

## Notes

- Old random/mock optimizer and walk-forward routes have been removed.
- If you add new backtest capability for dashboard, extend `dashboard/enhanced_backtest.py` first.
- Do not add a new standalone backtest engine under `dashboard/`.
