#!/usr/bin/env python3
"""
统一配置中心
YAML配置管理、环境变量、配置验证
"""

import os
import sys
import yaml
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Config:
    """配置基类"""
    # 交易配置
    SYMBOL: str = "BTCUSDT"
    INTERVAL: str = "4h"
    INITIAL_CAPITAL: float = 10000
    
    # API配置
    API_KEY: str = ""
    SECRET_KEY: str = ""
    TESTNET: bool = False
    
    # 风控配置
    STOP_LOSS: float = 0.05
    TAKE_PROFIT: float = 0.10
    MAX_POSITION: float = 0.95
    
    # 策略参数
    RSI_PERIOD: int = 14
    RSI_OVERBTOUGHT: int = 70
    RSI_OVERSOLD: int = 30


class ConfigManager:
    """
    配置管理器
    
    功能:
    - YAML配置加载
    - 环境变量覆盖
    - 配置验证
    - 热重载
    """
    
    def __init__(self, config_file: str = None):
        self.config_file = config_file
        self.config = Config()
        self.env_prefix = "QUANT_"
        
        # 加载
        if config_file:
            self.load(config_file)
    
    def load(self, config_file: str):
        """加载配置文件"""
        if not os.path.exists(config_file):
            print(f"⚠️ 配置文件不存在: {config_file}")
            return
        
        with open(config_file, 'r') as f:
            if config_file.endswith('.yaml') or config_file.endswith('.yml'):
                data = yaml.safe_load(f)
            elif config_file.endswith('.json'):
                data = json.load(f)
            else:
                print(f"❌ 不支持的配置文件格式")
                return
        
        # 合并配置
        self._merge_config(data)
        
        # 环境变量覆盖
        self._apply_env_vars()
        
        print(f"✅ 配置已加载: {config_file}")
    
    def _merge_config(self, data: Dict):
        """合并配置"""
        for key, value in data.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
            else:
                print(f"⚠️ 未知配置项: {key}")
    
    def _apply_env_vars(self):
        """应用环境变量"""
        for key in dir(self.config):
            if key.startswith('_'):
                continue
            
            env_key = f"{self.env_prefix}{key}"
            env_value = os.environ.get(env_key)
            
            if env_value is not None:
                # 类型转换
                current_type = type(getattr(self.config, key))
                
                try:
                    if current_type == bool:
                        value = env_value.lower() in ('true', '1', 'yes')
                    elif current_type == int:
                        value = int(env_value)
                    elif current_type == float:
                        value = float(env_value)
                    else:
                        value = env_value
                    
                    setattr(self.config, key, value)
                    print(f"  📌 环境变量覆盖: {key} = {value}")
                    
                except:
                    print(f"❌ 环境变量类型转换失败: {key}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置"""
        return getattr(self.config, key, default)
    
    def set(self, key: str, value: Any):
        """设置配置"""
        if hasattr(self.config, key):
            setattr(self.config, key, value)
        else:
            print(f"❌ 未知配置项: {key}")
    
    def save(self, config_file: str = None):
        """保存配置"""
        config_file = config_file or self.config_file
        
        if not config_file:
            print("❌ 未指定配置文件")
            return
        
        # 导出为dict
        data = {k: v for k, v in self.config.__dict__.items() 
                if not k.startswith('_')}
        
        # 保存
        with open(config_file, 'w') as f:
            if config_file.endswith('.yaml') or config_file.endswith('.yml'):
                yaml.dump(data, f, default_flow_style=False)
            elif config_file.endswith('.json'):
                json.dump(data, f, indent=2)
        
        print(f"✅ 配置已保存: {config_file}")
    
    def validate(self) -> Dict:
        """验证配置"""
        errors = []
        warnings = []
        
        # API检查
        if not self.config.API_KEY:
            errors.append("API_KEY 未设置")
        
        # 数值检查
        if self.config.STOP_LOSS < 0 or self.config.STOP_LOSS > 1:
            errors.append("STOP_LOSS 必须在 0-1 之间")
        
        if self.config.TAKE_PROFIT < 0 or self.config.TAKE_PROFIT > 1:
            errors.append("TAKE_PROFIT 必须在 0-1 之间")
        
        if self.config.MAX_POSITION < 0 or self.config.MAX_POSITION > 1:
            errors.append("MAX_POSITION 必须在 0-1 之间")
        
        # 警告
        if self.config.TESTNET:
            warnings.append("当前运行在测试网模式")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {k: v for k, v in self.config.__dict__.items() 
                if not k.startswith('_')}


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 50)
    print("统一配置中心")
    print("=" * 50)
    
    # 创建配置
    config_file = "/root/.openclaw/workspace/quant/quant/config/settings.yaml"
    
    # 检查是否存在
    if os.path.exists(config_file):
        manager = ConfigManager(config_file)
        
        # 验证
        result = manager.validate()
        print(f"\n📋 验证结果:")
        print(f"  有效: {result['valid']}")
        print(f"  错误: {result['errors']}")
        print(f"  警告: {result['warnings']}")
        
        # 打印配置
        print(f"\n📊 当前配置:")
        for key, value in manager.to_dict().items():
            print(f"  {key}: {value}")
    else:
        # 创建默认配置
        print(f"创建默认配置...")
        manager = ConfigManager()
        
        # 保存
        manager.save(config_file)
        print(f"✅ 已创建: {config_file}")
