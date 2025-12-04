import requests
import logging
import sys
import urllib.parse
from bs4 import BeautifulSoup

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class BaiduNewsScraper:
    """百度新闻抓取器"""
    
    BASE_URL = 'https://www.baidu.com/s'
    
    def __init__(self):
        self.session = requests.Session()
        # 设置请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': 'https://news.baidu.com/'
        })
    
    def fetch_news(self, keyword, page=1):
        """
        抓取百度新闻搜索结果
        
        Args:
            keyword (str): 搜索关键字
            page (int): 页码
            
        Returns:
            list: 新闻列表，每个新闻包含标题、概要、封面、原始URL和来源
        """
        try:
            logger.info(f'开始抓取关键词"{keyword}"的第{page}页新闻')
            
            # 构造请求参数
            params = {
                'rtt': 1,  # 1代表按时间排序，2代表按焦点排序
                'bsst': 1,
                'cl': 2,  # 2代表新闻
                'tn': 'news',
                'rsv_dl': 'ns_pc',
                'word': keyword,
                'pn': (page - 1) * 10  # 每页10条新闻
            }
            
            # 发送请求
            response = self.session.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()  # 检查请求是否成功
            
            # 打印响应信息
            logger.info(f'响应状态码: {response.status_code}')
            logger.info(f'响应URL: {response.url}')
            logger.info(f'Content-Type: {response.headers.get("Content-Type")}')
            logger.info(f'Content-Encoding: {response.headers.get("Content-Encoding")}')
            logger.info(f'原始内容长度: {len(response.content)}')
            
            # 处理响应内容
            html_content = self._handle_response_content(response)
            
            logger.info(f'处理后内容长度: {len(html_content)}')
            
            # 保存响应内容用于调试
            with open('baidu_response.html', 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # 提取新闻列表
            news_list = self._extract_news(html_content)
            
            logger.info(f'成功抓取关键词"{keyword}"的第{page}页新闻，共{len(news_list)}条')
            return news_list
            
        except Exception as e:
            logger.error(f'抓取新闻错误: {e}', exc_info=True)
            raise
    
    def _handle_response_content(self, response):
        """处理响应内容，利用requests内置功能处理压缩和编码"""
        # 利用requests内置功能获取解码后的内容
        logger.info(f'requests自动检测的编码: {response.encoding}')
        return response.text
    
    def _extract_news(self, html_content):
        """
        从HTML内容中提取新闻
        
        Args:
            html_content (str): HTML内容
            
        Returns:
            list: 新闻列表
        """
        news_list = []
        
        try:
            logger.info('开始使用BeautifulSoup提取新闻')
            
            # 创建BeautifulSoup对象
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 查找所有新闻条目 - 首先尝试查找class包含"result"的div
            news_items = soup.find_all('div', class_=lambda x: x and 'result' in x)
            logger.info(f'找到包含"result"类的div: {len(news_items)}个')
            
            if not news_items:
                # 尝试查找所有可能的新闻条目容器
                news_items = soup.find_all('div', attrs={'class': True})
                logger.info(f'找到所有带class的div: {len(news_items)}个')
                
                # 打印一些div的class信息，以便了解结构
                class_names = []
                for item in news_items[:20]:  # 只看前20个
                    class_names.append(item['class'])
                logger.info(f'前20个div的class名称: {class_names}')
            
            # 提取每个新闻条目的信息
            for item in news_items:
                news = self._extract_news_item(item)
                if news:
                    news_list.append(news)
            
            logger.info(f'成功提取到 {len(news_list)} 条新闻')
            
        except Exception as e:
            logger.error(f'提取新闻错误: {e}', exc_info=True)
        
        return news_list
    
    def _extract_news_item(self, item):
        """
        从新闻条目HTML中提取单个新闻信息
        
        Args:
            item (BeautifulSoup Tag): 新闻条目标签
            
        Returns:
            dict: 新闻信息
        """
        try:
            # 提取标题和URL
            title_tag = item.find('a')
            if not title_tag:
                return None
            
            title = title_tag.get_text(strip=True)
            url = title_tag.get('href', '')
            
            if not title or not url:
                return None
            
            # 提取来源和时间
            source = ''
            time = ''
            
            # 查找所有span标签，寻找来源和时间信息
            for span in item.find_all('span'):
                span_text = span.get_text(strip=True)
                if span_text and len(span_text) < 50:
                    # 简单判断来源和时间
                    if '年' in span_text or '月' in span_text or '日' in span_text or ':' in span_text:
                        time = span_text
                    else:
                        source = span_text
                    break
            
            # 提取封面图片
            image_url = ''
            img_tag = item.find('img')
            if img_tag:
                image_url = img_tag.get('src', '')
            
            # 构建新闻字典，Python 3.7+字典会保持插入顺序
            news = {
                'image_url': image_url,
                'title': title,
                'source': source,
                'url': url
            }
            
            logger.info(f'解析到新闻: 标题="{title[:30]}...", 来源="{source}", URL="{url[:50]}..."')
            
            return news
            
        except Exception as e:
            logger.error(f'提取新闻条目错误: {e}', exc_info=True)
        
        return None
        
    def deep_collect(self, url):
        """
        深度采集新闻详情页内容
        
        Args:
            url (str): 新闻详情页URL
            
        Returns:
            str: 提取的详细内容
        """
        try:
            logger.info(f'开始深度采集URL: {url[:50]}...')
            
            # 发送请求
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # 处理响应内容
            html_content = self._handle_response_content(response)
            
            # 使用BeautifulSoup解析
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 尝试多种方式提取主要内容
            content = ''
            
            # 尝试常见的新闻内容容器标签和类名
            content_selectors = [
                ('div', {'class': 'article-content'}),
                ('div', {'class': 'content'}),
                ('div', {'id': 'content'}),
                ('article', {}),
                ('div', {'class': 'main-content'}),
                ('div', {'class': 'news-content'}),
                ('div', {'class': 'article-body'}),
                ('div', {'class': 'content-body'}),
                ('div', {'class': 'content_detail'}),
                ('div', {'class': 'article-text'}),
            ]
            
            for tag, attrs in content_selectors:
                content_div = soup.find(tag, attrs)
                if content_div:
                    # 提取所有段落文本
                    paragraphs = content_div.find_all('p')
                    content = '\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
                    if content:
                        break
            
            # 如果没有找到内容，尝试提取所有p标签的文本
            if not content:
                all_paragraphs = soup.find_all('p')
                content = '\n'.join([p.get_text(strip=True) for p in all_paragraphs if p.get_text(strip=True) and len(p.get_text(strip=True)) > 50])
            
            # 如果还是没有找到内容，使用body标签的文本
            if not content:
                body_tag = soup.find('body')
                if body_tag:
                    content = body_tag.get_text(strip=True)[:1000]  # 限制长度
            
            logger.info(f'深度采集完成，提取内容长度: {len(content)}')
            return content
            
        except Exception as e:
            logger.error(f'深度采集错误: {e}', exc_info=True)
            return f'深度采集失败: {str(e)}'

# 测试代码
if __name__ == '__main__':
    try:
        scraper = BaiduNewsScraper()
        news_list = scraper.fetch_news('西昌', page=1)
        print(f'共抓取到{len(news_list)}条新闻')
        
        # 打印前5条新闻
        for i, news in enumerate(news_list[:5]):
            print(f'\n新闻{i+1}:')
            print(f'标题: {news["title"]}')
            print(f'来源: {news["source"]}')
            print(f'概要: {news["summary"]}')
            print(f'URL: {news["url"]}')
            print(f'图片: {news["image_url"]}')
            
    except Exception as e:
        print(f'抓取失败: {e}')
