import json
from pathlib import Path


def test_real_sample_benchmark_exists_and_has_results():
    path = Path('/root/.openclaw/workspace/quant/quant/data/backtest_benchmark.json')
    assert path.exists()
    payload = json.loads(path.read_text())
    assert payload['suite'] == 'backtest_framework_benchmark'
    assert len(payload['results']) >= 4
    for row in payload['results']:
        assert 'summary' in row
        assert 'total_return_pct' in row['summary']
