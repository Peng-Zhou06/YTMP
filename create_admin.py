"""
创建管理员账户脚本
"""
from app import create_app, db
from app.models import User

def create_admin():
    """创建管理员账户"""
    app = create_app()
    
    with app.app_context():
        # 检查是否已存在管理员
        existing_admin = User.query.filter_by(username='admin').first()
        if existing_admin:
            print("⚠️  管理员账户已存在！")
            print(f"用户名: {existing_admin.username}")
            print(f"姓名: {existing_admin.name}")
            print(f"邮箱: {existing_admin.email}")
            return
        
        # 创建管理员
        admin = User(
            username='admin',
            password='admin123',  # 会自动加密
            role='admin',
            name='系统管理员',
            email='admin@example.com',
            phone='13800138000'
        )
        
        db.session.add(admin)
        db.session.commit()
        
        print("=" * 60)
        print("✅ 管理员账户创建成功！")
        print("=" * 60)
        print(f"用户名: admin")
        print(f"密码: admin123")
        print(f"角色: 管理员")
        print("=" * 60)
        print("\n⚠️  请及时修改密码！")

if __name__ == '__main__':
    create_admin()
