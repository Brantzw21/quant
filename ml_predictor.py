#!/usr/bin/env python3
"""
机器学习预测模型
LSTM/GRU 预测价格走势
"""

import sys
import os
sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from dataclasses import dataclass


class MLPricePredictor:
    """
    机器学习价格预测
    
    模型:
    - Simple Moving Average (基准)
    - Linear Regression
    - Random Forest
    - LSTM (需要tensorflow)
    """
    
    def __init__(self, model_type: str = "lr"):
        self.model_type = model_type
        self.model = None
        self.scaler = None
        self.sequence_length = 30
        
        # 特征
        self.features = [
            'close', 'volume', 'returns',
            'ma5', 'ma20', 'ma60',
            'rsi', 'macd', 'boll'
        ]
    
    def prepare_data(self, df: pd.DataFrame, target_col: str = 'close') -> Tuple:
        """准备训练数据"""
        # 计算特征
        data = df.copy()
        
        # 技术指标
        data['returns'] = data['close'].pct_change()
        data['ma5'] = data['close'].rolling(5).mean()
        data['ma20'] = data['close'].rolling(20).mean()
        data['ma60'] = data['close'].rolling(60).mean()
        
        # RSI
        delta = data['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        data['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = data['close'].ewm(span=12, adjust=False).mean()
        exp2 = data['close'].ewm(span=26, adjust=False).mean()
        data['macd'] = exp1 - exp2
        
        # Bollinger
        data['boll'] = data['close'].rolling(20).std()
        
        # 填充NaN
        data = data.dropna()
        
        # 特征和目标
        X = data[self.features].values
        y = (data[target_col].shift(-1) > data[target_col]).astype(int)  # 1=涨, 0=跌
        
        # 分割
        split = int(len(X) * 0.8)
        
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]
        
        return X_train, X_test, y_train, y_test
    
    def train(self, X_train, y_train):
        """训练模型"""
        if self.model_type == "lr":
            self._train_lr(X_train, y_train)
        elif self.model_type == "rf":
            self._train_rf(X_train, y_train)
        elif self.model_type == "lstm":
            self._train_lstm(X_train, y_train)
        else:
            print(f"Unknown model type: {self.model_type}")
    
    def _train_lr(self, X, y):
        """线性回归"""
        try:
            from sklearn.linear_model import LinearRegression
            self.model = LinearRegression()
            self.model.fit(X, y)
            print("✅ Linear Regression 训练完成")
        except ImportError:
            print("❌ sklearn 未安装")
    
    def _train_rf(self, X, y):
        """随机森林"""
        try:
            from sklearn.ensemble import RandomForestClassifier
            self.model = RandomForestClassifier(n_estimators=100, max_depth=10)
            self.model.fit(X, y)
            print("✅ Random Forest 训练完成")
        except ImportError:
            print("❌ sklearn 未安装")
    
    def _train_lstm(self, X, y):
        """LSTM (简化版)"""
        try:
            # 需要tensorflow
            import tensorflow as tf
            from tensorflow.keras.models import Sequential
            from tensorflow.keras.layers import LSTM, Dense
            
            # 重塑为 [samples, timesteps, features]
            X = X.reshape((X.shape[0], 1, X.shape[1]))
            
            model = Sequential([
                LSTM(50, activation='relu', input_shape=(1, X.shape[2])),
                Dense(1, activation='sigmoid')
            ])
            
            model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
            model.fit(X, y, epochs=10, batch_size=32, verbose=0)
            
            self.model = model
            print("✅ LSTM 训练完成")
            
        except ImportError:
            print("❌ tensorflow 未安装，使用线性回归替代")
            self.model_type = "lr"
            self._train_lr(X, y)
    
    def predict(self, X) -> np.ndarray:
        """预测"""
        if self.model is None:
            print("❌ 模型未训练")
            return np.zeros(len(X))
        
        if self.model_type == "lstm":
            X = X.reshape((X.shape[0], 1, X.shape[1]))
        
        if self.model_type in ["lr", "rf"]:
            return self.model.predict(X).flatten()
        else:
            return (self.model.predict(X) > 0.5).astype(int).flatten()
    
    def evaluate(self, X_test, y_test) -> Dict:
        """评估模型"""
        if self.model is None:
            return {}
        
        y_pred = self.predict(X_test)
        
        # 准确率
        accuracy = np.mean(y_pred == y_test)
        
        # 简单的预测方向准确率
        return {
            'accuracy': accuracy,
            'predictions': y_pred[:10].tolist(),
            'actuals': y_test[:10].tolist()
        }


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 50)
    print("机器学习价格预测")
    print("=" * 50)
    
    # 生成测试数据
    np.random.seed(42)
    n = 500
    prices = 45000 * np.cumprod(1 + np.random.normal(0.001, 0.03, n))
    
    df = pd.DataFrame({
        'close': prices,
        'volume': np.random.uniform(1000, 10000, n)
    })
    
    # 创建预测器
    predictor = MLPricePredictor("rf")
    
    # 准备数据
    X_train, X_test, y_train, y_test = predictor.prepare_data(df)
    
    print(f"\n📊 数据: 训练 {len(X_train)}, 测试 {len(X_test)}")
    
    # 训练
    predictor.train(X_train, y_train)
    
    # 评估
    print("\n📈 评估结果:")
    result = predictor.evaluate(X_test, y_test)
    print(f"  准确率: {result.get('accuracy', 0):.2%}")
