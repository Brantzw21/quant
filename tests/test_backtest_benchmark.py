import json

from backtest_benchmark import run_benchmark_suite


def test_benchmark_suite_has_multiple_cases(tmp_path):
    payload = run_benchmark_suite()
    assert payload['suite'] == 'backtest_framework_benchmark'
    assert len(payload['results']) >= 3
    for row in payload['results']:
        assert 'summary' in row
        assert 'total_return_pct' in row['summary']

    out = tmp_path / 'bench.json'
    out.write_text(json.dumps(payload, ensure_ascii=False))
    assert out.exists()
