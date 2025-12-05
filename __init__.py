from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
import os

# 创建SQLAlchemy实例
db = SQLAlchemy()

# 创建Migrate实例
migrate = Migrate()

# 创建LoginManager实例
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = '请先登录！'
login_manager.login_message_category = 'warning'

# 创建Bcrypt实例
bcrypt = Bcrypt()

def create_app():
    # 创建Flask应用实例，指定模板和静态文件夹路径
    app = Flask(__name__, 
                template_folder=os.path.join(os.path.abspath(os.path.dirname(__file__)), '../templates'),
                static_folder=os.path.join(os.path.abspath(os.path.dirname(__file__)), '../static'),
                static_url_path='/static')
    
    # 配置应用
    app.config.from_object('config.Config')
    
    # 初始化扩展
    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    
    # 注册蓝图
    from app.routes import main_bp
    app.register_blueprint(main_bp)
    
    from app.auth import auth_bp
    app.register_blueprint(auth_bp)
    
    from app.admin import admin_bp
    app.register_blueprint(admin_bp)
    
    from app.api import api_bp
    app.register_blueprint(api_bp)
    
    return app

# 用户加载回调函数
@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))