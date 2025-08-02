#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask应用启动脚本
"""

import os
import sys
from pathlib import Path

def check_dependencies():
    """检查必要的依赖"""
    try:
        import flask
        import ffmpeg
        import qrcode
        print("✅ 所有依赖检查通过")
        return True
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("请运行: pip install -r requirements.txt")
        return False

def check_music_files():
    """检查音乐文件"""
    music_files = ["jiggy boogy.mp3", "bgm_mbz.mp3"]
    missing_files = []
    
    for music_file in music_files:
        if not os.path.exists(music_file):
            missing_files.append(music_file)
    
    if missing_files:
        print(f"⚠️ 缺少音乐文件: {', '.join(missing_files)}")
        print("某些功能可能无法正常工作")
    else:
        print("✅ 音乐文件检查通过")

def main():
    """主函数"""
    print("🎬 视频处理工具 - Flask版本")
    print("=" * 40)
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 检查音乐文件
    check_music_files()
    
    # 创建必要的目录
    for dir_name in ["static", "output"]:
        Path(dir_name).mkdir(exist_ok=True)
    
    print("\n🚀 启动Flask应用...")
    print("访问地址: http://localhost:5000")
    print("按 Ctrl+C 停止服务")
    print("=" * 40)
    
    # 导入并启动应用
    try:
        from app import app
        app.run(host='127.0.0.1', port=5000, debug=True)
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()