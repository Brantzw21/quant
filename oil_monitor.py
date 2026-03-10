#!/usr/bin/env python3
"""
油价监控脚本
监控 WTI原油(CL=F) 和 布伦特原油(BZ=F) 的波动
当波动超过阈值时发送飞书提醒
"""

import requests
import json
import os
import time
from datetime import datetime

# 配置
SYMBOLS = {
    'WTI': 'CL=F',      # WTI原油
    'Brent': 'BZ=F',    # 布伦特原油
}
VOLATILE_THRESHOLD = 0.02  # 2%波动阈值
HISTORY_FILE = '/root/.openclaw/workspace/quant/quant/logs/oil_history.json'
LAST_NEWS_FILE = '/root/.openclaw/workspace/quant/quant/logs/oil_last_news.json'

# 飞书群ID (油价监控群) - 用于标识
FEISHU_CHAT_ID = 'oc_370a467ea2acf51e7a1f989ee647b547'

# 飞书Webhook地址 (量化提醒机器人)
FEISHU_WEBHOOK = 'https://open.feishu.cn/open-apis/bot/v2/hook/569b1ffe-4392-4f93-a1a2-c54264461889'

def load_history():
    """加载历史数据"""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_history(data):
    """保存历史数据"""
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def get_oil_price(symbol):
    """获取油价 (使用Yahoo Finance API + 备用)"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    # 尝试多个 Yahoo 端点
    urls = [
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
        f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}",
    ]
    
    for url in urls:
        try:
            resp = requests.get(url, headers=headers, timeout=8)
            if resp.status_code == 429:
                time.sleep(2)
                continue
            data = resp.json()
            
            result = data.get('chart', {}).get('result', [])
            if not result:
                continue
                
            meta = result[0].get('meta', {})
            price = meta.get('regularMarketPrice')
            
            # 获取近5日收盘价
            indicators = result[0].get('indicators', {}).get('quote', [{}])[0]
            closes = indicators.get('close', [])
            closes = [c for c in closes if c is not None]
            
            if price:
                return price, closes
        except Exception as e:
            print(f"获取{symbol}尝试失败: {e}")
            continue
    
    # 备用：从新闻中提取价格
    print(f"无法获取{symbol}价格，将尝试从新闻获取")
    return None, None

def calculate_volatility(closes):
    """计算波动率"""
    if len(closes) < 2:
        return 0, 0
    
    # 日收益率
    returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
    
    # 最大单日波动
    max_day_vol = max(abs(r) for r in returns) if returns else 0
    
    # 周波动 (累计)
    week_vol = abs(closes[-1] - closes[0]) / closes[0] if closes else 0
    
    return max_day_vol, week_vol

def get_volatility_reason(max_day_vol, week_vol):
    """根据波动情况返回可能的原因"""
    reasons = []
    
    if week_vol > 0.08:
        reasons.append("⚡ 周波动剧烈(>8%)，可能因素:")
        reasons.append("  • OPEC+减产/增产决策")
        reasons.append("  • 地缘政治冲突升级")
        reasons.append("  • 全球经济衰退担忧")
        reasons.append("  • 美联储利率政策变化")
    elif week_vol > 0.05:
        reasons.append("⚡ 周波动较大(>5%)，可能因素:")
        reasons.append("  • 库存数据变化")
        reasons.append("  • 产油国声明")
        reasons.append("  • 美元指数波动")
    
    if max_day_vol > 0.03:
        reasons.append("📈 日内剧烈波动(>3%)，可能因素:")
        reasons.append("  • 突发地缘事件")
        reasons.append("  • EIA/API库存报告")
        reasons.append("  • 大资金快速进出")
    
    return "\n".join(reasons) if reasons else "✅ 波动在正常范围内"

def load_last_news():
    """加载上次发送的新闻"""
    if os.path.exists(LAST_NEWS_FILE):
        with open(LAST_NEWS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_last_news(news_titles):
    """保存已发送的新闻标题"""
    with open(LAST_NEWS_FILE, 'w') as f:
        json.dump(news_titles, f)

def send_alert(symbol, price, max_day_vol, week_vol):
    """发送飞书提醒"""
    if not FEISHU_WEBHOOK:
        print("未配置飞书Webhook，跳过提醒")
        return
    
    # 判断波动状态
    status = "⚠️ 异常波动" if max_day_vol > VOLATILE_THRESHOLD or week_vol > VOLATILE_THRESHOLD * 1.5 else "✅ 正常"
    
    # 发送波动提醒（纯文本）
    msg_text = f"⛽ 油价波动提醒 - {symbol}\n" + \
               f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n" + \
               f"💰 当前价格: ${price:.2f}\n" + \
               f"📊 日波动: {max_day_vol*100:.2f}%\n" + \
               f"📊 周波动: {week_vol*100:.2f}%\n" + \
               f"⚠️ 状态: {status}"
    
    msg = {"msg_type": "text", "content": {"text": msg_text}}
    requests.post(FEISHU_WEBHOOK, json=msg, timeout=10)
    print(f"已发送{symbol}波动提醒到飞书")
    
    # 如果波动异常，检查是否有新新闻
    if max_day_vol > VOLATILE_THRESHOLD or week_vol > VOLATILE_THRESHOLD * 1.5:
        news = get_oil_news()
        if news:
            last_news = load_last_news()
            current_titles = [n[1] for n in news]  # 英文标题作为去重依据
            
            # 只发送新新闻
            new_news = [n for n in news if n[1] not in last_news]
            
            if new_news:
                # 构建飞书富文本消息 (post) - 每条新闻一行
                content = [
                    [{"tag": "text", "text": f"⛽ 油价最新消息 - {datetime.now().strftime('%Y-%m-%d')}"}]
                ]
                
                for cn_title, en_title, link in new_news[:5]:
                    # 每条新闻作为一行：英文标题 + 中文翻译 + 链接
                    content.append([
                        {"tag": "text", "text": f"📰 {en_title[:70]}\n{cn_title}\n🔗 {link}"}
                    ])
                
                news_msg = {
                    "msg_type": "post",
                    "content": {
                        "post": {
                            "zh_cn": {
                                "title": "",
                                "content": content
                            }
                        }
                    }
                }
                requests.post(FEISHU_WEBHOOK, json=news_msg, timeout=10)
                print(f"已发送{symbol}新新闻到飞书")
                
                # 更新已发送的新闻列表
                save_last_news(current_titles)

def translate_title(title):
    """将英文标题翻译成中文"""
    # 按长度降序排列，优先匹配长词
    translations = [
        # 油价相关
        ('Oil prices', '油价'), ('oil prices', '油价'), ('Crude oil', '原油'), ('crude oil', '原油'),
        ('Saudi Arabia', '沙特阿拉伯'), ('Gulf states', '海湾国家'),
        ('Brent', '布伦特原油'), ('WTI', 'WTI原油'),
        ('per barrel', '每桶'), ('a barrel', '一桶'), ('barrels', '桶'),
        ('spare capacity', '备用产能'), ('strategic reserve', '战略储备'),
        ('cash crunch', '资金紧张'), ('Middle East', '中东'),
        ('Strait of Hormuz', '霍尔木兹海峡'),
        
        # 涨跌
        ('rises above', '突破'), ('surges above', '飙升突破'),
        ('surges', '飙升'), ('surge', '飙升'), ('spike', '暴涨'), ('jumps', '大涨'),
        ('soars', '飙涨'), ('soared', '飙升'), ('falls', '下跌'), ('drops', '下降'),
        ('slips', '下滑'), ('plunges', '暴跌'), ('plunge', '暴跌'), ('tumbles', '大跌'),
        ('slumps', '暴跌'), ('rises', '上涨'), ('gains', '上涨'), ('climbs', '攀升'),
        ('rally', '反弹'), ('rebound', '反弹'),
        
        # OPEC
        ('OPEC+', 'OPEC+'), ('OPEC', 'OPEC+'), ('Opec', 'OPEC+'),
        
        # 产油国
        ('Saudi', '沙特'), ('Russia', '俄罗斯'), ('Iraq', '伊拉克'), ('Iran', '伊朗'),
        ('UAE', '阿联酋'), ('Kuwait', '科威特'), ('Gulf', '海湾'),
        
        # 产量
        ('production', '产量'), ('output', '产量'), ('supply', '供应'), ('exports', '出口'),
        ('cut back', '减少'), ('cut', '减产'), ('cuts', '减产'),
        ('reduce', '削减'), ('reduction', '减少'), ('increase', '增产'),
        ('boost', '增加'), ('raise', '提高'),
        
        # 地缘
        ('war', '战争'), ('conflict', '冲突'), ('attack', '袭击'), ('strike', '打击'),
        ('tensions', '紧张局势'), ('threats', '威胁'), ('fear', '担忧'), ('risk', '风险'),
        ('Hormuz', '霍尔木兹海峡'), ('Israel', '以色列'), ('Palestine', '巴勒斯坦'),
        ('Ukraine', '乌克兰'),
        
        # 库存
        ('Inventory', '库存'), ('stocks', '库存'), ('reserves', '储备'),
        
        # G7/政府
        ('G7', 'G7国家'), ('US', '美国'), ('America', '美国'), ('China', '中国'),
        ('India', '印度'), ('reserve', '储备'), ('emergency', '紧急'),
        
        # 市场
        ('market', '市场'), ('markets', '市场'), ('global', '全球'), ('world', '世界'),
        ('trading', '交易'), ('traders', '交易员'), ('investors', '投资者'),
        ('producer', '产油国'), ('consumer', '消费国'),
        
        # 价格
        ('price', '价格'), ('prices', '价格'), ('cost', '成本'), ('value', '价值'),
        ('high', '高位'), ('highs', '高位'), ('low', '低位'), ('lows', '低位'),
        ('level', '水平'), ('peak', '峰值'), ('record', '纪录'),
        
        # 其他
        ('decision', '决策'), ('agreement', '协议'), ('deal', '协议'),
        ('chart', '图表'), ('data', '数据'), ('report', '报告'), ('news', '新闻'),
        ('despite', '尽管'), ('nearly', '接近'), ('touched', '触及'),
        ('above', '上'), ('below', '下'),
        
        # 清理残留
        ('pushing down', '压低'), ('pushing', '压制'), ('push', '压'),
        ('pulling', '拉'), ('pull', '拉'),
        ('Oil', '油价'), ('oil', '油价'),
        ('Prices', '价格'), ('prices', '价格'),
        ('pushing down', ''), ('pushing', ''), ('down', ''),
        ('despite', ''), ('cash crunch', '资金紧张'),
        ('Is ', ''), ('is ', ''), (' Is', ''), (' is', ''),
        ('Pushing', ''), ('Down', ''), ('Despite', ''),
        ('Cash', ''), ('Crunch', ''),
    ]
    
    translated = title
    for en, cn in translations:
        translated = translated.replace(en, cn)
    
    # 清理单字母和常见词
    for w in [' as ', ' at ', ' in ', ' is ', ' are ', ' was ', ' were ', ' the ', ' a ', ' an ', ' to ', ' of ', ' on ', ' and ', ' or ', ' but ', ' for ', ' with ', ' by ']:
        translated = translated.replace(w, ' ')
    
    # 清理多余空格
    import re
    translated = re.sub(r'\s+', ' ', translated).strip()
    
    return translated

def get_oil_news():
    """获取油价新闻（英文原文+中文总结）"""
    try:
        import xml.etree.ElementTree as ET
        
        # 英文搜索 - 更全面
        queries = [
            "oil prices OPEC crude",
            "crude oil Iran conflict",
            "oil market G7 reserve"
        ]
        
        news = []
        seen_titles = set()
        
        for query in queries:
            try:
                url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
                r = requests.get(url, timeout=10)
                root = ET.fromstring(r.text)
                
                for item in root.findall('.//item')[:3]:
                    title = item.find('title').text
                    link = item.find('link').text
                    if title and title not in seen_titles:
                        seen_titles.add(title)
                        # 翻译成中文
                        cn_title = translate_title(title)
                        news.append((cn_title, title, link))  # (中文总结, 英文原文, 链接)
            except Exception as e:
                print(f"搜索{query}失败: {e}")
                continue
            
            if len(news) >= 3:
                break
        
        return news[:3]
    except Exception as e:
        print(f"获取新闻失败: {e}")
        return []

def send_daily_news():
    """发送每日油价新闻"""
    if not FEISHU_WEBHOOK:
        return
    
    news = get_oil_news()
    if not news:
        return
    
    # 构建飞书富文本消息 (post) - 每条新闻一行
    content = [
        [{"tag": "text", "text": f"⛽ 油价最新消息 - {datetime.now().strftime('%Y-%m-%d')}"}]
    ]
    
    for cn_title, en_title, link in news[:5]:
        content.append([
            {"tag": "text", "text": f"📰 {en_title[:70]}\n{cn_title}\n🔗 {link}"}
        ])
    
    msg = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": "",
                    "content": content
                }
            }
        }
    }
    requests.post(FEISHU_WEBHOOK, json=msg, timeout=15)
    print("已发送每日新闻到飞书")

def main():
    print(f"[{datetime.now()}] 油价监控启动...")
    
    history = load_history()
    alerts = []
    has_price = False
    
    for name, symbol in SYMBOLS.items():
        price, closes = get_oil_price(symbol)
        
        if price is None:
            print(f"{name}: 获取数据失败")
            continue
        
        has_price = True
        max_day_vol, week_vol = calculate_volatility(closes)
        
        # 保存历史
        history[symbol] = {
            'price': price,
            'max_day_vol': max_day_vol,
            'week_vol': week_vol,
            'closes': closes,
            'updated': datetime.now().isoformat()
        }
        
        print(f"{name}: ${price:.2f}, 日波动 {max_day_vol*100:.2f}%, 周波动 {week_vol*100:.2f}%")
        
        # 检查是否超过阈值
        if max_day_vol > VOLATILE_THRESHOLD or week_vol > VOLATILE_THRESHOLD * 1.5:
            alerts.append((name, price, max_day_vol, week_vol))
    
    save_history(history)
    
    # 发送价格波动提醒
    for name, price, max_day_vol, week_vol in alerts:
        send_alert(name, price, max_day_vol, week_vol)
    
    # 即使没有价格数据，也发送新闻（如果有重大新闻）
    if not has_price or not alerts:
        news = get_oil_news()
        if news:
            # 检查是否有重要新闻需要发送
            important_keywords = ['war', 'conflict', 'surge', 'spike', 'OPEC', 'crude', 'emergency', 'Iran', 'G7']
            important_news = []
            for n in news:
                cn_title, en_title, link = n
                if any(kw.lower() in en_title.lower() for kw in important_keywords):
                    important_news.append(n)
            
            # 如果有重要新闻，即使没有价格也发送
            if important_news and FEISHU_WEBHOOK:
                content = [
                    [{"tag": "text", "text": f"📰 油价重要新闻 - {datetime.now().strftime('%Y-%m-%d')}"}]
                ]
                
                for cn_title, en_title, link in important_news[:5]:
                    content.append([
                        {"tag": "text", "text": f"📰 {en_title[:70]}\n{cn_title}\n🔗 {link}"}
                    ])
                
                msg = {
                    "msg_type": "post",
                    "content": {
                        "post": {
                            "zh_cn": {
                                "title": "",
                                "content": content
                            }
                        }
                    }
                }
                try:
                    requests.post(FEISHU_WEBHOOK, json=msg, timeout=10)
                    print("已发送重要新闻到飞书")
                except:
                    pass
    
    if not alerts:
        print("无异常波动")
    
    print(f"[{datetime.now()}] 监控完成")

if __name__ == '__main__':
    main()
