"""扩展User模型：添加头像、账号状态、登录失败次数等字段"""
from app import create_app, db
from sqlalchemy import text
import re

app = create_app()

with app.app_context():
    print("\n" + "="*60)
    print("开始扩展User模型")
    print("="*60 + "\n")
    
    # 从配置中获取数据库名称
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    match = re.search(r'\/(\w+)\?', db_uri) or re.search(r'\/(\w+)$', db_uri)
    db_name = match.group(1) if match else None
    
    if not db_name:
        print(f"⚠️  无法从配置中解析数据库名称，使用默认: yunzhi_training")
        db_name = 'yunzhi_training'
    
    print(f"使用数据库: {db_name}\n")
    
    try:
        # 1. 添加avatar字段（头像路径）
        print("1. 检查并添加 avatar 字段...")
        result = db.session.execute(text("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = :db_name 
            AND TABLE_NAME = 'users' 
            AND COLUMN_NAME = 'avatar'
        """), {'db_name': db_name})
        if not result.fetchone():
            db.session.execute(text("ALTER TABLE users ADD COLUMN avatar VARCHAR(255)"))
            print("   ✓ 已添加 avatar 字段")
        else:
            print("   - avatar 字段已存在")
        
        # 2. 添加is_active字段（账号是否激活/禁用）
        print("2. 检查并添加 is_active 字段...")
        result = db.session.execute(text("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = :db_name 
            AND TABLE_NAME = 'users' 
            AND COLUMN_NAME = 'is_active'
        """), {'db_name': db_name})
        if not result.fetchone():
            db.session.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE"))
            print("   ✓ 已添加 is_active 字段")
        else:
            print("   - is_active 字段已存在")
        
        # 3. 添加login_attempts字段（登录失败次数）
        print("3. 检查并添加 login_attempts 字段...")
        result = db.session.execute(text("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = :db_name 
            AND TABLE_NAME = 'users' 
            AND COLUMN_NAME = 'login_attempts'
        """), {'db_name': db_name})
        if not result.fetchone():
            db.session.execute(text("ALTER TABLE users ADD COLUMN login_attempts INTEGER DEFAULT 0"))
            print("   ✓ 已添加 login_attempts 字段")
        else:
            print("   - login_attempts 字段已存在")
        
        # 4. 添加last_login_attempt字段（最后一次登录尝试时间）
        print("4. 检查并添加 last_login_attempt 字段...")
        result = db.session.execute(text("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = :db_name 
            AND TABLE_NAME = 'users' 
            AND COLUMN_NAME = 'last_login_attempt'
        """), {'db_name': db_name})
        if not result.fetchone():
            db.session.execute(text("ALTER TABLE users ADD COLUMN last_login_attempt DATETIME"))
            print("   ✓ 已添加 last_login_attempt 字段")
        else:
            print("   - last_login_attempt 字段已存在")
        
        # 5. 添加last_login_at字段（最后登录时间）
        print("5. 检查并添加 last_login_at 字段...")
        result = db.session.execute(text("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = :db_name 
            AND TABLE_NAME = 'users' 
            AND COLUMN_NAME = 'last_login_at'
        """), {'db_name': db_name})
        if not result.fetchone():
            db.session.execute(text("ALTER TABLE users ADD COLUMN last_login_at DATETIME"))
            print("   ✓ 已添加 last_login_at 字段")
        else:
            print("   - last_login_at 字段已存在")
        
        db.session.commit()
        
        print("\n" + "="*60)
        print("✓ User模型扩展完成！")
        print("="*60 + "\n")
        
        # 验证新字段
        from app.models import User
        user = User.query.first()
        if user:
            print(f"测试用户: {user.username}")
            print(f"  - avatar: {user.avatar}")
            print(f"  - is_active: {user.is_active}")
            print(f"  - login_attempts: {user.login_attempts}")
            print(f"  - last_login_attempt: {user.last_login_attempt}")
            print(f"  - last_login_at: {user.last_login_at}")
            print("\n✓ 所有新字段已成功添加！\n")
        else:
            print("\nℹ️  数据库中暂无用户，请执行 python create_admin.py 创建管理员\n")
        
    except Exception as e:
        db.session.rollback()
        print(f"\n✗ 错误: {e}\n")
        import traceback
        traceback.print_exc()