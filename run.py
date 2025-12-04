from app import create_app, db

# 创建应用实例
app = create_app()

with app.app_context():
    # 创建所有表
    db.create_all()
    print('数据库初始化完成！')

if __name__ == '__main__':
    # 启动开发服务器
    app.run(debug=True)