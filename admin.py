from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models import User, Role, SystemSetting, ScrapingTask, DataCollection
from app.routes import admin_required

# 创建admin蓝图
admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin')
@admin_required
def admin_dashboard():
    # 统计信息
    total_users = User.query.count()
    total_roles = Role.query.count()
    
    # 最近用户
    recent_users = User.query.order_by(User.id.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html', 
                          total_users=total_users, 
                          total_roles=total_roles, 
                          recent_users=recent_users)

@admin_bp.route('/admin/users')
@admin_required
def users():
    # 获取当前页码
    page = request.args.get('page', 1, type=int)
    
    # 搜索和筛选
    search = request.args.get('search', '')
    role_id = request.args.get('role', '')
    
    # 查询用户
    query = User.query
    
    if search:
        query = query.filter((User.username.like(f'%{search}%')) | (User.email.like(f'%{search}%')))
    
    if role_id:
        query = query.filter_by(role_id=role_id)
    
    # 分页查询
    users = query.order_by(User.id.desc()).paginate(page=page, per_page=10)
    
    # 获取所有角色
    roles = Role.query.all()
    
    return render_template('admin/users.html', 
                          users=users.items, 
                          roles=roles, 
                          total_users=users.total, 
                          current_page=users.page)

@admin_bp.route('/admin/roles')
@admin_required
def roles():
    # 获取所有角色
    roles = Role.query.all()
    
    return render_template('admin/roles.html', roles=roles)

@admin_bp.route('/admin/role/add', methods=['POST'])
@admin_required
def add_role():
    name = request.form.get('name')
    description = request.form.get('description')
    
    if not name:
        flash('角色名称不能为空！', 'error')
        return redirect(url_for('admin.roles'))
    
    # 检查角色名称是否已存在
    if Role.query.filter_by(name=name).first():
        flash('角色名称已存在！', 'error')
        return redirect(url_for('admin.roles'))
    
    # 创建新角色
    role = Role(name=name, description=description)
    
    try:
        db.session.add(role)
        db.session.commit()
        flash('角色添加成功！', 'success')
    except Exception as e:
        db.session.rollback()
        flash('角色添加失败，请稍后重试！', 'error')
    
    return redirect(url_for('admin.roles'))

@admin_bp.route('/admin/roles/edit/<int:id>', methods=['GET'])
@admin_required
def get_role(id):
    role = Role.query.get_or_404(id)
    return jsonify({
        'id': role.id,
        'name': role.name,
        'description': role.description
    })

@admin_bp.route('/admin/role/edit/<int:id>', methods=['POST'])
@admin_required
def edit_role(id):
    role = Role.query.get_or_404(id)
    
    name = request.form.get('name')
    description = request.form.get('description')
    
    if not name:
        flash('角色名称不能为空！', 'error')
        return redirect(url_for('admin.roles'))
    
    # 检查角色名称是否已存在
    if Role.query.filter_by(name=name).first() and role.name != name:
        flash('角色名称已存在！', 'error')
        return redirect(url_for('admin.roles'))
    
    # 更新角色
    role.name = name
    role.description = description
    
    try:
        db.session.commit()
        flash('角色更新成功！', 'success')
    except Exception as e:
        db.session.rollback()
        flash('角色更新失败，请稍后重试！', 'error')
    
    return redirect(url_for('admin.roles'))

@admin_bp.route('/admin/role/delete/<int:id>')
@admin_required
def delete_role(id):
    role = Role.query.get_or_404(id)
    
    # 不能删除内置角色
    if role.name in ['admin', 'user']:
        flash('不能删除内置角色！', 'error')
        return redirect(url_for('admin.roles'))
    
    # 检查是否有用户使用该角色
    if role.users.count() > 0:
        flash('该角色下还有用户，不能删除！', 'error')
        return redirect(url_for('admin.roles'))
    
    try:
        db.session.delete(role)
        db.session.commit()
        flash('角色删除成功！', 'success')
    except Exception as e:
        db.session.rollback()
        flash('角色删除失败，请稍后重试！', 'error')
    
    return redirect(url_for('admin.roles'))

@admin_bp.route('/admin/settings', methods=['GET', 'POST'])
@admin_required
def settings():
    # 获取所有系统设置
    settings = SystemSetting.query.all()
    
    # 设置字典，用于前端展示
    settings_dict = {
        'app_name': SystemSetting.get('app_name', '政企智能舆情分析平台'),
        'logo_url': SystemSetting.get('logo_url', ''),
        'description': SystemSetting.get('description', '')
    }
    
    if request.method == 'POST':
        # 保存系统设置
        app_name = request.form.get('app_name')
        description = request.form.get('description')
        
        # 保存基本设置
        SystemSetting.set('app_name', app_name, '应用名称')
        SystemSetting.set('description', description, '应用描述')
        
        # 处理LOGO上传
        if 'logo' in request.files:
            logo = request.files['logo']
            if logo.filename != '':
                # 保存文件到静态文件夹
                import os
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)
                
                file_path = os.path.join(upload_folder, logo.filename)
                logo.save(file_path)
                
                # 保存LOGO URL
                SystemSetting.set('logo_url', logo.filename, '应用LOGO')
                flash('LOGO上传成功！', 'success')
        
        flash('系统设置保存成功！', 'success')
        return redirect(url_for('admin.settings'))
    
    return render_template('admin/settings.html', settings=settings_dict)

@admin_bp.route('/admin/scraping')
@admin_required
def scraping_tasks():
    # 获取当前页码
    page = request.args.get('page', 1, type=int)
    
    # 搜索关键词
    keyword = request.args.get('keyword', '')
    
    # 结果列表
    collections = []
    total_collections = 0
    search_result = None
    
    # 如果有搜索关键词，直接抓取并显示结果
    if keyword:
        try:
            # 导入爬虫模块
            from app.scraper import BaiduNewsScraper
            
            # 执行爬虫任务
            scraper = BaiduNewsScraper()
            news_list = scraper.fetch_news(keyword, page)
            
            # 处理结果
            collections = []
            for i, news in enumerate(news_list):
                # 模拟DataCollection对象结构
                collection = {
                    'id': i + 1,
                    'title': news.get('title', ''),
                    'image_url': news.get('image_url', ''),
                    'source': news.get('source', ''),
                    'url': news.get('url', '')
                }
                collections.append(collection)
            
            # 获取总数量（这里直接使用当前页结果数，实际中可能需要调整）
            total_collections = len(news_list)
            
            # 保存搜索结果信息
            search_result = {
                'keyword': keyword,
                'page': page,
                'total_results': total_collections
            }
            
        except Exception as e:
            flash(f'搜索失败：{str(e)}', 'error')
    
    return render_template('admin/scraping_tasks.html', 
                          collections=collections, 
                          total_collections=total_collections,
                          current_page=page,
                          keyword=keyword,
                          search_result=search_result)



@admin_bp.route('/admin/user/add', methods=['POST'])
@admin_required
def add_user():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    role_id = request.form.get('role_id')
    
    if not username or not email or not password or not role_id:
        flash('请填写所有必填字段！', 'error')
        return redirect(url_for('admin.users'))
    
    # 检查用户名是否已存在
    if User.query.filter_by(username=username).first():
        flash('用户名已存在！', 'error')
        return redirect(url_for('admin.users'))
    
    # 检查邮箱是否已存在
    if User.query.filter_by(email=email).first():
        flash('邮箱已存在！', 'error')
        return redirect(url_for('admin.users'))
    
    # 创建新用户
    user = User(username=username, email=email, role_id=role_id)
    user.set_password(password)
    
    try:
        db.session.add(user)
        db.session.commit()
        flash('用户添加成功！', 'success')
    except Exception as e:
        db.session.rollback()
        flash('用户添加失败，请稍后重试！', 'error')
    
    return redirect(url_for('admin.users'))

@admin_bp.route('/admin/users/edit/<int:id>', methods=['GET'])
@admin_required
def get_user(id):
    user = User.query.get_or_404(id)
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role_id': user.role_id
    })

@admin_bp.route('/admin/user/edit/<int:id>', methods=['POST'])
@admin_required
def edit_user(id):
    user = User.query.get_or_404(id)
    
    username = request.form.get('username')
    email = request.form.get('email')
    role_id = request.form.get('role_id')
    password = request.form.get('password')
    
    if not username or not email or not role_id:
        flash('请填写所有必填字段！', 'error')
        return redirect(url_for('admin.users'))
    
    # 检查用户名是否已存在
    if User.query.filter_by(username=username).first() and user.username != username:
        flash('用户名已存在！', 'error')
        return redirect(url_for('admin.users'))
    
    # 检查邮箱是否已存在
    if User.query.filter_by(email=email).first() and user.email != email:
        flash('邮箱已存在！', 'error')
        return redirect(url_for('admin.users'))
    
    # 更新用户信息
    user.username = username
    user.email = email
    user.role_id = role_id
    
    if password:
        user.set_password(password)
    
    try:
        db.session.commit()
        flash('用户更新成功！', 'success')
    except Exception as e:
        db.session.rollback()
        flash('用户更新失败，请稍后重试！', 'error')
    
    return redirect(url_for('admin.users'))

@admin_bp.route('/admin/user/delete/<int:id>')
@admin_required
def delete_user(id):
    user = User.query.get_or_404(id)
    
    # 不能删除自己
    if user.id == current_user.id:
        flash('不能删除当前登录用户！', 'error')
        return redirect(url_for('admin.users'))
    
    try:
        db.session.delete(user)
        db.session.commit()
        flash('用户删除成功！', 'success')
    except Exception as e:
        db.session.rollback()
        flash('用户删除失败，请稍后重试！', 'error')
    
    return redirect(url_for('admin.users'))