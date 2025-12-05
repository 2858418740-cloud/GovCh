from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required
from app.scraper import BaiduNewsScraper, XinhuaNewsScraper
import logging

# 创建蓝图
api_bp = Blueprint('api', __name__)

# 配置日志
logger = logging.getLogger(__name__)

@api_bp.route('/api/scrape', methods=['GET'])
def scrape_api():
    """
    API端点：用于抓取新闻数据
    
    参数：
        keyword: 搜索关键字
        page: 页码（可选，默认为1）
        source: 数据源（可选，默认为baidu，可选择baidu或xinhua）
        
    返回：
        JSON格式的新闻数据列表
    """
    try:
        # 获取请求参数
        keyword = request.args.get('keyword', '')
        page = int(request.args.get('page', 1))
        source = request.args.get('source', 'baidu')
        
        # 验证参数
        if not keyword:
            return jsonify({'error': '关键字不能为空'}), 400
            
        if page < 1:
            page = 1
        
        # 创建抓取器实例
        if source == 'xinhua':
            scraper = XinhuaNewsScraper()
        else:
            scraper = BaiduNewsScraper()
        
        # 抓取新闻
        news_list = scraper.fetch_news(keyword, page)
        
        # 返回结果
        return jsonify({
            'success': True,
            'data': {
                'keyword': keyword,
                'page': page,
                'count': len(news_list),
                'news': news_list
            }
        }), 200
        
    except Exception as e:
        logger.error(f'API抓取错误: {e}')
        return jsonify({
            'success': False,
            'error': f'抓取失败: {str(e)}'
        }), 500

@api_bp.route('/scrape', methods=['GET', 'POST'])
@login_required
def scrape_page():
    """
    数据抓取页面
    """
    news_list = []
    keyword = ''
    source = 'baidu'
    page = 1
    error = None
    
    if request.method == 'POST':
        try:
            keyword = request.form.get('keyword', '')
            source = request.form.get('source', 'baidu')
            page = int(request.form.get('page', 1))
            
            if not keyword:
                error = '请输入搜索关键字'
            else:
                # 创建抓取器实例
                if source == 'xinhua':
                    scraper = XinhuaNewsScraper()
                else:
                    scraper = BaiduNewsScraper()
                
                # 抓取新闻
                news_list = scraper.fetch_news(keyword, page)
                
        except Exception as e:
            logger.error(f'页面抓取错误: {e}')
            error = f'抓取失败: {str(e)}'
    
    return render_template('scrape.html', 
                           news_list=news_list, 
                           keyword=keyword,
                           source=source,
                           page=page, 
                           error=error)