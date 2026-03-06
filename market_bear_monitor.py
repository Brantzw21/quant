"""
牛熊市监控脚本
支持：A股、港股、美股
触发条件：价格跌破MA200（熊市）/ 突破MA200（牛市）
"""

import os
import json
import requests
import time
from datetime import datetime

# ========== 配置 ==========
DATA_DIR = "/root/.openclaw/workspace/quant_v2/data"
ALERT_CONFIG_FILE = os.path.join(DATA_DIR, "market_alerts.json")

# 主要指数配置
MARKETS = {
    "BTC": {"name": "比特币", "symbol": "BTC-USD", "ma_period": 200},
    "A股_上证指数": {"name": "上证指数", "symbol": "000001.SS", "ma_period": 200},
    "A股_创业板": {"name": "创业板指", "symbol": "399006.SZ", "ma_period": 200},
    "港股_恒生指数": {"name": "恒生指数", "symbol": "^HSI", "ma_period": 200},
    "港股_恒生科技": {"name": "恒生科技指数", "symbol": "3800.HK", "ma_period": 200},
    "美股_标普500": {"name": "S&P 500", "symbol": "^GSPC", "ma_period": 200},
    "美股_纳斯达克": {"name": "纳斯达克", "symbol": "^IXIC", "ma_period": 200},
    "美股_道琼斯": {"name": "道琼斯", "symbol": "^DJI", "ma_period": 200},
    "美股_纳指100": {"name": "纳指100(QQQ)", "symbol": "QQQ", "ma_period": 50},
}

# ========== 函数 ==========
def load_alert_state():
    """加载历史提醒状态"""
    if os.path.exists(ALERT_CONFIG_FILE):
        with open(ALERT_CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_alert_state(state):
    """保存提醒状态"""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(ALERT_CONFIG_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def get_ma200(symbol):
    """获取MA200"""
    for retry in range(3):
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1y"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            resp = requests.get(url, headers=headers, timeout=20)
            if resp.status_code != 200:
                time.sleep(2)
                continue
            data = resp.json()
            
            if 'chart' not in data or not data['chart']['result']:
                return None, None
            
            result = data['chart']['result'][0]
            quotes = result['indicators']['quote'][0]
            closes = [c for c in quotes['close'] if c]
            
            if len(closes) < 200:
                return None, None
            
            current_price = closes[-1]
            ma200 = sum(closes[-200:]) / 200
            
            return current_price, ma200
        except Exception as e:
            if retry < 2:
                time.sleep(2)
                continue
            print(f"获取{symbol}失败: {e}")
            return None, None
    return None, None

def check_market():
    """检查所有市场牛熊状态"""
    results = []
    state = load_alert_state()
    
    for key, info in MARKETS.items():
        symbol = info["symbol"]
        name = info["name"]
        
        current_price, ma200 = get_ma200(symbol)
        
        if current_price is None:
            continue
        
        is_bear = current_price < ma200
        prev_state = state.get(key, {}).get("in_bear", None)
        
        # 状态变化检测
        alert_triggered = None
        if prev_state is None:
            alert_triggered = "init"
        elif is_bear and not prev_state:
            alert_triggered = "enter_bear"
        elif not is_bear and prev_state:
            alert_triggered = "enter_bull"
        
        # 更新状态
        state[key] = {
            "in_bear": is_bear,
            "current_price": current_price,
            "ma200": ma200,
            "last_update": datetime.now().isoformat(),
            "alert_triggered": alert_triggered
        }
        
        results.append({
            "market": key,
            "name": name,
            "price": round(current_price, 2),
            "ma200": round(ma200, 2),
            "is_bear": is_bear,
            "status": "🐻 熊市" if is_bear else "🐮 牛市",
            "alert": alert_triggered
        })
    
    # 保存状态
    save_alert_state(state)
    
    return results

def format_message(results):
    """格式化提醒消息"""
    msg = "📊 **全球市场牛熊监控**\n\n"
    
    alerts = []
    for r in results:
        emoji = "🔴" if r["alert"] in ["enter_bear", "enter_bull"] else "⚪"
        status = f"{emoji} **{r['name']}**: {r['status']}\n"
        status += f"   价格: {r['price']} | MA200: {r['ma200']}\n"
        msg += status
        
        if r["alert"] == "enter_bear":
            alerts.append(f"⚠️ {r['name']} 进入熊市！")
        elif r["alert"] == "enter_bull":
            alerts.append(f"✅ {r['name']} 回到牛市！")
    
    if alerts:
        msg += "\n" + "\n".join(alerts)
    
    return msg

def send_alert(results):
    """发送提醒到用户"""
    alerts = [r for r in results if r["alert"] in ["enter_bear", "enter_bull"]]
    if not alerts:
        return
    
    msg = "📊 **牛熊市提醒**\n\n"
    for r in alerts:
        if r["alert"] == "enter_bear":
            msg += f"⚠️ **{r['name']}** 进入熊市！\n   价格: {r['price']} < MA200: {r['ma200']}\n\n"
        elif r["alert"] == "enter_bull":
            msg += f"✅ **{r['name']}** 回到牛市！\n   价格: {r['price']} > MA200: {r['ma200']}\n\n"
    
    # 调用OpenClaw发送消息
    try:
        import subprocess
        subprocess.run([
            "openclaw", "message", "send",
            "--channel", "feishu",
            "--target", "ou_1f6a9d62f149919c4bd02c330ddcae1d",
            "--message", msg
        ], capture_output=True, timeout=30)
        print(f"✅ 消息已发送: {len(alerts)}个提醒")
    except Exception as e:
        print(f"发送消息失败: {e}")

if __name__ == "__main__":
    print("=" * 50)
    print("🌍 全球市场牛熊监控")
    print("=" * 50)
    
    results = check_market()
    
    for r in results:
        alert_mark = "⚠️ " if r["alert"] in ["enter_bear", "enter_bull"] else "   "
        print(f"{alert_mark}{r['name']}: {r['status']} | {r['price']} vs MA200={r['ma200']}")
    
    # 发送提醒
    send_alert(results)
    
    print("\n" + "=" * 50)
