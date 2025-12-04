from app import db, bcrypt
from datetime import datetime
from flask_login import UserMixin

class Role(db.Model):
    # 角色表模型
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)  # 角色名称：admin/user
    description = db.Column(db.String(100))  # 角色描述
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    
    # 关系定义
    users = db.relationship('User', backref='role', lazy=True)
    
    def __repr__(self):
        return f'<Role {self.name}>'

class User(db.Model, UserMixin):
    # 用户表模型
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)  # 密码哈希
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False, default=2)  # 关联角色表，默认普通用户
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    # 密码验证方法
    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)
    
    # 设置密码方法
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    # 检查用户角色
    def is_admin(self):
        return self.role.name == 'admin'

class SystemSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(200))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get(cls, key, default=None):
        setting = cls.query.filter_by(key=key).first()
        return setting.value if setting else default

    @classmethod
    def set(cls, key, value, description=None):
        setting = cls.query.filter_by(key=key).first()
        if setting:
            setting.value = value
            if description:
                setting.description = description
        else:
            setting = cls(key=key, value=value, description=description)
            db.session.add(setting)
        db.session.commit()

class ScrapingTask(db.Model):
    """数据采集任务模型"""
    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(100), nullable=False)  # 搜索关键词
    page = db.Column(db.Integer, default=1)  # 采集页码
    status = db.Column(db.String(20), default='pending')  # pending, running, completed, failed
    total_count = db.Column(db.Integer, default=0)  # 采集到的总条数
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    completed_at = db.Column(db.DateTime)
    
    # 关系定义
    creator = db.relationship('User', backref=db.backref('scraping_tasks', lazy=True))
    collections = db.relationship('DataCollection', backref='task', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<ScrapingTask {self.keyword} - {self.status}>'

class DeepCollection(db.Model):
    """深度采集结果模型"""
    id = db.Column(db.Integer, primary_key=True)
    data_collection_id = db.Column(db.Integer, db.ForeignKey('data_collection.id'), nullable=False)
    content = db.Column(db.Text)  # 深度采集的详细内容
    created_at = db.Column(db.DateTime, server_default=db.func.now())  # 深度采集时间
    
    # 关系定义
    data_collection = db.relationship('DataCollection', backref=db.backref('deep_collection', lazy=True, uselist=False))
    
    def __repr__(self):
        return f'<DeepCollection for {self.data_collection_id}>'

class DataCollection(db.Model):
    """数据采集结果模型"""
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('scraping_task.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)  # 新闻标题
    image_url = db.Column(db.String(255))  # 封面图片URL
    source = db.Column(db.String(100))  # 新闻来源
    url = db.Column(db.String(255), nullable=False)  # 新闻原文URL
    is_deep_collected = db.Column(db.Boolean, default=False)  # 是否已执行深度采集
    collected_at = db.Column(db.DateTime, server_default=db.func.now())  # 采集时间
    saved_to_db = db.Column(db.Boolean, default=False)  # 是否已保存到数据库
    
    def __repr__(self):
        return f'<DataCollection {self.title[:50]}>'