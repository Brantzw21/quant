"""
数据备份与导出模块
- 定期备份市场数据
- 导出为CSV/JSON
- 数据统计
"""

import os
import json
import shutil
import time
import pandas as pd
from datetime import datetime


class DataBackup:
    """数据备份管理"""
    
    def __init__(self, data_dir='data/market'):
        self.data_dir = data_dir
        self.backup_dir = 'data/backup'
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def backup_all(self):
        """备份所有市场数据"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(self.backup_dir, f'backup_{timestamp}')
        os.makedirs(backup_path, exist_ok=True)
        
        count = 0
        if os.path.exists(self.data_dir):
            for f in os.listdir(self.data_dir):
                if f.endswith('.json'):
                    src = os.path.join(self.data_dir, f)
                    dst = os.path.join(backup_path, f)
                    shutil.copy2(src, dst)
                    count += 1
        
        # 保存备份记录
        manifest = {
            'timestamp': timestamp,
            'files': count,
            'path': backup_path
        }
        with open(os.path.join(self.backup_dir, 'manifest.json'), 'w') as f:
            json.dump(manifest, f, indent=2)
        
        print(f"✅ 备份完成: {count} 个文件 -> {backup_path}")
        return backup_path
    
    def restore_latest(self):
        """恢复最新备份"""
        manifest_path = os.path.join(self.backup_dir, 'manifest.json')
        if not os.path.exists(manifest_path):
            print("❌ 无备份记录")
            return
        
        with open(manifest_path) as f:
            manifest = json.load(f)
        
        backup_path = manifest['path']
        count = 0
        for f in os.listdir(backup_path):
            if f.endswith('.json'):
                src = os.path.join(backup_path, f)
                dst = os.path.join(self.data_dir, f)
                shutil.copy2(src, dst)
                count += 1
        
        print(f"✅ 恢复完成: {count} 个文件")
        return count
    
    def list_backups(self):
        """列出所有备份"""
        if not os.path.exists(self.backup_dir):
            return []
        
        backups = []
        for d in os.listdir(self.backup_dir):
            path = os.path.join(self.backup_dir, d)
            if os.path.isdir(path):
                files = [f for f in os.listdir(path) if f.endswith('.json')]
                backups.append({
                    'name': d,
                    'files': len(files),
                    'path': path
                })
        
        return sorted(backups, key=lambda x: x['name'], reverse=True)


def export_to_csv(symbol='BTC', timeframe='1h', output_dir='data/exports'):
    """导出数据为CSV"""
    from data_manager import get_data_manager
    
    dm = get_data_manager()
    data = dm.get_btc_klines(timeframe, limit=1000)
    
    if not data:
        print("无数据")
        return
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 转换为DataFrame
    df = pd.DataFrame(data)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # 导出
    filename = f"{symbol.replace('/', '_')}_{timeframe}.csv"
    filepath = os.path.join(output_dir, filename)
    df.to_csv(filepath, index=False)
    
    print(f"✅ 导出完成: {filepath}")
    return filepath


def get_data_stats():
    """获取数据统计"""
    from data_manager import DATA_DIR
    
    stats = {
        'markets': {},
        'total_files': 0,
        'total_size': 0
    }
    
    if not os.path.exists(DATA_DIR):
        return stats
    
    for f in os.listdir(DATA_DIR):
        if f.endswith('.json'):
            path = os.path.join(DATA_DIR, f)
            size = os.path.getsize(path)
            stats['total_files'] += 1
            stats['total_size'] += size
            
            # 解析文件名
            name = f.replace('.json', '')
            stats['markets'][name] = {
                'size': size,
                'updated': datetime.fromtimestamp(os.path.getmtime(path)).isoformat()
            }
    
    stats['total_size_mb'] = round(stats['total_size'] / 1024 / 1024, 2)
    return stats


if __name__ == '__main__':
    import sys
    
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'stats'
    
    if cmd == 'backup':
        backup = DataBackup()
        backup.backup_all()
    elif cmd == 'restore':
        backup = DataBackup()
        backup.restore_latest()
    elif cmd == 'list':
        backup = DataBackup()
        for b in backup.list_backups():
            print(f"{b['name']}: {b['files']} files")
    elif cmd == 'stats':
        stats = get_data_stats()
        print("📊 数据统计:")
        print(f"  文件数: {stats['total_files']}")
        print(f"  总大小: {stats['total_size_mb']} MB")
    elif cmd == 'export':
        export_to_csv()
