import requests
import logging
import sys
import urllib.parse
from bs4 import BeautifulSoup

# 配置模块级别的日志记录器
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 检查是否已经有处理器，如果没有则添加
if not logger.handlers:
    # 创建文件处理器
    file_handler = logging.FileHandler('scraper.log', encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    
    # 创建控制台处理器
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(stream_handler)

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
    
    def deep_collect_with_rule(self, url, title_xpath, content_xpath, source=None, update_rule=False):
        """
        使用规则库中的XPath进行深度采集
        
        Args:
            url (str): 新闻详情页URL
            title_xpath (str): 标题的XPath
            content_xpath (str): 内容的XPath
            source (str): 数据来源，用于更新规则库
            update_rule (bool): 是否在发现规则变化时自动更新规则库
            
        Returns:
            str: 提取的标题和内容，格式为"标题+内容"
        """
        try:
            logger.info(f'开始使用规则进行深度采集URL: {url[:50]}...')
            
            # 发送请求
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # 处理响应内容
            html_content = self._handle_response_content(response)
            
            # 使用BeautifulSoup解析
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取标题
            title = ''
            try:
                # 使用BeautifulSoup的select_one方法解析XPath
                # 注意：BeautifulSoup的select方法支持CSS选择器，需要转换XPath
                # 这里简单处理，假设XPath格式为//tag[@class="class"]
                if title_xpath.startswith('//'):
                    # 转换简单的XPath到CSS选择器
                    css_selector = title_xpath[2:].replace('[', '.').replace(']', '').replace('@class=', '')
                    title_element = soup.select_one(css_selector)
                    if title_element:
                        title = title_element.get_text(strip=True)
                else:
                    # 如果是CSS选择器格式直接使用
                    title_element = soup.select_one(title_xpath)
                    if title_element:
                        title = title_element.get_text(strip=True)
            except Exception as e:
                logger.error(f'提取标题失败: {e}')
            
            # 提取内容
            content = ''
            try:
                if content_xpath.startswith('//'):
                    # 转换简单的XPath到CSS选择器
                    css_selector = content_xpath[2:].replace('[', '.').replace(']', '').replace('@class=', '')
                    content_elements = soup.select(css_selector)
                    if content_elements:
                        content = '\n'.join([elem.get_text(strip=True) for elem in content_elements if elem.get_text(strip=True)])
                else:
                    # 如果是CSS选择器格式直接使用
                    content_elements = soup.select(content_xpath)
                    if content_elements:
                        content = '\n'.join([elem.get_text(strip=True) for elem in content_elements if elem.get_text(strip=True)])
            except Exception as e:
                logger.error(f'提取内容失败: {e}')
            
            # 如果没有找到标题，尝试从页面中提取并更新规则
            if not title:
                logger.info(f'使用XPath未找到标题，尝试自动发现')
                # 尝试常见的标题标签和类名
                title_selectors = [
                    ('h1', {'class': 'title'}),
                    ('h1', {'class': 'article-title'}),
                    ('h1', {'class': 'news-title'}),
                    ('h2', {'class': 'title'}),
                    ('div', {'class': 'title'}),
                    ('h1', {}),
                ]
                
                for tag, attrs in title_selectors:
                    title_element = soup.find(tag, attrs)
                    if title_element:
                        title = title_element.get_text(strip=True)
                        if update_rule and source:
                            # 更新规则库中的标题XPath
                            new_title_xpath = f'//{tag}'
                            if attrs:
                                for key, value in attrs.items():
                                    new_title_xpath += f'[@{key}="{value}"]'
                            logger.info(f'发现新的标题XPath: {new_title_xpath}，来源: {source}')
                            # 这里可以添加更新规则库的逻辑
                            self._update_scraping_rule(source, new_title_xpath, None)
                        break
                
                # 如果还是没找到，使用页面的title标签
                if not title:
                    title_element = soup.find('title')
                    if title_element:
                        title = title_element.get_text(strip=True)
            
            # 如果没有找到内容，使用默认方式提取并更新规则
            if not content:
                logger.info(f'使用XPath未找到内容，尝试自动发现')
                # 尝试常见的新闻内容容器标签和类名
                content_selectors = [
                    ('div', {'class': 'article-content'}),
                    ('div', {'class': 'content'}),
                    ('div', {'id': 'content'}),
                    ('article', {}),
                    ('div', {'class': 'main-content'}),
                    ('div', {'class': 'news-content'}),
                    ('div', {'class': 'article-body'}),
                ]
                
                for tag, attrs in content_selectors:
                    content_div = soup.find(tag, attrs)
                    if content_div:
                        paragraphs = content_div.find_all('p')
                        content = '\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
                        if content and update_rule and source:
                            # 更新规则库中的内容XPath
                            new_content_xpath = f'//{tag}'
                            if attrs:
                                for key, value in attrs.items():
                                    new_content_xpath += f'[@{key}="{value}"]/p'
                            else:
                                new_content_xpath += '/p'
                            logger.info(f'发现新的内容XPath: {new_content_xpath}，来源: {source}')
                            # 这里可以添加更新规则库的逻辑
                            self._update_scraping_rule(source, None, new_content_xpath)
                        break
            
            # 组合标题和内容
            result = f"{title}\n{content}" if title else content
            
            logger.info(f'使用规则深度采集完成，提取标题长度: {len(title)}, 内容长度: {len(content)}')
            return result
            
        except Exception as e:
            logger.error(f'使用规则深度采集错误: {e}', exc_info=True)
            return f'深度采集失败: {str(e)}'
    
    def _update_scraping_rule(self, source, title_xpath, content_xpath):
        """
        更新规则库中的规则
        
        Args:
            source (str): 数据来源
            title_xpath (str): 新的标题XPath
            content_xpath (str): 新的内容XPath
        """
        try:
            # 导入模型，避免循环导入
            from app.models import ScrapingRule, db
            
            # 查找匹配的规则
            rule = ScrapingRule.query.filter(ScrapingRule.site_name.ilike(f'%{source}%')).first()
            if rule:
                # 更新规则
                if title_xpath:
                    rule.title_xpath = title_xpath
                if content_xpath:
                    rule.content_xpath = content_xpath
                
                db.session.commit()
                logger.info(f'规则库更新成功，来源: {source}')
            else:
                logger.info(f'未找到匹配的规则，来源: {source}')
        except Exception as e:
            logger.error(f'更新规则库失败: {e}', exc_info=True)
    
    def collect_by_source(self, url, source, update_rule=False):
        """
        根据数据来源匹配采集规则库中的站点名称，使用规则库中的XPath进行详细内容采集
        
        Args:
            url (str): 新闻详情页URL
            source (str): 数据来源
            update_rule (bool): 是否在发现规则变化时自动更新规则库
            
        Returns:
            str: 提取的标题和内容，格式为"标题+内容"
        """
        try:
            logger.info(f'开始根据来源{source}匹配规则进行采集URL: {url[:50]}...')
            
            # 导入模型，避免循环导入
            from app.models import ScrapingRule
            
            # 根据来源匹配规则库中的站点名称
            rule = ScrapingRule.query.filter(ScrapingRule.site_name.ilike(f'%{source}%')).first()
            
            if not rule:
                logger.info(f'未找到匹配的规则，来源: {source}，使用默认方式采集')
                content = self.deep_collect(url)
                return f'默认采集内容: {content}'
            
            logger.info(f'找到匹配的规则，站点名称: {rule.site_name}，使用规则进行采集')
            
            # 使用规则库中的XPath进行深度采集
            result = self.deep_collect_with_rule(
                url=url,
                title_xpath=rule.title_xpath,
                content_xpath=rule.content_xpath,
                source=source,
                update_rule=update_rule
            )
            
            return result
            
        except Exception as e:
            logger.error(f'根据来源采集错误: {e}', exc_info=True)
            return f'根据来源采集失败: {str(e)}'

class XinhuaNewsScraper:
    """新华网四川频道新闻抓取器"""
    
    BASE_URL = 'https://sc.news.cn/index.htm'
    
    def __init__(self):
        self.session = requests.Session()
        # 设置请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9'
        })
    
    def fetch_news(self, keyword=None, page=1):
        """
        抓取新华网四川频道新闻
        
        Args:
            keyword (str): 搜索关键字（可选，目前新华网四川频道首页不支持直接搜索）
            page (int): 页码（可选，目前仅支持首页）
            
        Returns:
            list: 新闻列表，每个新闻包含标题、概要、封面、原始URL和来源
        """
        try:
            logger.info(f'开始抓取新华网四川频道新闻')
            
            # 发送请求
            response = self.session.get(self.BASE_URL, timeout=10)
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
            with open('xinhua_response.html', 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # 提取新闻列表
            news_list = self._extract_news(html_content)
            
            # 如果提供了关键词，过滤新闻列表
            if keyword:
                news_list = [news for news in news_list if keyword in news['title']]
                logger.info(f'按关键词"{keyword}"过滤后，剩余{len(news_list)}条新闻')
            
            logger.info(f'成功抓取新华网四川频道新闻，共{len(news_list)}条')
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
            
            # 查找所有新闻条目 - 查找class为kgfn的div
            news_items = soup.find_all('div', class_='kgfn')
            logger.info(f'找到class为kgfn的div: {len(news_items)}个')
            
            # 提取每个新闻条目的信息
            for item in news_items:
                news = self._extract_news_item(item)
                if news:
                    news_list.append(news)
            
            # 查找包含dt和dd的新闻条目
            dt_tags = soup.find_all('dt')
            logger.info(f'找到dt标签: {len(dt_tags)}个')
            
            for dt in dt_tags:
                dd = dt.find_next_sibling('dd')
                if dd:
                    # 创建一个包含dt和dd的临时标签
                    import copy
                    temp_tag = copy.copy(dd.parent)
                    news = self._extract_news_item(temp_tag)
                    if news and news not in news_list:
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
            a_tag = item.find('a')
            if not a_tag:
                return None
            
            title = a_tag.string.strip() if a_tag.string else '无标题'
            href = a_tag.get('href', '')
            
            if not title or not href:
                return None
            
            # 处理相对路径，转换为绝对路径
            if not href.startswith('http'):
                if href.startswith('20'):  # 如20251119/2b7f00b11ea44433bb84f0d656cb3c26/c.html
                    href = f'https://sc.news.cn/{href}'
                elif href.startswith('//'):
                    href = f'https:{href}'
                elif href.startswith('/'):
                    href = f'https://sc.news.cn{href}'
                elif href.startswith('https://'):
                    pass
                else:
                    href = f'https://sc.news.cn/{href}'
            
            # 提取来源
            source = '新华网'
            
            # 提取封面图片
            image_url = ''
            img_tag = item.find('img')
            if img_tag:
                image_url = img_tag.get('src', '')
                # 处理图片URL
                if image_url and not image_url.startswith('http'):
                    if image_url.startswith('//'):
                        image_url = f'https:{image_url}'
                    elif image_url.startswith('/'):
                        image_url = f'https://sc.news.cn{image_url}'
                    elif image_url.startswith('images/'):
                        image_url = f'https://sc.news.cn/{image_url}'
            
            # 构建新闻字典，Python 3.7+字典会保持插入顺序
            news = {
                'image_url': image_url,
                'title': title,
                'source': source,
                'url': href
            }
            
            logger.info(f'解析到新闻: 标题="{title[:30]}...", 来源="{source}", URL="{href[:50]}..."')
            
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
            
            # 尝试常见的新华网内容容器标签和类名
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
                ('div', {'class': 'detail-content'}),
                ('div', {'class': 'content-text'}),
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
        # 测试百度新闻爬虫
        print('测试百度新闻爬虫:')
        baidu_scraper = BaiduNewsScraper()
        baidu_news_list = baidu_scraper.fetch_news('成都', page=1)
        print(f'百度新闻共抓取到{len(baidu_news_list)}条新闻')
        
        # 测试新华网新闻爬虫
        print('\n\n测试新华网新闻爬虫:')
        xinhua_scraper = XinhuaNewsScraper()
        xinhua_news_list = xinhua_scraper.fetch_news('成都', page=1)
        print(f'新华网新闻共抓取到{len(xinhua_news_list)}条新闻')
        
        # 打印前5条新华网新闻
        print('\n\n前5条新华网新闻:')
        for i, news in enumerate(xinhua_news_list[:5]):
            print(f'\n新闻{i+1}:')
            print(f'标题: {news["title"]}')
            print(f'来源: {news["source"]}')
            print(f'URL: {news["url"]}')
            print(f'图片: {news["image_url"]}')
            
    except Exception as e:
        print(f'抓取失败: {e}')
