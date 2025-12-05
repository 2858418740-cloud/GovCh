from flask import Blueprint, render_template, abort, request, Response, jsonify
from flask_login import login_required, current_user
import functools
import json
from app.scraper import BaiduNewsScraper

# 创建蓝图
main_bp = Blueprint('main', __name__)

# 检查管理员权限的装饰器
def admin_required(f):
    @login_required
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin():
            abort(403)  # 403 Forbidden
        return f(*args, **kwargs)
    return decorated_function

@main_bp.route('/')
@login_required
def index():
    # 根据用户角色渲染不同内容
    return render_template('index.html')

@main_bp.route('/about')
def about():
    # 渲染关于页面模板
    return render_template('about.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    # 普通用户和管理员都可以访问的仪表盘
    return render_template('dashboard.html')

@main_bp.route('/api/news', methods=['GET'])
def get_news():
    """
    新闻抓取API接口
    参数:
        keyword: 搜索关键词
        page: 页码（可选，默认1）
    返回:
        JSON格式的新闻列表
    """
    try:
        # 获取请求参数
        keyword = request.args.get('keyword', '')
        page = int(request.args.get('page', 1))
        
        # 参数验证
        if not keyword:
            return jsonify({'error': '请提供搜索关键词'}), 400
        
        if page < 1:
            page = 1
        
        # 使用抓取模块获取新闻
        scraper = BaiduNewsScraper()
        raw_news_list = scraper.fetch_news(keyword, page)
        
        # 重新构建新闻列表，确保字段顺序正确
        news_list = []
        for news in raw_news_list:
            ordered_news = {
                'image_url': news.get('image_url', ''),
                'title': news.get('title', ''),
                'source': news.get('source', ''),
                'url': news.get('url', '')
            }
            news_list.append(ordered_news)
        
        # 构建响应数据
        response_data = {
            'status': 'success',
            'keyword': keyword,
            'page': page,
            'count': len(news_list),
            'news_list': news_list
        }
        
        # 使用json.dumps手动序列化，确保字段顺序不变
        json_str = json.dumps(response_data, ensure_ascii=False)
        
        # 返回响应
        return Response(json_str, mimetype='application/json')
        
    except Exception as e:
        # 处理异常
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

