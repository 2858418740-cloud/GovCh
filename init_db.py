from app import create_app, db
from app.models import Role, User

app = create_app()

with app.app_context():
    print('开始初始化数据库...')
    try:
        # 创建数据库表
        db.create_all()
        print('✓ 数据库表创建成功')
    except Exception as e:
        print(f'✗ 数据库表创建失败: {e}')
    
    print('开始创建角色...')
    try:
        if not Role.query.first():
            admin_role = Role(name='admin', description='管理员角色')
            user_role = Role(name='user', description='普通用户角色')
            db.session.add_all([admin_role, user_role])
            db.session.commit()
            print('✓ 角色创建成功')
        else:
            print('角色已存在，无需创建')
    except Exception as e:
        print(f'✗ 角色创建失败: {e}')
    
    print('开始创建管理员用户...')
    try:
        if not User.query.join(Role).filter(Role.name == 'admin').first():
            admin_role = Role.query.filter_by(name='admin').first()
            admin_user = User(username='admin', email='admin@example.com', role_id=admin_role.id)
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
            print('✓ 管理员用户创建成功')
            print('管理员账号: admin')
            print('密码: admin123')
        else:
            print('管理员用户已存在，无需创建')
    except Exception as e:
        print(f'✗ 管理员用户创建失败: {e}')