from app import create_app, db
from app.models import Role, User

app = create_app()

with app.app_context():
    # 创建数据库表
    db.create_all()
    
    # 创建角色
    if not Role.query.first():
        admin_role = Role(name='admin', description='管理员角色')
        user_role = Role(name='user', description='普通用户角色')
        db.session.add_all([admin_role, user_role])
        db.session.commit()
    
    # 创建管理员用户
    if not User.query.join(Role).filter(Role.name == 'admin').first():
        admin_role = Role.query.filter_by(name='admin').first()
        admin_user = User(username='admin', email='admin@example.com', role_id=admin_role.id)
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        db.session.commit()
        print('初始化完成！')
        print('管理员账号: admin')
        print('密码: admin123')
    else:
        print('初始化已完成！')