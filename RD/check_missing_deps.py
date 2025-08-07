#!/usr/bin/env python3
"""
检查缺少的依赖包
"""

import sys
import subprocess

def check_package(package_name):
    """检查包是否已安装"""
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False

def main():
    """检查所有需要的包"""
    print("检查虚拟客服API所需的依赖包...")
    print("=" * 50)
    
    # 需要检查的包列表
    required_packages = [
        ('fastapi', 'fastapi==0.95.1'),
        ('uvicorn', 'uvicorn==0.22.0'),
        ('sqlalchemy', 'sqlalchemy==2.0.12'),
        ('alembic', 'alembic==1.10.4'),
        ('pymysql', 'PyMySQL==1.1.0'),
        ('pydantic', 'pydantic[email]==1.10.7'),
        ('email_validator', 'email-validator'),
        ('jose', 'python-jose[cryptography]'),
        ('passlib', 'passlib[bcrypt]'),
        ('jwt', 'pyjwt==2.7.0'),
        ('bcrypt', 'bcrypt==4.0.1'),
        ('cryptography', 'cryptography>=41.0.0'),
        ('multipart', 'python-multipart==0.0.6'),
        ('redis', 'redis>=4.5.5'),
        ('dotenv', 'python-dotenv==1.0.0'),
        ('arrow', 'arrow==1.3.0'),
        ('nanoid', 'nanoid==2.0.0'),
        ('pandas', 'pandas>=1.5.0'),
        ('openpyxl', 'openpyxl>=3.0.0'),
        ('pytest', 'pytest>=7.0.0'),
        ('pytest_asyncio', 'pytest-asyncio>=0.21.0')
    ]
    
    missing_packages = []
    installed_packages = []
    
    for import_name, pip_name in required_packages:
        if check_package(import_name):
            installed_packages.append(pip_name)
            print(f"✅ {pip_name}")
        else:
            missing_packages.append(pip_name)
            print(f"❌ {pip_name}")
    
    print("\n" + "=" * 50)
    print(f"已安装: {len(installed_packages)} 个包")
    print(f"缺少: {len(missing_packages)} 个包")
    
    if missing_packages:
        print("\n缺少的依赖包:")
        print("-" * 30)
        for package in missing_packages:
            print(f"  {package}")
        
        print("\n安装命令:")
        print("-" * 30)
        print("pip3 install \\")
        for i, package in enumerate(missing_packages):
            if i == len(missing_packages) - 1:
                print(f"  {package}")
            else:
                print(f"  {package} \\")
    else:
        print("\n🎉 所有依赖包都已安装！")

if __name__ == "__main__":
    main()
