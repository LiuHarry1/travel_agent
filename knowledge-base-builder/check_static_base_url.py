"""检查 static_base_url 配置是否正确"""
import os
from pathlib import Path

# 检查 .env 文件
env_file = Path(".env")
if env_file.exists():
    print("📄 找到 .env 文件")
    with open(env_file, 'r', encoding='utf-8') as f:
        content = f.read()
        if 'STATIC_BASE_URL' in content:
            print("✅ .env 文件中包含 STATIC_BASE_URL")
            for line in content.split('\n'):
                if 'STATIC_BASE_URL' in line and not line.strip().startswith('#'):
                    print(f"   配置行: {line.strip()}")
        else:
            print("❌ .env 文件中没有找到 STATIC_BASE_URL")
            print("   请添加: STATIC_BASE_URL=http://localhost:8001")
else:
    print("⚠️  未找到 .env 文件")
    print("   请在 knowledge-base-builder 目录下创建 .env 文件")
    print("   添加: STATIC_BASE_URL=http://localhost:8001")

# 检查环境变量
env_value = os.getenv("STATIC_BASE_URL")
if env_value:
    print(f"\n✅ 环境变量 STATIC_BASE_URL: {env_value}")
else:
    print("\n❌ 环境变量 STATIC_BASE_URL 未设置")

# 检查配置读取
try:
    from config.settings import get_settings
    settings = get_settings()
    print(f"\n📋 Settings 中的 static_base_url: '{settings.static_base_url}'")
    if settings.static_base_url:
        print(f"   ✅ 配置已读取: {settings.static_base_url}")
    else:
        print("   ❌ 配置为空，将使用相对路径")
        print("   💡 解决方案:")
        print("      1. 在 .env 文件中添加: STATIC_BASE_URL=http://localhost:8001")
        print("      2. 或设置环境变量: export STATIC_BASE_URL=http://localhost:8001")
        print("      3. 重启服务以使配置生效")
except Exception as e:
    print(f"\n❌ 读取配置时出错: {e}")

