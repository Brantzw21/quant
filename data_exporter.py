#!/usr/bin/env python3
"""
数据导出器
支持多种格式导出: CSV/JSON/Excel/HTML
"""

import os
import sys
import json
import csv
import pandas as pd
from typing import Dict, List, Any
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class ExportConfig:
    """导出配置"""
    output_dir: str = "/root/.openclaw/workspace/quant/quant/data/exports"
    filename_prefix: str = "export"
    include_timestamp: bool = True


class DataExporter:
    """
    数据导出器
    
    支持格式:
    - CSV
    - JSON
    - Excel
    - HTML
    """
    
    def __init__(self, config: ExportConfig = None):
        self.config = config or ExportConfig()
        os.makedirs(self.config.output_dir, exist_ok=True)
    
    def _get_filename(self, suffix: str, ext: str) -> str:
        """生成文件名"""
        parts = [self.config.filename_prefix, suffix]
        
        if self.config.include_timestamp:
            parts.append(datetime.now().strftime("%Y%m%d_%H%M%S"))
        
        filename = "_".join(parts) + ext
        
        return os.path.join(self.config.output_dir, filename)
    
    def to_csv(self, data: List[Dict], suffix: str = "data") -> str:
        """导出CSV"""
        if not data:
            return ""
        
        filepath = self._get_filename(suffix, ".csv")
        
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        
        return filepath
    
    def to_json(self, data: Any, suffix: str = "data") -> str:
        """导出JSON"""
        filepath = self._get_filename(suffix, ".json")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        return filepath
    
    def to_excel(self, data: Dict[str, List], suffix: str = "data") -> str:
        """导出Excel (多Sheet)"""
        filepath = self._get_filename(suffix, ".xlsx")
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            for sheet_name, rows in data.items():
                if rows:
                    df = pd.DataFrame(rows)
                    # Excel sheet名限制31字符
                    sheet_name = sheet_name[:31]
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        return filepath
    
    def to_html(self, data: List[Dict], title: str = "Data Report", 
                suffix: str = "data") -> str:
        """导出HTML"""
        if not data:
            return ""
        
        filepath = self._get_filename(suffix, ".html")
        
        df = pd.DataFrame(data)
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        tr:hover {{ background-color: #ddd; }}
        .timestamp {{ color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    {df.to_html(index=False, classes='data-table')}
</body>
</html>
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return filepath
    
    # ===== 专用导出方法 =====
    
    def export_trades(self, trades: List[Dict]) -> str:
        """导出交易记录"""
        return self.to_csv(trades, "trades")
    
    def export_signals(self, signals: List[Dict]) -> str:
        """导出信号历史"""
        return self.to_json(signals, "signals")
    
    def export_performance(self, performance: Dict) -> str:
        """导出绩效报告"""
        return self.to_json(performance, "performance")
    
    def export_full_report(self, data: Dict[str, Any]) -> str:
        """导出完整报告 (多格式)"""
        results = {}
        
        # 导出各部分
        if 'trades' in data:
            results['trades'] = self.to_csv(data['trades'], "trades")
        
        if 'signals' in data:
            results['signals'] = self.to_json(data['signals'], "signals")
        
        if 'performance' in data:
            results['performance'] = self.to_json(data['performance'], "performance")
        
        # Excel汇总
        excel_data = {}
        
        if 'trades' in data:
            excel_data['交易记录'] = data['trades']
        
        if 'positions' in data:
            excel_data['持仓'] = data['positions']
        
        if 'orders' in data:
            excel_data['订单'] = data['orders']
        
        if excel_data:
            results['excel'] = self.to_excel(excel_data, "report")
        
        return results


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 50)
    print("数据导出器")
    print("=" * 50)
    
    # 创建导出器
    exporter = DataExporter()
    
    # 模拟交易数据
    trades = [
        {"time": "2026-01-01 10:00", "symbol": "BTCUSDT", "side": "BUY", "price": 45000, "quantity": 0.1},
        {"time": "2026-01-05 14:30", "symbol": "BTCUSDT", "side": "SELL", "price": 46000, "quantity": 0.1, "pnl": 100},
        {"time": "2026-01-10 09:15", "symbol": "ETHUSDT", "side": "BUY", "price": 2500, "quantity": 1},
        {"time": "2026-01-15 11:00", "symbol": "ETHUSDT", "side": "SELL", "price": 2400, "quantity": 1, "pnl": -100},
    ]
    
    # 导出CSV
    print("\n导出CSV...")
    csv_file = exporter.to_csv(trades, "trades")
    print(f"  -> {csv_file}")
    
    # 导出JSON
    print("\n导出JSON...")
    json_file = exporter.to_json(trades, "trades")
    print(f"  -> {json_file}")
    
    # 导出HTML
    print("\n导出HTML...")
    html_file = exporter.to_html(trades, "交易记录", "trades")
    print(f"  -> {html_file}")
    
    # 导出完整报告
    print("\n导出完整报告...")
    report_data = {
        'trades': trades,
        'signals': [
            {"time": "2026-01-01", "signal": "BUY", "confidence": 0.75},
            {"time": "2026-01-10", "signal": "SELL", "confidence": 0.65},
        ],
        'performance': {
            'total_return': 0.15,
            'sharpe_ratio': 1.5,
            'max_drawdown': 0.08
        }
    }
    results = exporter.export_full_report(report_data)
    
    for key, filepath in results.items():
        print(f"  {key}: {filepath}")
    
    print("\n✅ 导出完成")
