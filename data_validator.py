#!/usr/bin/env python3
"""
数据验证器
验证数据质量、完整性、一致性
"""

import sys
import os
sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class ValidationIssue:
    """验证问题"""
    severity: str  # error, warning, info
    category: str  # missing, outlier, anomaly, consistency
    field: str
    message: str
    row: int = -1
    value: any = None


class DataValidator:
    """
    数据验证器
    
    检查:
    - 缺失值
    - 异常值
    - 数据类型
    - 范围检查
    - 一致性
    - 重复
    """
    
    def __init__(self):
        self.issues = []
        self.stats = {}
    
    def validate_dataframe(self, df: pd.DataFrame, rules: Dict = None) -> List[ValidationIssue]:
        """
        验证DataFrame
        
        Args:
            df: 数据
            rules: 验证规则
        
        Returns:
            问题列表
        """
        self.issues = []
        
        # 默认规则
        rules = rules or {}
        
        # 1. 缺失值检查
        self._check_missing(df)
        
        # 2. 重复检查
        self._check_duplicates(df)
        
        # 3. 类型检查
        self._check_types(df)
        
        # 4. 范围检查
        if 'ranges' in rules:
            self._check_ranges(df, rules['ranges'])
        
        # 5. 异常值检查
        if 'outliers' in rules:
            self._check_outliers(df, rules['outliers'])
        
        # 6. 一致性检查
        if 'consistency' in rules:
            self._check_consistency(df, rules['consistency'])
        
        return self.issues
    
    def _check_missing(self, df: pd.DataFrame):
        """检查缺失值"""
        for col in df.columns:
            missing = df[col].isna()
            
            if missing.any():
                count = missing.sum()
                pct = count / len(df) * 100
                
                if pct > 50:
                    severity = 'error'
                elif pct > 10:
                    severity = 'warning'
                else:
                    severity = 'info'
                
                self.issues.append(ValidationIssue(
                    severity=severity,
                    category='missing',
                    field=col,
                    message=f"缺失 {count} 条 ({pct:.1f}%)",
                    value=count
                ))
    
    def _check_duplicates(self, df: pd.DataFrame):
        """检查重复"""
        if 'timestamp' in df.columns and 'symbol' in df.columns:
            # 时间+品种重复
            dup = df.duplicated(['timestamp', 'symbol']).sum()
            
            if dup > 0:
                self.issues.append(ValidationIssue(
                    severity='warning',
                    category='duplicates',
                    field='timestamp+symbol',
                    message=f"发现 {dup} 条重复记录",
                    value=dup
                ))
        else:
            # 全字段重复
            dup = df.duplicated().sum()
            
            if dup > 0:
                self.issues.append(ValidationIssue(
                    severity='warning',
                    category='duplicates',
                    field='all',
                    message=f"发现 {dup} 条完全重复",
                    value=dup
                ))
    
    def _check_types(self, df: pd.DataFrame):
        """检查数据类型"""
        for col in df.columns:
            # 数值列检查
            if col in ['close', 'open', 'high', 'low', 'volume', 'price']:
                if df[col].dtype == 'object':
                    # 尝试转换
                    try:
                        pd.to_numeric(df[col])
                    except:
                        self.issues.append(ValidationIssue(
                            severity='error',
                            category='type',
                            field=col,
                            message=f"数据类型错误: {df[col].dtype}",
                            value=str(df[col].dtype)
                        ))
    
    def _check_ranges(self, df: pd.DataFrame, ranges: Dict):
        """检查范围"""
        for col, (min_val, max_val) in ranges.items():
            if col not in df.columns:
                continue
            
            out_of_range = ((df[col] < min_val) | (df[col] > max_val)).sum()
            
            if out_of_range > 0:
                pct = out_of_range / len(df) * 100
                
                self.issues.append(ValidationIssue(
                    severity='warning' if pct < 5 else 'error',
                    category='range',
                    field=col,
                    message=f"{out_of_range} 条超出范围 [{min_val}, {max_val}] ({pct:.1f}%)",
                    value=out_of_range
                ))
    
    def _check_outliers(self, df: pd.DataFrame, columns: List[str]):
        """检查异常值 (IQR方法)"""
        for col in columns:
            if col not in df.columns:
                continue
            
            # 转换数值
            try:
                values = pd.to_numeric(df[col], errors='coerce').dropna()
            except:
                continue
            
            if len(values) < 10:
                continue
            
            # IQR
            q1 = values.quantile(0.25)
            q3 = values.quantile(0.75)
            iqr = q3 - q1
            
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            
            outliers = ((values < lower) | (values > upper)).sum()
            
            if outliers > 0:
                pct = outliers / len(values) * 100
                
                self.issues.append(ValidationIssue(
                    severity='info',
                    category='outlier',
                    field=col,
                    message=f"发现 {outliers} 个异常值 ({pct:.1f}%)",
                    value=outliers
                ))
    
    def _check_consistency(self, df: pd.DataFrame, rules: Dict):
        """一致性检查"""
        # high >= low
        if 'high' in df.columns and 'low' in df.columns:
            invalid = (df['high'] < df['low']).sum()
            
            if invalid > 0:
                self.issues.append(ValidationIssue(
                    severity='error',
                    category='consistency',
                    field='high<low',
                    message=f"最高价 < 最低价: {invalid} 条",
                    value=invalid
                ))
        
        # close 在 high-low 之间
        if all(c in df.columns for c in ['close', 'high', 'low']):
            invalid = ((df['close'] > df['high']) | (df['close'] < df['low'])).sum()
            
            if invalid > 0:
                self.issues.append(ValidationIssue(
                    severity='warning',
                    category='consistency',
                    field='close',
                    message=f"收盘价超出高低范围: {invalid} 条",
                    value=invalid
                ))
        
        # 时间递增
        if 'timestamp' in df.columns:
            try:
                times = pd.to_datetime(df['timestamp'])
                invalid = (times.diff() < timedelta(0)).sum()
                
                if invalid > 0:
                    self.issues.append(ValidationIssue(
                        severity='error',
                        category='consistency',
                        field='timestamp',
                        message=f"时间非递增: {invalid} 条",
                        value=invalid
                    ))
            except:
                pass
    
    def get_summary(self) -> Dict:
        """获取验证摘要"""
        summary = {
            'total_issues': len(self.issues),
            'by_severity': {},
            'by_category': {}
        }
        
        for issue in self.issues:
            # 按严重性统计
            summary['by_severity'][issue.severity] = \
                summary['by_severity'].get(issue.severity, 0) + 1
            
            # 按类别统计
            summary['by_category'][issue.category] = \
                summary['by_category'].get(issue.category, 0) + 1
        
        return summary
    
    def is_valid(self, max_errors: int = 0, max_warnings: int = 10) -> bool:
        """是否通过验证"""
        errors = sum(1 for i in self.issues if i.severity == 'error')
        warnings = sum(1 for i in self.issues if i.severity == 'warning')
        
        return errors <= max_errors and warnings <= max_warnings


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 50)
    print("数据验证器")
    print("=" * 50)
    
    # 创建测试数据
    data = {
        'timestamp': pd.date_range('2024-01-01', periods=100, freq='1H'),
        'symbol': ['BTC'] * 50 + ['ETH'] * 50,
        'open': np.random.uniform(40000, 50000, 100),
        'high': np.random.uniform(40000, 50000, 100),
        'low': np.random.uniform(40000, 50000, 100),
        'close': np.random.uniform(40000, 50000, 100),
        'volume': np.random.uniform(1000, 10000, 100),
    }
    
    # 添加问题
    data['close'][0] = np.nan  # 缺失值
    data['high'][10] = data['low'][10] - 100  # high < low
    data['volume'][20] = 1000000  # 异常值
    
    df = pd.DataFrame(data)
    
    # 验证
    validator = DataValidator()
    
    rules = {
        'ranges': {
            'volume': (0, 50000),
            'close': (10000, 100000)
        },
        'outliers': ['volume', 'close'],
        'consistency': True
    }
    
    issues = validator.validate_dataframe(df, rules)
    
    # 结果
    print(f"\n📊 验证结果:")
    print(f"  发现 {len(issues)} 个问题")
    print(f"  通过: {'✅' if validator.is_valid() else '❌'}")
    
    print(f"\n📋 问题列表:")
    for issue in issues:
        emoji = {'error': '❌', 'warning': '⚠️', 'info': 'ℹ️'}.get(issue.severity, '❓')
        print(f"  {emoji} [{issue.severity}] {issue.field}: {issue.message}")
    
    print(f"\n📈 摘要:")
    summary = validator.get_summary()
    print(f"  按严重性: {summary['by_severity']}")
    print(f"  按类别: {summary['by_category']}")
