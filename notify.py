"""
飞书消息通知模块
"""
import requests
import json

# 飞书Webhook地址
WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/569b1ffe-4392-4f93-a1a2-c54264461889"

def send_message(text: str, webhook: str = None) -> bool:
    """发送飞书消息"""
    url = webhook or WEBHOOK_URL
    if not url:
        print("⚠️ 未配置飞书Webhook")
        return False
    
    try:
        response = requests.post(url, json={
            "msg_type": "text",
            "content": {"text": text}
        }, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"发送失败: {e}")
        return False

def notify_bear_market(is_bear: bool, price: float, ma200: float):
    """熊市提醒"""
    if is_bear:
        msg = f"⚠️ 警报！BTC可能进入熊市\n💰 价格: ${price:.0f}\n📊 MA200: ${ma200:.0f}"
    else:
        msg = f"✅ 解锁！BTC回到牛市\n💰 价格: ${price:.0f}"
    
    send_message(msg)

def notify_weekly_report(report_data: dict):
    """周报提醒"""
    msg = f"""
📊 量化周报 - {report_data.get('date', '')}
===
💰 权益: ${report_data.get('equity', 0):.2f}
📈 总盈亏: ${report_data.get('total_pnl', 0):.2f}
📅 本周: ${report_data.get('week_pnl', 0):.2f}
📝 持仓: {report_data.get('position', 0)} BTC
"""
    send_message(msg)

def notify_signal_change(new_signal: dict, old_signal: str = None):
    """信号变化推送"""
    signal = new_signal.get('signal', 'N/A')
    confidence = new_signal.get('confidence', 0)
    reason = new_signal.get('reason', '')
    price = new_signal.get('indicators', {}).get('4h', {}).get('price', 0)
    
    # 信号emoji
    emoji = {
        'BUY': '🟢',
        'SELL': '🔴',
        'HOLD': '⏸️',
        'SHORT': '📉',
        'COVER': '📈'
    }.get(signal, '❓')
    
    msg = f"""
{emoji} 策略信号变化

📌 信号: {signal} ({confidence*100:.0f}%)
💰 价格: ${price:,.2f}
📝 原因: {reason}
"""
    
    # 只有信号变化才推送
    if signal != old_signal:
        send_message(msg)
        return True
    return False

if __name__ == "__main__":
    # 测试
    send_message("🧪 量化系统测试消息")
