#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MySQL数据库备份与恢复脚本
数据库：hnkj
"""

import os
import subprocess
import datetime
import sys

# ==================== 配置区域 ====================
DB_HOST = 'localhost'
DB_PORT = '3306'
DB_USER = 'root'
DB_PASSWORD = '123456'
DB_NAME = 'hnkj'

# 备份文件保存路径
BACKUP_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_FILE = os.path.join(BACKUP_DIR, f"hnkj_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.sql")


def backup_database():
    """备份数据库（包含表结构、数据、外键约束、触发器、存储过程等）"""
    print("=" * 60)
    print("开始备份数据库...")
    print("=" * 60)
    
    try:
        # 构建mysqldump命令
        cmd = [
            'mysqldump',
            f'--host={DB_HOST}',
            f'--port={DB_PORT}',
            f'--user={DB_USER}',
            '--default-character-set=utf8mb4',
            '--single-transaction',  # 保证数据一致性
            '--routines',  # 包含存储过程和函数
            '--triggers',  # 包含触发器
            '--events',  # 包含事件
            '--add-drop-database',  # 添加删除数据库语句
            '--add-drop-table',  # 添加删除表语句
            '--complete-insert',  # 使用完整的INSERT语句（包含列名）
            '--disable-keys',  # 导入时禁用索引，提高导入速度
            '--lock-tables=false',  # 不锁表
        ]
        
        # 如果有密码，添加密码参数
        if DB_PASSWORD:
            cmd.append(f'--password={DB_PASSWORD}')
        
        # 添加数据库名
        cmd.append(DB_NAME)
        
        # 执行备份命令
        print(f"备份文件将保存到: {BACKUP_FILE}")
        print("正在备份，请稍候...")
        
        with open(BACKUP_FILE, 'w', encoding='utf-8') as outfile:
            result = subprocess.run(
                cmd,
                stdout=outfile,
                stderr=subprocess.PIPE,
                text=True,
                timeout=3600  # 1小时超时
            )
        
        # 检查执行结果
        if result.returncode != 0:
            print(f"\n备份失败！错误信息:")
            print(result.stderr)
            return False
        
        # 验证备份文件
        if not os.path.exists(BACKUP_FILE) or os.path.getsize(BACKUP_FILE) == 0:
            print("\n备份失败：备份文件为空或不存在")
            return False
        
        file_size = os.path.getsize(BACKUP_FILE)
        file_size_mb = file_size / (1024 * 1024)
        
        print("\n" + "=" * 60)
        print("备份成功！")
        print("=" * 60)
        print(f"备份文件: {BACKUP_FILE}")
        print(f"文件大小: {file_size_mb:.2f} MB")
        print(f"备份时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        print("\n备份内容包括:")
        print("  ✓ 数据库结构")
        print("  ✓ 所有表结构")
        print("  ✓ 所有数据")
        print("  ✓ 外键约束")
        print("  ✓ 索引")
        print("  ✓ 触发器")
        print("  ✓ 存储过程和函数")
        print("  ✓ 事件")
        print("=" * 60)
        
        return True
        
    except FileNotFoundError:
        print("\n错误：未找到mysqldump命令")
        print("请确保MySQL已正确安装，并且mysqldump已添加到系统环境变量PATH中")
        print("MySQL的mysqldump通常位于: C:\\Program Files\\MySQL\\MySQL Server X.X\\bin\\mysqldump.exe")
        return False
        
    except subprocess.TimeoutExpired:
        print("\n备份超时（超过1小时），请检查数据库大小和网络连接")
        return False
        
    except Exception as e:
        print(f"\n备份过程中发生错误: {str(e)}")
        return False


def restore_database(backup_file_path=None):
    """从备份文件恢复数据库"""
    # 如果没有指定备份文件，使用最新的备份文件
    if not backup_file_path:
        backup_files = [f for f in os.listdir(BACKUP_DIR) if f.startswith('hnkj_backup_') and f.endswith('.sql')]
        if not backup_files:
            print("未找到备份文件，请先执行备份")
            return False
        
        # 使用最新的备份文件
        backup_files.sort(reverse=True)
        backup_file_path = os.path.join(BACKUP_DIR, backup_files[0])
        print(f"使用最新备份文件: {backup_file_path}")
    
    if not os.path.exists(backup_file_path):
        print(f"备份文件不存在: {backup_file_path}")
        return False
    
    print("=" * 60)
    print("警告：此操作将覆盖当前数据库的所有数据！")
    print("=" * 60)
    print(f"备份文件: {backup_file_path}")
    print(f"目标数据库: {DB_NAME}")
    print("=" * 60)
    
    # 确认操作
    confirm = input("\n确定要恢复数据库吗？（输入 YES 确认）: ")
    if confirm != 'YES':
        print("操作已取消")
        return False
    
    print("\n正在恢复数据库，请稍候...")
    
    try:
        # 构建mysql命令
        cmd = [
            'mysql',
            f'--host={DB_HOST}',
            f'--port={DB_PORT}',
            f'--user={DB_USER}',
            '--default-character-set=utf8mb4',
        ]
        
        # 如果有密码，添加密码参数
        if DB_PASSWORD:
            cmd.append(f'--password={DB_PASSWORD}')
        
        # 执行恢复命令
        with open(backup_file_path, 'r', encoding='utf-8') as infile:
            result = subprocess.run(
                cmd,
                stdin=infile,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True,
                timeout=3600
            )
        
        if result.returncode != 0:
            print(f"\n恢复失败！错误信息:")
            print(result.stderr)
            return False
        
        print("\n" + "=" * 60)
        print("数据库恢复成功！")
        print("=" * 60)
        print(f"恢复时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        return True
        
    except FileNotFoundError:
        print("\n错误：未找到mysql命令")
        print("请确保MySQL已正确安装，并且mysql已添加到系统环境变量PATH中")
        return False
        
    except subprocess.TimeoutExpired:
        print("\n恢复超时（超过1小时），请检查数据库大小和网络连接")
        return False
        
    except Exception as e:
        print(f"\n恢复过程中发生错误: {str(e)}")
        return False


def main():
    """主函数"""
    print("\n")
    print("=" * 60)
    print(" " * 10 + "MySQL数据库备份与恢复工具")
    print(" " * 15 + "数据库: " + DB_NAME)
    print("=" * 60)
    print()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'backup':
            # 执行备份
            success = backup_database()
            sys.exit(0 if success else 1)
            
        elif command == 'restore':
            # 恢复数据库
            backup_file = sys.argv[2] if len(sys.argv) > 2 else None
            success = restore_database(backup_file)
            sys.exit(0 if success else 1)
            
        else:
            print("用法:")
            print("  python db_backup_restore.py backup              - 备份数据库")
            print("  python db_backup_restore.py restore             - 恢复数据库（使用最新备份）")
            print("  python db_backup_restore.py restore <备份文件>   - 恢复数据库（指定备份文件）")
    else:
        # 交互式菜单
        print("请选择操作:")
        print("  1. 备份数据库（保存当前状态）")
        print("  2. 恢复数据库（从备份恢复）")
        print()
        
        choice = input("请输入选项 (1/2): ").strip()
        
        if choice == '1':
            success = backup_database()
            sys.exit(0 if success else 1)
        elif choice == '2':
            success = restore_database()
            sys.exit(0 if success else 1)
        else:
            print("无效的选项")
            sys.exit(1)


if __name__ == '__main__':
    main()
