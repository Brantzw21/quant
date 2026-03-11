#!/usr/bin/env python3
"""
通知系统增强
支持多渠道: 飞书/邮件/Telegram/短信
"""

import os
import sys
import json
import requests
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum


class NotificationType(Enum):
    """通知类型"""
    SIGNAL = "signal"       # 交易信号
    TRADE = "trade"        # 成交
    RISK = "risk"          # 风控告警
    SYSTEM = "system"       # 系统
    REPORT = "report"       # 报告


class Channel(Enum):
    """通知渠道"""
    FEISHU = "feishu"
    EMAIL = "email"
    TELEGRAM = "telegram"
    SMS = "sms"
    DINGTALK = "dingtalk"


@dataclass
class NotificationConfig:
    """通知配置"""
    enabled: bool = True
    channels: List[str] = None
    
    # 飞书
    feishu_webhook: str = ""
    feishu_user_id: str = ""
    
    # 邮件
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_to: str = ""
    
    # Telegram
    telegram_token: str = ""
    telegram_chat_id: str = ""
    
    # 短信
    sms_provider: str = ""  # aliyun, twilio
    sms_key: str = ""
    sms_secret: str = ""
    sms_phone: str = ""
    
    # 钉钉
    dingtalk_webhook: str = ""
    
    def __post_init__(self):
        if self.channels is None:
            self.channels = ["feishu"]


class NotificationManager:
    """
    通知管理器
    
    支持多渠道发送
    """
    
    def __init__(self, config: NotificationConfig = None):
        self.config = config or NotificationConfig()
        self.history: List[Dict] = []
    
    def send(self, 
             title: str, 
             content: str, 
             notification_type: NotificationType = NotificationType.SYSTEM,
             channels: List[Channel] = None) -> Dict:
        """
        发送通知
        
        Args:
            title: 标题
            content: 内容
            notification_type: 类型
            channels: 指定渠道
        
        Returns:
            发送结果
        """
        if not self.config.enabled:
            return {'status': 'disabled'}
        
        channels = channels or [Channel(c) for c in self.config.channels]
        
        results = {}
        
        for channel in channels:
            try:
                if channel == Channel.FEISHU:
                    results['feishu'] = self._send_feishu(title, content)
                elif channel == Channel.EMAIL:
                    results['email'] = self._send_email(title, content)
                elif channel == Channel.TELEGRAM:
                    results['telegram'] = self._send_telegram(title, content)
                elif channel == Channel.DINGTALK:
                    results['dingtalk'] = self._send_dingtalk(title, content)
            except Exception as e:
                results[str(channel)] = {'status': 'error', 'message': str(e)}
        
        # 记录历史
        self.history.append({
            'time': datetime.now().isoformat(),
            'title': title,
            'type': notification_type.value,
            'results': results
        })
        
        return results
    
    def _send_feishu(self, title: str, content: str) -> Dict:
        """发送飞书消息"""
        if not self.config.feishu_webhook:
            return {'status': 'not_configured'}
        
        # 消息类型
        msg_type = "text"
        
        # 构建消息内容
        text_content = f"{title}\n{content}"
        
        payload = {
            "msg_type": msg_type,
            "content": {
                "text": text_content
            }
        }
        
        # 添加提及
        if self.config.feishu_user_id:
            payload["content"]["text"] = f"<at id=all></at>\n{text_content}"
        
        # 发送
        resp = requests.post(
            self.config.feishu_webhook,
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        return {'status': 'ok' if resp.status_code == 200 else 'error', 'code': resp.status_code}
    
    def _send_email(self, title: str, content: str) -> Dict:
        """发送邮件"""
        if not self.config.smtp_host:
            return {'status': 'not_configured'}
        
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.header import Header
            
            # 构建邮件
            msg = MIMEText(content, 'html', 'utf-8')
            msg['Subject'] = Header(title, 'utf-8')
            msg['From'] = self.config.smtp_user
            msg['To'] = self.config.email_to
            
            # 发送
            server = smtplib.SMTP(self.config.smtp_host, self.config.smtp_port)
            server.starttls()
            server.login(self.config.smtp_user, self.config.smtp_password)
            server.sendmail(self.config.smtp_user, self.config.email_to, msg.as_string())
            server.quit()
            
            return {'status': 'ok'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def _send_telegram(self, title: str, content: str) -> Dict:
        """发送Telegram"""
        if not self.config.telegram_token:
            return {'status': 'not_configured'}
        
        url = f"https://api.telegram.org/bot{self.config.telegram_token}/sendMessage"
        
        payload = {
            'chat_id': self.config.telegram_chat_id,
            'text': f"*{title}*\n\n{content}",
            'parse_mode': 'Markdown'
        }
        
        resp = requests.post(url, json=payload)
        
        return {'status': 'ok' if resp.status_code == 200 else 'error'}
    
    def _send_dingtalk(self, title: str, content: str) -> Dict:
        """发送钉钉"""
        if not self.config.dingtalk_webhook:
            return {'status': 'not_configured'}
        
        payload = {
            'msgtype': 'text',
            'text': {
                'content': f"{title}\n{content}"
            }
        }
        
        resp = requests.post(
            self.config.dingtalk_webhook,
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        return {'status': 'ok' if resp.status_code == 200 else 'error'}
    
    # ===== 便捷方法 =====
    
    def notify_signal(self, symbol: str, signal: str, confidence: float, price: float):
        """通知信号"""
        emoji = {"BUY": "🟢", "SELL": "🔴", "HOLD": "⏸️"}.get(signal, "❓")
        
        content = f"""
{emoji} 信号: {signal}
📊 品种: {symbol}
💰 价格: {price}
📈 置信度: {confidence:.0%}
🕐 时间: {datetime.now().strftime('%H:%M:%S')}
"""
        
        return self.send(
            f"交易信号 - {symbol}",
            content,
            NotificationType.SIGNAL
        )
    
    def notify_trade(self, action: str, symbol: str, quantity: float, price: float, order_id: str = ""):
        """通知成交"""
        emoji = "🟢" if action == "BUY" else "🔴"
        
        content = f"""
{emoji} {action} 已成交
📊 品种: {symbol}
🔢 数量: {quantity}
💰 价格: {price}
🆔 订单ID: {order_id}
🕐 时间: {datetime.now().strftime('%H:%M:%S')}
"""
        
        return self.send(
            f"成交通知 - {action} {symbol}",
            content,
            NotificationType.TRADE
        )
    
    def notify_risk(self, level: str, message: str):
        """通知风控"""
        emoji = {"low": "🟢", "medium": "🟡", "high": "🔴", "critical": "🚨"}.get(level, "❓")
        
        content = f"""
{emoji} 风控告警 - {level.upper()}
📝 原因: {message}
🕐 时间: {datetime.now().strftime('%H:%M:%S')}
"""
        
        return self.send(
            "风控告警",
            content,
            NotificationType.RISK
        )
    
    def notify_report(self, report_type: str, content: str):
        """通知报告"""
        return self.send(
            f"报告 - {report_type}",
            content,
            NotificationType.REPORT
        )
    
    def get_history(self, n: int = 10) -> List[Dict]:
        """获取历史通知"""
        return self.history[-n:]


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 配置
    config = NotificationConfig(
        enabled=True,
        channels=["feishu"],
        feishu_webhook="https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
    )
    
    # 创建管理器
    nm = NotificationManager(config)
    
    # 发送通知
    print("发送信号通知...")
    result = nm.notify_signal("BTCUSDT", "BUY", 0.75, 50000)
    print(result)
    
    print("\n发送风控通知...")
    result = nm.notify_risk("high", "回撤超过10%")
    print(result)
