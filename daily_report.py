#!/usr/bin/env python3
"""
每日开发进度汇报 + GitHub同步
每天18:00自动执行
"""

import os
import subprocess
import json
from datetime import datetime
from pathlib import Path

# 配置
WORKSPACE = "/root/.openclaw/workspace"
QUANT_V2 = f"{WORKSPACE}/quant/v2"
GIT_REPO = "Brantzw21/quant"
NOTIFY_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/569b1ffe-4392-4f93-a1a2-c54264461889"

def run_cmd(cmd, cwd=None):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return result.returncode, result.stdout, result.stderr

def get_git_status(repo_path):
    """获取git变更状态"""
    os.chdir(repo_path)
    
    # 检查远程
    _, remote_out, _ = run_cmd("git remote -v")
    if not remote_out.strip():
        return None, "未配置远程仓库"
    
    # 获取状态
    code, status_out, _ = run_cmd("git status --porcelain")
    if code != 0:
        return None, "git status失败"
    
    # 获取最近commit
    _, last_commit, _ = run_cmd("git log -1 --oneline")
    
    # 获取diff统计
    _, diff_stat, _ = run_cmd("git diff --stat")
    
    return {
        "changed_files": [l for l in status_out.strip().split('\n') if l],
        "last_commit": last_commit.strip() or "无",
        "diff_stat": diff_stat.strip() or "无变更"
    }, None

def git_commit_push(repo_path):
    """自动提交推送"""
    os.chdir(repo_path)
    
    # Add all
    run_cmd("git add -A")
    
    # Check if there are changes
    code, status, _ = run_cmd("git status --porcelain")
    if not status.strip():
        return False, "没有变更"
    
    # Commit with date
    date = datetime.now().strftime("%Y-%m-%d")
    msg = f"update: 日常开发 {date}"
    run_cmd(f'git commit -m "{msg}"')
    
    # Push
    code, out, err = run_cmd("git push origin main 2>&1")
    if code != 0:
        return False, err
    
    return True, msg

def send_notify(message):
    """发送飞书通知"""
    import requests
    try:
        requests.post(NOTIFY_WEBHOOK, json={
            "msg_type": "text",
            "content": {"text": message}
        }, timeout=10)
    except:
        pass

def main():
    print(f"[{datetime.now()}] 开始每日汇报...")
    
    # 获取v2状态
    status_v2, err = get_git_status(QUANT_V2)
    
    msg = f"""
📊 Quant项目每日汇报 - {datetime.now().strftime('%Y-%m-%d')}

【quant_v2 状态】
"""
    
    if err:
        msg += f"❌ {err}\n"
    else:
        msg += f"📌 最近提交: {status_v2['last_commit']}\n"
        
        if status_v2['changed_files']:
            msg += f"\n📝 未提交变更 ({len(status_v2['changed_files'])}个文件):\n"
            for f in status_v2['changed_files'][:10]:
                msg += f"  {f}\n"
            if len(status_v2['changed_files']) > 10:
                msg += f"  ... 等共{len(status_v2['changed_files'])}个\n"
            
            # 自动提交
            success, push_msg = git_commit_push(QUANT_V2)
            if success:
                msg += f"\n✅ 已推送到GitHub: {push_msg}"
            else:
                msg += f"\n⚠️ 推送失败: {push_msg}"
        else:
            msg += "\n✅ 无变更，工作区干净"
    
    # 策略运行状态
    msg += f"""

【策略状态】
"""
    log_file = f"{QUANT_V2}/logs/strategy.log"
    if os.path.exists(log_file):
        with open(log_file) as f:
            lines = f.readlines()
            if lines:
                last_line = lines[-1].strip()
                msg += f"最后运行: {last_line[:80]}..."
    
    print(msg)
    send_notify(msg)
    print("✅ 汇报完成")

if __name__ == "__main__":
    main()
