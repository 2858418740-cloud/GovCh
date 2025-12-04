from app import create_app, db
from app.models import Role, User

# 创建应用实例
app = create_app()

# 应用上下文
with app.app_context():
    # 创建数据库表
    db.create_all()
    
    # 创建角色
    print('创建默认角色...')
    
    # 检查是否已有角色
    if not Role.query.first():
        # 创建管理员角色
        admin_role = Role(name='admin', description='管理员角色')
        db.session.add(admin_role)
        
        # 创建普通用户角色
        user_role = Role(name='user', description='普通用户角色')
        db.session.add(user_role)
        
        db.session.commit()
        print('角色创建成功！')
    else:
        print('角色已存在，跳过创建。')
    
    # 创建管理员用户
    print('创建管理员用户...')
    
    # 检查是否已有管理员用户
    admin = User.query.join(Role).filter(Role.name == 'admin').first()
    if not admin:
        # 获取管理员角色
        admin_role = Role.query.filter_by(name='admin').first()
        
        # 创建管理员用户
        admin_user = User(
            username='admin',
            email='admin@example.com',
            role_id=admin_role.id
        )
        admin_user.set_password('admin123')  # 默认密码
        
        db.session.add(admin_user)
        db.session.commit()
        print('管理员用户创建成功！')
        print('用户名: admin')
        print('密码: admin123')
    else:
        print('管理员用户已存在，跳过创建。')
    
    print('初始化完成！')