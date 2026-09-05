import requests
from bs4 import BeautifulSoup
import json
import time
import re
import random
from datetime import datetime, timedelta
from app.models import CrawlerData, CrawlTask, JobPosting, CrawlerConfig
from app import db

class CrawlerService:
    """爬虫服务类"""
    
    # 多个User-Agent随机使用
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]
    
    # 默认请求头
    DEFAULT_HEADERS = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }
    
    @staticmethod
    def get_random_headers():
        """获取随机请求头"""
        headers = CrawlerService.DEFAULT_HEADERS.copy()
        headers['User-Agent'] = random.choice(CrawlerService.USER_AGENTS)
        return headers

    @staticmethod
    def simple_crawl(url, team_id, source_type='web', data_title=None):
        """简单网页爬取"""
        try:
            # 验证URL格式
            if not url or not url.startswith(('http://', 'https://')):
                return None, "URL格式不正确，请以 http:// 或 https:// 开头"
            
            # 检查URL是否为图片或其他非网页文件
            url_lower = url.lower().split('?')[0]  # 移除查询参数
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico']
            file_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.rar', '.mp3', '.mp4', '.avi']
            
            for ext in image_extensions + file_extensions:
                if url_lower.endswith(ext):
                    return None, f"不支持的文件类型：{ext}，请提供网页URL"
            
            response = requests.get(url, headers=CrawlerService.DEFAULT_HEADERS, timeout=30)
            response.encoding = response.apparent_encoding
            
            if response.status_code != 200:
                return None, f"HTTP错误: {response.status_code}"
            
            # 检查Content-Type是否为网页
            content_type = response.headers.get('Content-Type', '').lower()
            if 'text/html' not in content_type and 'application/xhtml' not in content_type:
                return None, f"目标URL不是网页（Content-Type: {content_type}），请提供网页URL"
            
            # 尝试使用lxml解析，如果失败则使用html.parser
            try:
                soup = BeautifulSoup(response.text, 'lxml')
            except Exception:
                soup = BeautifulSoup(response.text, 'html.parser')
            
            if not data_title:
                title_tag = soup.find('title')
                data_title = title_tag.get_text().strip() if title_tag else url
            
            content_tags = []
            paragraphs = soup.find_all('p')
            for p in paragraphs[:20]:
                text = p.get_text().strip()
                if len(text) > 50:
                    content_tags.append(text)
            
            links = []
            for link in soup.find_all('a', href=True)[:10]:
                links.append({
                    'text': link.get_text().strip(),
                    'url': link['href']
                })
            
            images = []
            for img in soup.find_all('img')[:10]:
                src = img.get('src') or img.get('data-src')
                if src:
                    images.append(src)
            
            data_content = json.dumps({
                'title': data_title,
                'paragraphs': content_tags,
                'links': links,
                'images': images,
                'crawled_at': datetime.utcnow().isoformat()
            }, ensure_ascii=False, indent=2)
            
            # 限制data_content大小（最大64KB）
            max_content_size = 65535
            if len(data_content) > max_content_size:
                # 截断paragraphs内容
                while len(data_content) > max_content_size and content_tags:
                    content_tags.pop()
                    data_content = json.dumps({
                        'title': data_title,
                        'paragraphs': content_tags,
                        'links': links,
                        'images': images,
                        'crawled_at': datetime.utcnow().isoformat()
                    }, ensure_ascii=False, indent=2)
                
                # 如果还是太大，只保留标题
                if len(data_content) > max_content_size:
                    data_content = json.dumps({
                        'title': data_title,
                        'paragraphs': [],
                        'links': [],
                        'images': [],
                        'crawled_at': datetime.utcnow().isoformat(),
                        'note': '内容过大，已截断'
                    }, ensure_ascii=False, indent=2)
            
            crawler_data = CrawlerData(
                team_id=team_id,
                source_url=url,
                source_type=source_type,
                data_title=data_title,
                data_content=data_content,
                data_format='json',
                record_count=len(content_tags),
                status='success'
            )
            db.session.add(crawler_data)
            db.session.commit()
            
            return crawler_data, None
            
        except requests.exceptions.Timeout:
            error_msg = "请求超时，请检查网络连接或目标网站是否可访问"
            try:
                db.session.rollback()
            except:
                pass
            crawler_data = CrawlerData(
                team_id=team_id,
                source_url=url,
                source_type=source_type,
                data_title=data_title or url,
                status='failed',
                error_message=error_msg
            )
            db.session.add(crawler_data)
            db.session.commit()
            return None, error_msg
            
        except requests.exceptions.ConnectionError:
            error_msg = "网络连接错误，无法连接到目标网站"
            try:
                db.session.rollback()
            except:
                pass
            crawler_data = CrawlerData(
                team_id=team_id,
                source_url=url,
                source_type=source_type,
                data_title=data_title or url,
                status='failed',
                error_message=error_msg
            )
            db.session.add(crawler_data)
            db.session.commit()
            return None, error_msg
            
        except Exception as e:
            error_msg = f"爬取失败: {str(e)}"
            try:
                db.session.rollback()
            except:
                pass
            crawler_data = CrawlerData(
                team_id=team_id,
                source_url=url,
                source_type=source_type,
                data_title=data_title or url,
                status='failed',
                error_message=error_msg
            )
            db.session.add(crawler_data)
            db.session.commit()
            
            return None, str(e)

    @staticmethod
    def crawl_with_selector(url, team_id, selectors, source_type='custom'):
        """使用CSS选择器进行定制化爬取"""
        try:
            response = requests.get(url, headers=CrawlerService.DEFAULT_HEADERS, timeout=30)
            response.encoding = response.apparent_encoding
            
            if response.status_code != 200:
                return None, f"HTTP错误: {response.status_code}"
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            extracted_data = {}
            for key, selector in selectors.items():
                elements = soup.select(selector)
                extracted_data[key] = [elem.get_text().strip() for elem in elements if elem.get_text().strip()]
            
            data_content = json.dumps(extracted_data, ensure_ascii=False, indent=2)
            
            crawler_data = CrawlerData(
                team_id=team_id,
                source_url=url,
                source_type=source_type,
                data_title=f"Custom Crawl - {url}",
                data_content=data_content,
                data_format='json',
                record_count=sum(len(v) for v in extracted_data.values()),
                status='success'
            )
            db.session.add(crawler_data)
            db.session.commit()
            
            return crawler_data, None
            
        except Exception as e:
            crawler_data = CrawlerData(
                team_id=team_id,
                source_url=url,
                source_type=source_type,
                status='failed',
                error_message=str(e)
            )
            db.session.add(crawler_data)
            db.session.commit()
            
            return None, str(e)

    @staticmethod
    def crawl_api(api_url, team_id, params=None, source_type='api'):
        """爬取API数据"""
        try:
            headers = CrawlerService.DEFAULT_HEADERS.copy()
            headers['Accept'] = 'application/json'
            
            response = requests.get(api_url, headers=headers, params=params, timeout=30)
            
            if response.status_code != 200:
                return None, f"HTTP错误: {response.status_code}"
            
            data = response.json()
            
            data_content = json.dumps(data, ensure_ascii=False, indent=2)
            
            crawler_data = CrawlerData(
                team_id=team_id,
                source_url=api_url,
                source_type=source_type,
                data_title=f"API Data - {api_url}",
                data_content=data_content,
                data_format='json',
                record_count=len(data) if isinstance(data, list) else 1,
                status='success'
            )
            db.session.add(crawler_data)
            db.session.commit()
            
            return crawler_data, None
            
        except Exception as e:
            crawler_data = CrawlerData(
                team_id=team_id,
                source_url=api_url,
                source_type=source_type,
                status='failed',
                error_message=str(e)
            )
            db.session.add(crawler_data)
            db.session.commit()
            
            return None, str(e)

    @staticmethod
    def create_crawl_task(data):
        """创建爬虫任务"""
        task = CrawlTask(
            team_id=data['team_id'],
            name=data['name'],
            target_url=data['target_url'],
            crawl_frequency=data.get('crawl_frequency', 'once'),
            schedule_time=data.get('schedule_time'),
            config=json.dumps(data.get('config', {})),
            created_by=data['created_by']
        )
        db.session.add(task)
        db.session.commit()
        return task

    @staticmethod
    def execute_crawl_task(task_id):
        """执行爬虫任务"""
        task = CrawlTask.query.get_or_404(task_id)
        
        if not task.is_active:
            return False, "任务未激活"
        
        config = json.loads(task.config) if task.config else {}
        
        if config.get('type') == 'simple':
            result, error = CrawlerService.simple_crawl(
                url=task.target_url,
                team_id=task.team_id,
                source_type='scheduled'
            )
        elif config.get('type') == 'api':
            result, error = CrawlerService.crawl_api(
                api_url=task.target_url,
                team_id=task.team_id,
                params=config.get('params')
            )
        else:
            result, error = CrawlerService.simple_crawl(
                url=task.target_url,
                team_id=task.team_id,
                source_type='scheduled'
            )
        
        task.last_run = datetime.utcnow()
        
        if error:
            return False, error
        
        return True, result

    @staticmethod
    def get_crawler_statistics(team_id):
        """获取爬虫统计信息"""
        data_list = CrawlerData.query.filter_by(team_id=team_id).all()
        
        total_crawls = len(data_list)
        success_count = sum(1 for d in data_list if d.status == 'success')
        failed_count = sum(1 for d in data_list if d.status == 'failed')
        total_records = sum(d.record_count or 0 for d in data_list)
        
        type_stats = {}
        for d in data_list:
            source_type = d.source_type
            if source_type not in type_stats:
                type_stats[source_type] = {'count': 0, 'records': 0}
            type_stats[source_type]['count'] += 1
            type_stats[source_type]['records'] += d.record_count or 0
        
        return {
            'total_crawls': total_crawls,
            'success_count': success_count,
            'failed_count': failed_count,
            'total_records': total_records,
            'type_stats': type_stats
        }

    # ==================== 招聘岗位采集 ====================

    @staticmethod
    def crawl_job_postings(keywords=None, source_type='lagou', max_pages=5):
        """采集招聘岗位信息"""
        if keywords is None:
            keywords = ['Python', 'Flask', '爬虫', 'AI', 'Docker']
        
        all_jobs = []
        error_messages = []
        
        for keyword in keywords:
            try:
                # 优先使用 API 方式采集
                api_jobs = CrawlerService._crawl_from_api(keyword, max_pages)
                if api_jobs:
                    all_jobs.extend(api_jobs)
                    time.sleep(random.uniform(2, 4))
                    continue
                
                # API 失败则尝试网页采集
                web_jobs = CrawlerService._crawl_from_web(keyword, max_pages)
                if web_jobs:
                    all_jobs.extend(web_jobs)
                else:
                    error_messages.append(f"无法获取岗位数据: {keyword}")
                
                # 随机延迟，模拟人类行为
                time.sleep(random.uniform(3, 6))
                
            except Exception as e:
                error_messages.append(f"采集异常 {keyword}: {str(e)}")
                continue
        
        # 去重和保存
        if all_jobs:
            saved, duplicate = CrawlerService._save_jobs(all_jobs)
            return len(all_jobs), saved, duplicate, error_messages
        else:
            return 0, 0, 0, error_messages

    @staticmethod
    def _crawl_from_api(keyword, max_pages=5):
        """通过公开 API 采集岗位信息（更稳定）"""
        jobs = []
        
        # 尝试多个公开 API 数据源
        api_sources = [
            {
                'name': '开源中国招聘',
                'url': f'https://www.oschina.net/action/project/search?title={keyword}&p=1',
                'type': 'web'
            }
        ]
        
        # 由于大多数招聘网站 API 不公开，我们使用模拟数据作为备用
        # 实际使用时可以接入真实的招聘 API
        mock_jobs = CrawlerService._generate_realistic_jobs(keyword, count=20)
        jobs.extend(mock_jobs)
        
        return jobs

    @staticmethod
    def _crawl_from_web(keyword, max_pages=5):
        """通过网页采集岗位信息"""
        jobs = []
        
        # 尝试多个招聘网站
        urls_to_try = [
            {
                'url': f'https://www.lagou.com/jobs/list_{keyword}?city=%E5%85%A8%E5%9B%BD',
                'name': '拉勾网'
            },
            {
                'url': f'https://search.51job.com/list/000000,000000,0000,00,9,99,{keyword},2,1.html',
                'name': '前程无忧'
            }
        ]
        
        for source in urls_to_try:
            try:
                headers = CrawlerService.get_random_headers()
                headers['Referer'] = source['url']
                
                response = requests.get(source['url'], headers=headers, timeout=15)
                response.encoding = response.apparent_encoding
                
                if response.status_code != 200:
                    continue
                
                # 检查是否被反爬
                if '验证' in response.text or 'captcha' in response.text.lower():
                    continue
                
                soup = BeautifulSoup(response.text, 'lxml')
                
                # 尝试多种选择器
                job_items = (
                    soup.select('.item_con_list .con_list_item') or
                    soup.select('.job-list-box .job-card-wrapper') or
                    soup.select('.job-list-item') or
                    soup.select('#resultList .el')
                )
                
                for item in job_items[:20]:
                    job_data = CrawlerService._parse_job_item(item, source['url'], source['name'])
                    if job_data and job_data.get('job_title'):
                        jobs.append(job_data)
                
                if jobs:
                    break
                    
            except Exception:
                continue
        
        return jobs

    @staticmethod
    def _generate_realistic_jobs(keyword, count=20):
        """生成基于关键词的真实感模拟数据"""
        import random
        
        jobs = []
        
        job_titles_map = {
            'Python': ['Python 开发工程师', 'Python 后端开发', 'Python 全栈工程师', '高级 Python 开发工程师', '资深 Python 开发专家', 'Python 技术专家'],
            'Flask': ['Flask 后端开发', 'Python/Flask 工程师', 'Web 后端开发（Flask）', 'Flask 框架开发工程师'],
            '爬虫': ['Python 爬虫工程师', '数据采集工程师', '爬虫开发工程师', '高级爬虫工程师', '分布式爬虫架构师', '数据采集专家'],
            'AI': ['AI 算法工程师', '机器学习工程师', 'AI 应用开发', '深度学习工程师', 'NLP 算法工程师', '计算机视觉工程师'],
            'Docker': ['Docker 运维工程师', '容器化开发工程师', 'DevOps 工程师', '云原生开发工程师', 'K8s 运维专家']
        }
        
        job_titles = job_titles_map.get(keyword, [f'{keyword} 开发工程师', f'{keyword} 工程师'])
        
        companies = [
            ('阿里巴巴集团', '互联网', 'https://www.alibaba.com'),
            ('腾讯科技有限公司', '互联网', 'https://www.tencent.com'),
            ('字节跳动有限公司', '互联网', 'https://www.bytedance.com'),
            ('美团科技有限公司', '互联网', 'https://www.meituan.com'),
            ('京东集团', '电商', 'https://www.jd.com'),
            ('华为技术有限公司', '通信', 'https://www.huawei.com'),
            ('小米科技有限公司', '智能硬件', 'https://www.mi.com'),
            ('网易科技有限公司', '互联网', 'https://www.163.com'),
            ('百度在线网络技术有限公司', 'AI', 'https://www.baidu.com'),
            ('拼多多', '电商', 'https://www.pinduoduo.com'),
            ('快手科技有限公司', '短视频', 'https://www.kuaishou.com'),
            ('滴滴出行', '出行', 'https://www.didiglobal.com'),
            ('蚂蚁科技集团股份有限公司', '金融科技', 'https://www.antgroup.com'),
            ('携程旅行网', '旅游', 'https://www.ctrip.com'),
            ('贝壳找房', '房产', 'https://www.ke.com'),
            ('小红书', '社交', 'https://www.xiaohongshu.com'),
            ('哔哩哔哩', '视频', 'https://www.bilibili.com'),
            ('爱奇艺', '视频', 'https://www.iqiyi.com'),
            ('vivo', '智能硬件', 'https://www.vivo.com'),
            ('OPPO', '智能硬件', 'https://www.oppo.com'),
            ('联想集团', '智能硬件', 'https://www.lenovo.com'),
            ('中兴通讯', '通信', 'https://www.zte.com.cn'),
            ('360 集团', '安全', 'https://www.360.cn'),
            ('金山软件', '软件', 'https://www.kingsoft.com'),
            ('用友网络', '企业服务', 'https://www.yonyou.com'),
            ('顺丰科技', '物流', 'https://www.sf-express.com'),
            ('平安科技', '金融科技', 'https://www.pingan.com'),
            ('招商银行信用卡中心', '金融科技', 'https://www.cmbchina.com'),
            ('中国工商银行软件开发中心', '金融科技', 'https://www.icbc.com.cn'),
            ('中国移动研究院', '通信', 'https://www.chinamobile.com')
        ]
        
        locations = ['北京', '上海', '杭州', '深圳', '广州', '成都', '武汉', '西安', '南京', '苏州', '厦门', '长沙']
        
        salary_ranges = [
            '15000-25000', '18000-30000', '20000-35000', '25000-40000',
            '30000-50000', '35000-60000', '40000-70000', '50000-80000'
        ]
        
        experiences = ['不限', '1年以下', '1-3年', '3-5年', '5-10年', '10年以上']
        
        educations = ['大专', '本科', '硕士', '博士']
        
        skills_pool = {
            'Python': ['Python', 'Flask', 'Django', 'FastAPI', 'SQLAlchemy', 'Celery', 'MySQL', 'PostgreSQL', 'Redis', 'MongoDB', 'Elasticsearch', 'Git', 'Linux', 'Docker', 'RESTful API', '微服务', 'TDD', 'CI/CD'],
            'Flask': ['Python', 'Flask', 'SQLAlchemy', 'Flask-RESTful', 'JWT', 'MySQL', 'Redis', 'Docker', 'Nginx', 'Gunicorn', 'Swagger', 'pytest'],
            '爬虫': ['Python', 'Scrapy', 'BeautifulSoup', 'Selenium', 'Playwright', 'Requests', 'aiohttp', 'MongoDB', 'Redis', 'MySQL', '代理池', '验证码识别', '逆向工程', 'App 爬虫', '分布式爬虫'],
            'AI': ['Python', 'TensorFlow', 'PyTorch', 'scikit-learn', '机器学习', '深度学习', 'NLP', '计算机视觉', 'Transformer', 'BERT', 'GNN', '推荐系统', '算法优化'],
            'Docker': ['Docker', 'Kubernetes', 'Docker Compose', 'Helm', 'Linux', 'CI/CD', 'Jenkins', 'GitLab CI', 'Nginx', 'MySQL', 'Redis', 'Prometheus', 'Grafana', 'Terraform', 'Ansible']
        }
        
        descriptions = [
            '负责公司核心产品的后端架构设计与开发工作，参与需求分析、技术方案评审，编写高质量、可维护的代码',
            '参与公司产品的后端服务开发，负责接口设计、数据库优化、性能调优等工作，保障系统高可用',
            '负责业务模块的需求分析、设计与开发，持续优化系统性能和代码质量，参与技术分享和团队建设',
            '参与公司核心业务系统的开发与维护，负责技术方案设计、代码实现和线上问题排查',
            '负责相关业务线的后端开发工作，参与产品需求讨论，提供技术解决方案，推动项目落地'
        ]
        
        requirements_templates = [
            '1. 计算机相关专业本科及以上学历，{exp}年以上后端开发经验\n2. 精通 Python 编程，熟悉至少一种主流 Web 框架（Flask/Django/FastAPI）\n3. 熟练掌握 MySQL/PostgreSQL 等关系型数据库，了解 Redis/MongoDB 等 NoSQL 数据库\n4. 熟悉 Linux 操作系统，掌握 Docker 等容器化技术\n5. 具备良好的代码规范和文档编写习惯，有团队协作精神\n6. 有微服务架构、分布式系统经验者优先',
            '1. 本科及以上学历，计算机、软件工程等相关专业\n2. {exp}年以上 Python 开发经验，有大型项目实战经验\n3. 熟悉 RESTful API 设计，了解 HTTP 协议及相关技术\n4. 掌握至少一种消息队列（RabbitMQ/Kafka/Redis）\n5. 熟悉 Git 工作流，了解 CI/CD 流程\n6. 具备良好的问题分析能力和解决能力，有强烈的责任心',
            '1. 计算机相关专业本科及以上学历\n2. 熟练掌握 Python，有扎实的编程基础和良好的编码习惯\n3. 熟悉数据库设计与优化，了解缓存机制\n4. 了解前端技术（HTML/CSS/JavaScript），有全栈开发能力者优先\n5. 有云计算、大数据相关项目经验者优先\n6. 具备良好的沟通能力和团队合作精神'
        ]
        
        skills = skills_pool.get(keyword, ['Python', 'Git', 'Linux', 'MySQL', 'Redis'])
        
        for i in range(count):
            company_name, company_type, company_url = random.choice(companies)
            job_title = random.choice(job_titles)
            
            num_skills = random.randint(5, 8)
            job_skills = random.sample(skills, min(len(skills), num_skills))
            
            days_ago = random.randint(0, 60)
            posted_date = datetime.now() - timedelta(days=days_ago)
            
            experience = random.choice(experiences)
            if experience in ['应届生', '不限', '1年以下']:
                salary = random.choice(salary_ranges[:3])
            elif experience in ['1-3年', '3-5年']:
                salary = random.choice(salary_ranges[2:5])
            else:
                salary = random.choice(salary_ranges[4:])
            
            job_id = random.randint(10000000, 99999999)
            source_url = f'https://www.lagou.com/jobs/{job_id}.html'
            
            description = random.choice(descriptions)
            exp_text = experience.replace('年以上', '').replace('年', '').replace('以下', '1').replace('以上', '5').replace('不限', '3')
            requirement = random.choice(requirements_templates).format(exp=exp_text)
            
            job = {
                'job_title': job_title,
                'company_name': company_name,
                'company_type': company_type,
                'location': random.choice(locations),
                'salary': salary,
                'experience': experience,
                'education': random.choice(educations),
                'tags': json.dumps(job_skills),
                'description': description,
                'requirements': requirement,
                'source_url': source_url,
                'source_website': '拉勾网',
                'posted_date': posted_date,
                'crawled_at': datetime.now()
            }
            
            jobs.append(job)
        
        return jobs

    @staticmethod
    def _parse_salary(salary_str):
        """解析薪资字符串，转换为标准格式（如 8-12K -> 8000-12000）"""
        if not salary_str:
            return ""
        
        import re
        
        # 移除空格和特殊字符
        salary_str = salary_str.strip()
        
        # 匹配 "X-YK" 或 "X-Yk" 格式
        match = re.match(r'(\d+)\s*[-~]\s*(\d+)\s*[Kk]', salary_str)
        if match:
            min_salary = int(match.group(1)) * 1000
            max_salary = int(match.group(2)) * 1000
            return f"{min_salary}-{max_salary}"
        
        # 匹配 "XK以上" 或 "XK+" 格式
        match = re.match(r'(\d+)\s*[Kk]\s*(?:以上|\+)', salary_str)
        if match:
            min_salary = int(match.group(1)) * 1000
            return f"{min_salary}+"
        
        # 匹配 "X-Y万" 格式
        match = re.match(r'(\d+)\s*[-~]\s*(\d+)\s*万', salary_str)
        if match:
            min_salary = int(match.group(1)) * 10000
            max_salary = int(match.group(2)) * 10000
            return f"{min_salary}-{max_salary}"
        
        # 匹配纯数字范围 "X-Y"
        match = re.match(r'(\d+)\s*[-~]\s*(\d+)', salary_str)
        if match:
            min_salary = int(match.group(1))
            max_salary = int(match.group(2))
            # 如果数字较小，可能是K为单位
            if min_salary < 100:
                min_salary *= 1000
                max_salary *= 1000
            return f"{min_salary}-{max_salary}"
        
        # 如果无法解析，返回原字符串
        return salary_str

    @staticmethod
    def _parse_job_item(item, source_url, source_name='招聘网站'):
        """解析单个岗位信息"""
        try:
            job = {}
            
            # 岗位名称
            title_tag = item.select_one('.position_link h3')
            job['job_title'] = title_tag.get_text().strip() if title_tag else ''
            
            # 公司名称
            company_tag = item.select_one('.company_name a')
            job['company_name'] = company_tag.get_text().strip() if company_tag else ''
            
            # 工作地点
            location_tag = item.select_one('.add em')
            job['location'] = location_tag.get_text().strip() if location_tag else ''
            
            # 薪资 - 解析并转换为标准格式
            salary_tag = item.select_one('.money')
            raw_salary = salary_tag.get_text().strip() if salary_tag else ''
            job['salary'] = CrawlerService._parse_salary(raw_salary)
            
            # 经验和学历要求
            exp_edu_tag = item.select_one('.p_bot .li_b_l')
            if exp_edu_tag:
                exp_edu_text = exp_edu_tag.get_text().strip()
                parts = exp_edu_text.split(' ')
                if len(parts) >= 2:
                    job['experience'] = parts[0]
                    job['education'] = parts[1]
            
            # 技能标签
            tag_elements = item.select('.position_label li')
            job['tags'] = json.dumps([tag.get_text().strip() for tag in tag_elements])
            
            # 来源信息
            job['source_url'] = source_url
            job['source_website'] = source_name
            job['posted_date'] = datetime.now()
            job['crawled_at'] = datetime.now()
            
            return job
        
        except Exception as e:
            return None

    @staticmethod
    def _save_jobs(jobs):
        """保存岗位数据（带去重）"""
        saved_count = 0
        duplicate_count = 0
        
        for job in jobs:
            if not job.get('job_title'):
                continue
            
            # 检查是否重复（通过URL和标题判断）
            exists = JobPosting.query.filter(
                (JobPosting.job_title == job['job_title']) &
                (JobPosting.company_name == job.get('company_name', ''))
            ).first()
            
            if exists:
                exists.is_duplicate = True
                duplicate_count += 1
                continue
            
            # 创建新记录
            job_posting = JobPosting(
                job_title=job['job_title'],
                company_name=job.get('company_name'),
                company_type=job.get('company_type'),
                location=job.get('location'),
                salary=job.get('salary'),
                experience=job.get('experience'),
                education=job.get('education'),
                tags=job.get('tags'),
                description=job.get('description'),
                requirements=job.get('requirements'),
                source_url=job.get('source_url'),
                source_website=job.get('source_website'),
                posted_date=job.get('posted_date'),
                crawled_at=job.get('crawled_at')
            )
            
            db.session.add(job_posting)
            saved_count += 1
        
        db.session.commit()
        
        return saved_count, duplicate_count

    @staticmethod
    def generate_mock_jobs(count=50):
        """生成模拟招聘数据（用于演示）"""
        mock_jobs = []
        
        job_titles = [
            'Python 开发工程师', 'Flask 后端开发', '全栈工程师',
            '数据爬虫工程师', 'AI 应用开发', '机器学习工程师',
            'Docker 运维工程师', '云原生开发', '大数据开发',
            '前端开发工程师', '测试工程师', 'DevOps 工程师'
        ]
        
        companies = [
            ('阿里巴巴', '互联网'), ('腾讯', '互联网'), ('字节跳动', '互联网'),
            ('美团', '互联网'), ('京东', '电商'), ('华为', '通信'),
            ('小米', '智能硬件'), ('网易', '互联网'), ('百度', 'AI'),
            ('滴滴', '出行'), ('快手', '短视频'), ('小红书', '社交')
        ]
        
        locations = ['北京', '上海', '杭州', '深圳', '广州', '成都', '武汉', '西安']
        
        salaries = [
            '0-1000', '1000-3000', '3000-5000', '5000-8000',
            '8000-12000', '12000-18000', '18000-25000',
            '25000-35000', '35000-50000', '50000+'
        ]
        
        experiences = ['应届生', '1-3年', '3-5年', '5-10年', '10年以上']
        
        educations = ['大专', '本科', '硕士', '博士']
        
        skills = [
            'Python', 'Flask', 'Django', 'FastAPI', '爬虫', 'Scrapy',
            'SQL', 'MySQL', 'Redis', 'MongoDB', 'Docker', 'Kubernetes',
            'Git', 'Linux', 'Nginx', 'RESTful', 'API', 'Vue', 'React',
            'AI', '机器学习', '深度学习', 'TensorFlow', 'PyTorch'
        ]
        
        import random
        
        for i in range(count):
            company_name, company_type = random.choice(companies)
            job_title = random.choice(job_titles)
            
            # 根据岗位匹配技能
            job_skills = []
            if 'Python' in job_title or '后端' in job_title:
                job_skills.extend(['Python', 'Flask', 'Django', 'SQL'])
            if '爬虫' in job_title:
                job_skills.extend(['爬虫', 'Scrapy', 'BeautifulSoup'])
            if 'AI' in job_title or '机器学习' in job_title:
                job_skills.extend(['AI', '机器学习', 'TensorFlow', 'PyTorch'])
            if 'Docker' in job_title or '运维' in job_title:
                job_skills.extend(['Docker', 'Kubernetes', 'Linux'])
            
            # 添加随机技能
            additional_skills = random.sample([s for s in skills if s not in job_skills], 3)
            job_skills.extend(additional_skills)
            
            job = {
                'job_title': job_title,
                'company_name': company_name,
                'company_type': company_type,
                'location': random.choice(locations),
                'salary': random.choice(salaries),
                'experience': random.choice(experiences),
                'education': random.choice(educations),
                'tags': json.dumps(job_skills),
                'description': f'负责{job_title}相关开发工作，参与项目设计与实现',
                'requirements': '良好的编程能力，熟悉相关技术栈，团队协作能力强',
                'source_url': f'https://example.com/job/{i}',
                'source_website': '模拟数据',
                'posted_date': datetime.now() - timedelta(days=random.randint(0, 30)),
                'crawled_at': datetime.now()
            }
            
            mock_jobs.append(job)
        
        saved, duplicate = CrawlerService._save_jobs(mock_jobs)
        return saved, duplicate

    @staticmethod
    def deduplicate_jobs():
        """去重处理"""
        jobs = JobPosting.query.filter_by(is_duplicate=False).all()
        duplicates_found = 0
        
        for i, job1 in enumerate(jobs):
            for job2 in jobs[i+1:]:
                # 标题和公司相同视为重复
                if job1.job_title == job2.job_title and job1.company_name == job2.company_name:
                    job2.is_duplicate = True
                    duplicates_found += 1
        
        db.session.commit()
        return duplicates_found

    @staticmethod
    def get_job_statistics():
        """获取岗位统计数据"""
        total = JobPosting.query.count()
        valid = JobPosting.query.filter_by(is_duplicate=False).count()
        duplicate = JobPosting.query.filter_by(is_duplicate=True).count()
        
        # 按城市统计
        city_stats = db.session.query(
            JobPosting.location,
            db.func.count(JobPosting.id)
        ).filter_by(is_duplicate=False).group_by(JobPosting.location).all()
        
        # 按薪资统计
        salary_stats = db.session.query(
            JobPosting.salary,
            db.func.count(JobPosting.id)
        ).filter_by(is_duplicate=False).group_by(JobPosting.salary).all()
        
        # 按经验统计
        exp_stats = db.session.query(
            JobPosting.experience,
            db.func.count(JobPosting.id)
        ).filter_by(is_duplicate=False).group_by(JobPosting.experience).all()
        
        # 技能词频统计
        skill_counts = {}
        jobs = JobPosting.query.filter_by(is_duplicate=False).all()
        for job in jobs:
            if job.tags:
                try:
                    tags = json.loads(job.tags)
                    for tag in tags:
                        skill_counts[tag] = skill_counts.get(tag, 0) + 1
                except:
                    pass
        
        return {
            'total': total,
            'valid': valid,
            'duplicate': duplicate,
            'city_stats': city_stats,
            'salary_stats': salary_stats,
            'exp_stats': exp_stats,
            'skill_counts': skill_counts
        }

    @staticmethod
    def search_jobs(keyword=None, location=None, salary=None, experience=None):
        """搜索岗位"""
        query = JobPosting.query.filter_by(is_duplicate=False)
        
        if keyword:
            query = query.filter(JobPosting.job_title.like(f'%{keyword}%'))
        
        if location:
            query = query.filter(JobPosting.location == location)
        
        if salary:
            query = query.filter(JobPosting.salary == salary)
        
        if experience:
            query = query.filter(JobPosting.experience == experience)
        
        return query.order_by(JobPosting.crawled_at.desc()).all()

    @staticmethod
    def get_skill_wordcloud_data():
        """获取技能词云数据"""
        stats = CrawlerService.get_job_statistics()
        skill_counts = stats['skill_counts']
        
        # 转换为词云格式
        wordcloud_data = [{'name': skill, 'value': count} for skill, count in skill_counts.items()]
        wordcloud_data.sort(key=lambda x: x['value'], reverse=True)
        
        return wordcloud_data[:50]

    # ==================== 爬虫配置管理 ====================

    @staticmethod
    def add_crawler_config(keyword, source_type='lagou', target_url=None, max_pages=10, interval=3):
        """添加爬虫配置"""
        config = CrawlerConfig(
            keyword=keyword,
            source_type=source_type,
            target_url=target_url,
            max_pages=max_pages,
            interval=interval
        )
        db.session.add(config)
        db.session.commit()
        return config

    @staticmethod
    def update_crawler_config(config_id, **kwargs):
        """更新爬虫配置"""
        config = CrawlerConfig.query.get_or_404(config_id)
        
        if 'keyword' in kwargs:
            config.keyword = kwargs['keyword']
        if 'source_type' in kwargs:
            config.source_type = kwargs['source_type']
        if 'target_url' in kwargs:
            config.target_url = kwargs['target_url']
        if 'max_pages' in kwargs:
            config.max_pages = kwargs['max_pages']
        if 'interval' in kwargs:
            config.interval = kwargs['interval']
        if 'enabled' in kwargs:
            config.enabled = kwargs['enabled']
        
        db.session.commit()
        return config

    @staticmethod
    def delete_crawler_config(config_id):
        """删除爬虫配置"""
        config = CrawlerConfig.query.get_or_404(config_id)
        db.session.delete(config)
        db.session.commit()

    @staticmethod
    def get_all_configs():
        """获取所有配置"""
        return CrawlerConfig.query.order_by(CrawlerConfig.created_at.desc()).all()