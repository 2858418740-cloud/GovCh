import logging
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models import User, Role, SystemSetting, ScrapingTask, DataCollection, DeepCollection, ScrapingRule, AIEngine
from app.routes import admin_required

# 设置日志记录
logger = logging.getLogger(__name__)

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
def scraping():
    """
    数据采集页面
    """
    return render_template('admin/scraping.html')

@admin_bp.route('/admin/scraping_rules')
@admin_required
def scraping_rules():
    # 获取所有采集规则
    rules = ScrapingRule.query.order_by(ScrapingRule.id.desc()).all()
    return render_template('admin/scraping_rules.html', rules=rules)

def process_request_headers(headers_text):
    """
    处理原始文本格式的request headers，将其转换为JSON格式
    
    参数:
        headers_text: 原始文本格式的headers
        
    返回:
        str: JSON格式的headers
    """
    if not headers_text:
        return None
    
    headers_dict = {}
    lines = headers_text.strip().split('\n')
    
    i = 0
    while i < len(lines):
        # 跳过空行
        if not lines[i].strip():
            i += 1
            continue
        
        # 获取header名
        header_name = lines[i].strip()
        
        # 获取下一行作为header值
        if i + 1 < len(lines):
            header_value = lines[i + 1].strip()
            headers_dict[header_name] = header_value
            i += 2
        else:
            # 如果没有下一行，可能是格式问题，跳过
            i += 1
    
    # 转换为JSON字符串
    import json
    return json.dumps(headers_dict, ensure_ascii=False)

@admin_bp.route('/admin/scraping_rules/add', methods=['POST'])
@admin_required
def add_scraping_rule():
    site_name = request.form.get('site_name')
    site_url = request.form.get('site_url')
    title_xpath = request.form.get('title_xpath')
    content_xpath = request.form.get('content_xpath')
    request_headers_text = request.form.get('request_headers')
    
    # 处理request headers，转换为JSON格式
    request_headers = process_request_headers(request_headers_text)
    
    # 验证必填字段
    if not site_name or not site_url or not title_xpath or not content_xpath:
        flash('请填写所有必填字段！', 'error')
        return redirect(url_for('admin.scraping_rules'))
    
    # 检查站点URL是否已存在
    if ScrapingRule.query.filter_by(site_url=site_url).first():
        flash('该站点URL已存在！', 'error')
        return redirect(url_for('admin.scraping_rules'))
    
    # 创建新规则
    new_rule = ScrapingRule(
        site_name=site_name,
        site_url=site_url,
        title_xpath=title_xpath,
        content_xpath=content_xpath,
        request_headers=request_headers
    )
    
    try:
        db.session.add(new_rule)
        db.session.commit()
        flash('采集规则添加成功！', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'采集规则添加失败：{str(e)}', 'error')
    
    return redirect(url_for('admin.scraping_rules'))

@admin_bp.route('/admin/scraping_rules/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_scraping_rule(id):
    rule = ScrapingRule.query.get_or_404(id)
    
    # 如果是GET请求，返回编辑页面
    if request.method == 'GET':
        return render_template('admin/edit_scraping_rule.html', rule=rule)
    
    # 如果是POST请求，处理表单提交
    site_name = request.form.get('site_name')
    site_url = request.form.get('site_url')
    title_xpath = request.form.get('title_xpath')
    content_xpath = request.form.get('content_xpath')
    request_headers_text = request.form.get('request_headers')
    
    # 处理request headers，转换为JSON格式
    request_headers = process_request_headers(request_headers_text)
    
    # 验证必填字段
    if not site_name or not site_url or not title_xpath or not content_xpath:
        flash('请填写所有必填字段！', 'error')
        return redirect(url_for('admin.scraping_rules'))
    
    # 检查站点URL是否已存在（排除当前规则）
    if ScrapingRule.query.filter_by(site_url=site_url).filter(ScrapingRule.id != id).first():
        flash('该站点URL已存在！', 'error')
        return redirect(url_for('admin.scraping_rules'))
    
    # 更新规则
    rule.site_name = site_name
    rule.site_url = site_url
    rule.title_xpath = title_xpath
    rule.content_xpath = content_xpath
    rule.request_headers = request_headers
    
    try:
        db.session.commit()
        flash('采集规则更新成功！', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'采集规则更新失败：{str(e)}', 'error')
    
    return redirect(url_for('admin.scraping_rules'))

@admin_bp.route('/admin/scraping_rules/delete/<int:id>')
@admin_required
def delete_scraping_rule(id):
    rule = ScrapingRule.query.get_or_404(id)
    
    try:
        db.session.delete(rule)
        db.session.commit()
        flash('采集规则删除成功！', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'采集规则删除失败：{str(e)}', 'error')
    
    return redirect(url_for('admin.scraping_rules'))

@admin_bp.route('/admin/api/start_scraping', methods=['GET', 'POST'])
@admin_required
def start_scraping():
    """
    开始采集任务API
    """
    try:
        # 从GET查询参数或POST请求体中获取关键词
        keyword = request.args.get('keyword', request.json.get('keyword', '') if request.json else '').strip()
        if not keyword:
            return jsonify({'success': False, 'message': '关键词不能为空'})
        
        # 从GET查询参数或POST请求体中获取页码
        page = int(request.args.get('page', request.json.get('page', 1) if request.json else 1))
        
        logger.info(f'开始执行采集任务，关键词: {keyword}')
        
        # 创建爬虫实例
        from app.scraper import BaiduNewsScraper
        scraper = BaiduNewsScraper()
        
        # 执行采集
        news_list = scraper.fetch_news(keyword, page)
        
        # 保存到数据库
        saved_count = 0
        for news in news_list:
            if news and news.get('title') and news.get('url'):  # 只检查必要字段
                # 检查是否已存在相同URL的记录
                existing = DataCollection.query.filter_by(url=news['url']).first()
                if not existing:
                    # 创建新的数据采集记录
                    new_collection = DataCollection(
                        task_id=None,
                        title=news['title'],
                        source=news.get('source', ''),
                        url=news['url'],
                        image_url=news.get('image_url', ''),
                        keyword=keyword
                    )
                    db.session.add(new_collection)
                    saved_count += 1
        
        # 提交事务
        if saved_count > 0:
            db.session.commit()
            
        # 获取最新的采集数据
        latest_collections = DataCollection.query.order_by(DataCollection.id.desc()).limit(saved_count).all()
        
        # 格式化返回数据
        data = []
        for collection in latest_collections:
            data.append({
                'id': collection.id,
                'title': collection.title,
                'source': collection.source,
                'url': collection.url,
                'image_url': collection.image_url,
                'created_at': collection.collected_at.strftime('%Y-%m-%d %H:%M:%S'),
                'is_deep_collected': collection.is_deep_collected,
                'saved_to_db': collection.saved_to_db,
                'original_url': collection.url,  # 前端模板使用original_url
                'publish_time': collection.collected_at.strftime('%Y-%m-%d %H:%M:%S')  # 前端模板使用publish_time
            })
        
        return jsonify({'success': True, 'message': f'成功采集并保存了 {saved_count} 条新闻数据', 'count': saved_count, 'data': data})
            
    except Exception as e:
        logger.error(f'采集任务执行失败: {e}', exc_info=True)
        return jsonify({'success': False, 'message': f'采集任务执行失败: {str(e)}'})

@admin_bp.route('/admin/api/deep_collect', methods=['POST'])
def deep_collect():
    """
    深度采集API
    """
    try:
        collection_id = request.json.get('collection_id')
        if not collection_id:
            return jsonify({'success': False, 'message': '无效的采集ID'})
        
        # 查找采集记录
        collection = DataCollection.query.get_or_404(collection_id)
        
        # 检查是否已经深度采集过
        if collection.is_deep_collected:
            return jsonify({'success': False, 'message': '该数据已经深度采集过'})
        
        # 执行深度采集
        logger.info(f'开始深度采集，ID: {collection_id}, URL: {collection.url}, Source: {collection.source}')
        
        # 根据来源匹配采集规则
        from app.scraper import BaiduNewsScraper
        scraper = BaiduNewsScraper('')
        
        # 查找匹配的规则
        matched_rule = ScrapingRule.query.filter(ScrapingRule.site_name.ilike(f'%{collection.source}%')).first()
        
        if matched_rule:
            logger.info(f'找到匹配的采集规则: {matched_rule.site_name}')
            # 使用规则中的XPath进行深度采集，并启用自动更新规则功能
            content = scraper.deep_collect_with_rule(
                collection.url, 
                matched_rule.title_xpath, 
                matched_rule.content_xpath, 
                source=collection.source,
                update_rule=True
            )
        else:
            logger.info(f'未找到匹配的采集规则，使用默认方式采集')
            # 使用默认方式进行深度采集
            content = scraper.deep_collect(collection.url)
        
        # 创建深度采集记录
        deep_collection = DeepCollection(
            data_collection_id=collection_id,
            content=content
        )
        db.session.add(deep_collection)
        
        # 更新采集记录状态
        collection.is_deep_collected = True
        db.session.commit()
        
        return jsonify({'success': True, 'message': '深度采集完成', 'content': content[:100] + '...'})
        
    except Exception as e:
        logger.error(f'深度采集失败: {e}', exc_info=True)
        return jsonify({'success': False, 'message': f'深度采集失败: {str(e)}'})

@admin_bp.route('/admin/api/save_data', methods=['POST'])
def save_data():
    """
    保存采集数据API
    """
    try:
        collection_ids = request.json.get('collection_ids', [])
        if not collection_ids:
            return jsonify({'success': False, 'message': '请选择要保存的数据'})
        
        saved_count = 0
        
        for collection_id in collection_ids:
            # 查找采集记录
            collection = DataCollection.query.get_or_404(collection_id)
            
            # 检查是否已经保存过
            if not collection.saved_to_db:
                # 更新保存状态
                collection.saved_to_db = True
                saved_count += 1
        
        # 提交事务
        if saved_count > 0:
            db.session.commit()
            return jsonify({'success': True, 'message': f'成功保存了 {saved_count} 条数据'})
        else:
            return jsonify({'success': True, 'message': '所有选择的数据都已经保存过'})
            
    except Exception as e:
        logger.error(f'保存数据失败: {e}', exc_info=True)
        return jsonify({'success': False, 'message': f'保存数据失败: {str(e)}'})

@admin_bp.route('/admin/api/get_collected_data', methods=['GET'])
def get_collected_data():
    """
    获取采集数据API
    """
    try:
        keyword = request.args.get('keyword', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = 12  # 每页显示12条数据，适合橱窗展示
        
        # 构建查询
        query = DataCollection.query
        if keyword:
            query = query.filter(DataCollection.title.like(f'%{keyword}%') | DataCollection.keyword.like(f'%{keyword}%'))
        
        # 分页查询
        pagination = query.order_by(DataCollection.created_at.desc()).paginate(page=page, per_page=per_page)
        collections = pagination.items
        
        # 格式化数据
        data = []
        for collection in collections:
            data.append({
                'id': collection.id,
                'title': collection.title,
                'source': collection.source,
                'url': collection.url,
                'original_url': collection.url,
                'image_url': collection.image_url,
                'created_at': collection.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'is_deep_collected': collection.is_deep_collected,
                'saved_to_db': collection.saved_to_db
            })
        
        return jsonify({
            'success': True,
            'data': data,
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': pagination.page
        })
        
    except Exception as e:
        logger.error(f'获取采集数据失败: {e}', exc_info=True)
        return jsonify({'success': False, 'message': f'获取采集数据失败: {str(e)}'})

@admin_bp.route('/admin/scraping_tasks')
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
            from app.scraper import BaiduNewsScraper, XinhuaNewsScraper
            
            # 获取数据源参数
            source = request.args.get('source', 'baidu')
            
            # 执行爬虫任务
            if source == 'xinhua':
                scraper = XinhuaNewsScraper()
            else:
                scraper = BaiduNewsScraper()
            news_list = scraper.fetch_news(keyword, page)
            
            # 处理结果
            collections = []
            saved_count = 0
            for i, news in enumerate(news_list):
                if news and news.get('title') and news.get('url'):  # 只检查必要字段
                    # 检查是否已存在相同URL的记录
                    existing = DataCollection.query.filter_by(url=news['url']).first()
                    if not existing:
                        # 创建新的数据采集记录并保存到数据库
                        new_collection = DataCollection(
                            task_id=None,
                            title=news['title'],
                            source=news.get('source', ''),
                            url=news['url'],
                            image_url=news.get('image_url', ''),
                            keyword=keyword
                        )
                        db.session.add(new_collection)
                        saved_count += 1
                        
                        # 将新保存的记录添加到结果列表
                        collection = {
                            'id': i + 1,
                            'title': news['title'],
                            'image_url': news.get('image_url', ''),
                            'source': news.get('source', ''),
                            'url': news['url']
                        }
                        collections.append(collection)
                    else:
                        # 将已存在的记录添加到结果列表
                        collection = {
                            'id': i + 1,
                            'title': news['title'],
                            'image_url': news.get('image_url', ''),
                            'source': news.get('source', ''),
                            'url': news['url']
                        }
                        collections.append(collection)
            
            # 提交事务
            if saved_count > 0:
                db.session.commit()
                flash(f'成功保存{saved_count}条新闻到数据库', 'success')
            
            # 获取总数量
            total_collections = len(collections)
            
            # 保存搜索结果信息
            search_result = {
                'keyword': keyword,
                'page': page,
                'total_results': total_collections
            }
            
        except Exception as e:
            db.session.rollback()
            flash(f'搜索失败：{str(e)}', 'error')
    
    return render_template('admin/scraping_tasks.html', 
                          collections=collections, 
                          total_collections=total_collections,
                          current_page=page,
                          keyword=keyword,
                          source=request.args.get('source', 'baidu'),
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

@admin_bp.route('/admin/data_warehouse')
@admin_required
def data_warehouse():
    """
    数据仓库管理页面
    """
    return render_template('admin/data_warehouse.html')

@admin_bp.route('/admin/api/get_warehouse_data', methods=['GET'])
def get_warehouse_data():
    """
    获取数据仓库中的数据（API）
    """
    try:
        # 获取请求参数
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        search = request.args.get('search', '')
        
        # 构建查询
        query = DataCollection.query
        
        if search:
            query = query.filter((DataCollection.title.like(f'%{search}%')) | 
                                (DataCollection.keyword.like(f'%{search}%')) | 
                                (DataCollection.source.like(f'%{search}%')))
        
        # 分页查询
        pagination = query.order_by(DataCollection.id.desc()).paginate(page=page, per_page=limit)
        collections = pagination.items
        
        # 格式化数据
        data = []
        for collection in collections:
            data.append({
                'id': collection.id,
                'title': collection.title,
                'source': collection.source,
                'url': collection.url,
                'image_url': collection.image_url,
                'keyword': collection.keyword,
                'collected_at': collection.collected_at.strftime('%Y-%m-%d %H:%M:%S') if collection.collected_at else '',
                'is_deep_collected': collection.is_deep_collected,
                'saved_to_db': collection.saved_to_db
            })
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'count': pagination.total,
            'data': data
        })
        
    except Exception as e:
        logger.error(f'获取数据仓库数据失败: {e}', exc_info=True)
        return jsonify({'code': 1, 'msg': f'获取数据失败: {str(e)}'})

@admin_bp.route('/admin/api/edit_warehouse_data', methods=['POST'])
def edit_warehouse_data():
    """
    编辑数据仓库中的数据（API）
    """
    try:
        # 获取请求参数
        id = request.json.get('id')
        title = request.json.get('title')
        source = request.json.get('source')
        url = request.json.get('url')
        image_url = request.json.get('image_url')
        keyword = request.json.get('keyword')
        
        if not id or not title or not url:
            return jsonify({'code': 1, 'msg': 'ID、标题和URL不能为空'})
        
        # 查找采集记录
        collection = DataCollection.query.get_or_404(id)
        
        # 更新数据
        collection.title = title
        collection.source = source
        collection.url = url
        collection.image_url = image_url
        collection.keyword = keyword
        
        # 提交事务
        db.session.commit()
        
        return jsonify({'code': 0, 'msg': '数据更新成功'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'编辑数据仓库数据失败: {e}', exc_info=True)
        return jsonify({'code': 1, 'msg': f'编辑数据失败: {str(e)}'})

@admin_bp.route('/admin/api/get_detail_content/<int:data_id>', methods=['GET'])
def get_detail_content(data_id):
    """
    获取详细内容API接口
    """
    try:
        # 查找数据
        data_item = DataCollection.query.get(data_id)
        if not data_item:
            return jsonify({'code': 1, 'msg': '数据不存在'})
        
        # 检查是否已经有深度采集内容
        if not data_item.is_deep_collected:
            return jsonify({'code': 1, 'msg': '该数据尚未进行详细内容采集'})
        
        # 查询深度采集内容
        deep_content = DeepCollection.query.filter_by(data_collection_id=data_id).first()
        if not deep_content:
            return jsonify({'code': 1, 'msg': '未找到详细内容'})
        
        # 返回详细内容
        return jsonify({
            'code': 0,
            'msg': '获取成功',
            'data': {
                'id': data_item.id,
                'title': data_item.title,
                'source': data_item.source,
                'content': deep_content.content
            }
        })
    except Exception as e:
        logger.error(f'获取详细内容错误: {e}', exc_info=True)
        return jsonify({'code': 1, 'msg': f'获取详细内容失败: {str(e)}'})

@admin_bp.route('/admin/api/collect_detail_content', methods=['POST'])
def collect_detail_content():
    """
    详细内容采集API接口
    """
    try:
        data = request.get_json()
        data_ids = data.get('data_ids')
        update_rule = data.get('update_rule', False)
        
        if not data_ids or not isinstance(data_ids, list):
            return jsonify({'code': 1, 'msg': '无效的参数'})
        
        # 导入Scraper类
        from app.scraper import BaiduNewsScraper
        scraper = BaiduNewsScraper()
        
        results = []
        
        # 遍历所有要采集的数据
        for data_id in data_ids:
            # 查找数据
            data_item = DataCollection.query.get(data_id)
            if not data_item:
                results.append({'id': data_id, 'status': 'error', 'message': '数据不存在'})
                continue
            
            # 检查是否已经有深度采集内容
            if data_item.is_deep_collected:
                # 查询深度采集内容
                deep_content = DeepCollection.query.filter_by(data_collection_id=data_id).first()
                if deep_content:
                    results.append({'id': data_id, 'status': 'warning', 'message': '该数据已经采集过详细内容'})
                    continue
            
            # 根据来源匹配规则进行详细内容采集
            detail_content = scraper.collect_by_source(
                url=data_item.url,
                source=data_item.source,
                update_rule=update_rule
            )
            
            # 保存深度采集内容
            deep_content = DeepCollection(
                data_collection_id=data_id,
                content=detail_content
            )
            db.session.add(deep_content)
            
            # 更新数据标记
            data_item.is_deep_collected = True
            
            results.append({'id': data_id, 'status': 'success', 'message': '详细内容采集成功'})
        
        # 提交事务
        db.session.commit()
        
        success_count = len([r for r in results if r["status"] == "success"])
        return jsonify({'code': 0, 'msg': f'成功采集{success_count}条数据的详细内容', 'results': results})
    except Exception as e:
        logger.error(f'详细内容采集错误: {e}', exc_info=True)
        db.session.rollback()
        return jsonify({'code': 1, 'msg': f'详细内容采集失败: {str(e)}'})

@admin_bp.route('/admin/api/delete_warehouse_data', methods=['POST'])
def delete_warehouse_data():
    """
    删除数据仓库中的数据（API）
    """
    try:
        # 获取请求参数
        ids = request.json.get('ids')
        
        if not ids:
            return jsonify({'code': 1, 'msg': '请选择要删除的数据'})
        
        # 删除数据
        delete_count = 0
        for id in ids:
            collection = DataCollection.query.get(id)
            if collection:
                # 删除关联的深度采集数据
                if collection.deep_collection:
                    db.session.delete(collection.deep_collection)
                db.session.delete(collection)
                delete_count += 1
        
        # 提交事务
        db.session.commit()
        
        return jsonify({'code': 0, 'msg': f'成功删除 {delete_count} 条数据'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'删除数据仓库数据失败: {e}', exc_info=True)
        return jsonify({'code': 1, 'msg': f'删除数据失败: {str(e)}'})

@admin_bp.route('/admin/api/analyze_warehouse_data', methods=['POST'])
def analyze_warehouse_data():
    """
    预留的AI分析接口（API）
    """
    try:
        # 获取请求参数
        ids = request.json.get('ids')
        analyze_type = request.json.get('analyze_type', 'sentiment')  # 默认为情感分析
        
        if not ids:
            return jsonify({'code': 1, 'msg': '请选择要分析的数据'})
        
        # 这里预留AI分析逻辑，当前仅返回示例结果
        # 实际实现时，需要调用AI服务进行分析
        analysis_result = {
            'total_analyzed': len(ids),
            'analyze_type': analyze_type,
            'sentiment_distribution': {
                'positive': 65,
                'neutral': 25,
                'negative': 10
            },
            'keywords': ['成都', '发展', '政策', '经济', '城市']
        }
        
        return jsonify({
            'code': 0, 
            'msg': 'AI分析完成（预留接口）',
            'result': analysis_result
        })
        
    except Exception as e:
        logger.error(f'AI分析数据仓库数据失败: {e}', exc_info=True)
        return jsonify({'code': 1, 'msg': f'分析数据失败: {str(e)}'})

@admin_bp.route('/admin/api/save_to_database', methods=['POST'])
def save_to_database():
    """
    保存单条数据到数据库（API）
    """
    try:
        # 获取请求参数
        id = request.json.get('id')
        
        if not id:
            return jsonify({'code': 1, 'msg': 'ID不能为空'})
        
        # 查找采集记录
        collection = DataCollection.query.get_or_404(id)
        
        # 检查是否已经保存到数据库
        if collection.saved_to_db:
            return jsonify({'code': 0, 'msg': '该数据已经保存到数据库'})
        
        # 更新保存状态
        collection.saved_to_db = True
        db.session.commit()
        
        return jsonify({'code': 0, 'msg': '数据保存到数据库成功'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'保存数据到数据库失败: {e}', exc_info=True)
        return jsonify({'code': 1, 'msg': f'保存数据失败: {str(e)}'})

@admin_bp.route('/admin/api/batch_save_to_database', methods=['POST'])
def batch_save_to_database():
    """
    批量保存数据到数据库（API）
    """
    try:
        # 获取请求参数
        ids = request.json.get('ids')
        
        if not ids or not isinstance(ids, list):
            return jsonify({'code': 1, 'msg': '无效的参数'})
        
        # 更新数据状态
        success_count = 0
        for id in ids:
            collection = DataCollection.query.get(id)
            if collection and not collection.saved_to_db:
                collection.saved_to_db = True
                success_count += 1
        
        db.session.commit()
        
        return jsonify({'code': 0, 'msg': f'成功保存 {success_count} 条数据到数据库'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'批量保存数据到数据库失败: {e}', exc_info=True)
        return jsonify({'code': 1, 'msg': f'批量保存数据失败: {str(e)}'})

@admin_bp.route('/admin/ai_engines')
@admin_required
def ai_engines():
    """AI引擎管理页面"""
    engines = AIEngine.query.order_by(AIEngine.id.desc()).all()
    return render_template('admin/ai_engines.html', engines=engines)

@admin_bp.route('/admin/ai_engines/add', methods=['POST'])
@admin_required
def add_ai_engine():
    """添加AI引擎"""
    provider_name = request.form.get('provider_name')
    api_url = request.form.get('api_url')
    api_key = request.form.get('api_key')
    model_name = request.form.get('model_name')
    description = request.form.get('description')
    is_active = request.form.get('is_active') == '1'
    
    # 验证必填字段
    if not provider_name or not api_url or not api_key or not model_name:
        flash('请填写所有必填字段！', 'error')
        return redirect(url_for('admin.ai_engines'))
    
    try:
        # 创建新的AI引擎
        new_engine = AIEngine(
            provider_name=provider_name,
            api_url=api_url,
            api_key=api_key,
            model_name=model_name,
            description=description,
            is_active=is_active
        )
        
        # 保存到数据库
        db.session.add(new_engine)
        db.session.commit()
        
        flash('AI引擎添加成功！', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'AI引擎添加失败：{str(e)}', 'error')
    
    return redirect(url_for('admin.ai_engines'))

@admin_bp.route('/admin/ai_engines/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_ai_engine(id):
    """编辑AI引擎"""
    # 获取要编辑的AI引擎
    engine = AIEngine.query.get_or_404(id)
    
    if request.method == 'POST':
        # 更新AI引擎信息
        provider_name = request.form.get('provider_name')
        api_url = request.form.get('api_url')
        api_key = request.form.get('api_key')
        model_name = request.form.get('model_name')
        description = request.form.get('description')
        is_active = request.form.get('is_active') == '1'
        
        # 验证必填字段
        if not provider_name or not api_url or not api_key or not model_name:
            flash('请填写所有必填字段！', 'error')
            return redirect(url_for('admin.edit_ai_engine', id=id))
        
        try:
            # 更新数据库
            engine.provider_name = provider_name
            engine.api_url = api_url
            engine.api_key = api_key
            engine.model_name = model_name
            engine.description = description
            engine.is_active = is_active
            
            db.session.commit()
            
            flash('AI引擎编辑成功！', 'success')
            return redirect(url_for('admin.ai_engines'))
        except Exception as e:
            db.session.rollback()
            flash(f'AI引擎编辑失败：{str(e)}', 'error')
    
    return render_template('admin/edit_ai_engine.html', engine=engine)

@admin_bp.route('/admin/ai_engines/delete/<int:id>')
@admin_required
def delete_ai_engine(id):
    """删除AI引擎"""
    try:
        # 获取要删除的AI引擎
        engine = AIEngine.query.get_or_404(id)
        
        # 从数据库中删除
        db.session.delete(engine)
        db.session.commit()
        
        flash('AI引擎删除成功！', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'AI引擎删除失败：{str(e)}', 'error')
    
    return redirect(url_for('admin.ai_engines'))