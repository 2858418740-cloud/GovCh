import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    # 应用密钥
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False