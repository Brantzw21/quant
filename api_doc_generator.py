#!/usr/bin/env python3
"""
API 文档生成器
自动扫描Python模块生成API文档
"""

import os
import sys
import inspect
import json
from typing import Dict, List, Any
from datetime import datetime


class APIDocGenerator:
    """
    API文档生成器
    
    功能:
    - 扫描Python模块
    - 提取函数、类、参数
    - 生成Markdown文档
    """
    
    def __init__(self, module_dir: str):
        self.module_dir = module_dir
        self.modules = []
    
    def scan_modules(self, pattern: str = "*.py") -> List[str]:
        """扫描模块"""
        import glob
        
        files = glob.glob(os.path.join(self.module_dir, pattern))
        
        # 排除测试和特殊文件
        modules = []
        for f in files:
            basename = os.path.basename(f)
            if not basename.startswith('_') and not basename.startswith('test'):
                modules.append(f)
        
        return modules
    
    def extract_module_info(self, filepath: str) -> Dict:
        """提取模块信息"""
        module_name = os.path.basename(filepath)[:-3]
        
        # 动态导入模块
        sys.path.insert(0, os.path.dirname(filepath))
        
        try:
            module = __import__(module_name)
        except Exception as e:
            print(f"导入失败 {module_name}: {e}")
            return None
        
        info = {
            'name': module_name,
            'file': filepath,
            'classes': [],
            'functions': [],
            'description': inspect.getdoc(module) or ""
        }
        
        # 提取类
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__ == module_name:
                class_info = {
                    'name': name,
                    'description': inspect.getdoc(obj),
                    'methods': []
                }
                
                # 提取方法
                for method_name, method in inspect.getmembers(obj, inspect.isfunction):
                    if not method_name.startswith('_'):
                        class_info['methods'].append({
                            'name': method_name,
                            'description': inspect.getdoc(method),
                            'params': self._extract_params(method)
                        })
                
                info['classes'].append(class_info)
        
        # 提取函数
        for name, obj in inspect.getmembers(module, inspect.isfunction):
            if obj.__module__ == module_name and not name.startswith('_'):
                info['functions'].append({
                    'name': name,
                    'description': inspect.getdoc(obj),
                    'params': self._extract_params(obj)
                })
        
        return info
    
    def _extract_params(self, func) -> List[Dict]:
        """提取函数参数"""
        params = []
        
        try:
            sig = inspect.signature(func)
            
            for name, param in sig.parameters.items():
                p = {
                    'name': name,
                    'type': str(param.annotation) if param.annotation != inspect.Parameter.empty else 'Any',
                    'default': str(param.default) if param.default != inspect.Parameter.empty else None,
                    'kind': str(param.kind)
                }
                params.append(p)
        except:
            pass
        
        return params
    
    def generate_markdown(self, module_info: Dict) -> str:
        """生成Markdown文档"""
        md = []
        
        # 模块标题
        md.append(f"# {module_info['name']}")
        md.append("")
        
        # 描述
        if module_info['description']:
            md.append(module_info['description'])
            md.append("")
        
        # 类
        if module_info['classes']:
            md.append("## Classes")
            md.append("")
            
            for cls in module_info['classes']:
                md.append(f"### {cls['name']}")
                md.append("")
                
                if cls['description']:
                    md.append(cls['description'])
                    md.append("")
                
                # 方法
                if cls['methods']:
                    md.append("**Methods:**")
                    md.append("")
                    
                    for method in cls['methods']:
                        md.append(f"- `{method['name']}()` - {method['description'] or ''}")
                    
                    md.append("")
        
        # 函数
        if module_info['functions']:
            md.append("## Functions")
            md.append("")
            
            for func in module_info['functions']:
                md.append(f"### {func['name']}")
                md.append("")
                
                if func['description']:
                    md.append(func['description'])
                    md.append("")
                
                # 参数
                if func['params']:
                    md.append("**Parameters:**")
                    md.append("")
                    
                    for p in func['params']:
                        default = f" = {p['default']}" if p['default'] else ""
                        md.append(f"- `{p['name']}` ({p['type']}){default}")
                    
                    md.append("")
        
        return "\n".join(md)
    
    def generate_all(self, output_dir: str = None):
        """生成所有模块文档"""
        files = self.scan_modules()
        
        all_docs = []
        
        for filepath in files:
            info = self.extract_module_info(filepath)
            
            if info:
                all_docs.append(info)
                
                # 生成Markdown
                md = self.generate_markdown(info)
                
                if output_dir:
                    output_file = os.path.join(output_dir, f"{info['name']}.md")
                    
                    os.makedirs(output_dir, exist_ok=True)
                    
                    with open(output_file, 'w') as f:
                        f.write(md)
                    
                    print(f"生成: {output_file}")
        
        # 生成索引
        if output_dir:
            self._generate_index(all_docs, output_dir)
        
        return all_docs
    
    def _generate_index(self, modules: List[Dict], output_dir: str):
        """生成索引"""
        md = ["# Quant API Documentation", ""]
        md.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        md.append("")
        
        md.append("## Modules")
        md.append("")
        
        for mod in modules:
            md.append(f"- [{mod['name']}]({mod['name']}.md)")
        
        index_file = os.path.join(output_dir, "README.md")
        
        with open(index_file, 'w') as f:
            f.write("\n".join(md))
        
        print(f"生成索引: {index_file}")


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 50)
    print("API文档生成器")
    print("=" * 50)
    
    # 创建生成器
    module_dir = "/root/.openclaw/workspace/quant/quant"
    output_dir = "/root/.openclaw/workspace/quant/quant/docs/api"
    
    generator = APIDocGenerator(module_dir)
    
    # 扫描模块
    print("\n📂 扫描模块...")
    modules = generator.scan_modules()
    
    print(f"找到 {len(modules)} 个模块:")
    for m in modules[:10]:
        print(f"  - {os.path.basename(m)}")
    
    # 生成文档
    print("\n📝 生成文档...")
    generator.generate_all(output_dir)
    
    print("\n✅ 完成!")
