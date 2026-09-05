"""
AI 智能助手服务
支持智谱 AI 等大模型 API
"""
import requests
import os
from datetime import datetime
from flask import current_app


class AIAssistantService:
    """AI 智能助手服务"""
    
    SYSTEM_PROMPT = """你是一个全能的智能助手，可以帮助用户解答任何问题。

你的能力：
1. 技术问题：编程、数据库、云计算、网络等
2. 实时信息：新闻、天气、股票、赛事等（你会自动搜索最新信息）
3. 学习指导：学习方法、职业规划、时间管理等
4. 生活问题：健康、旅行、美食、娱乐等
5. 创意写作：文章、故事、诗歌、文案等

注意：
- 回答要简洁明了，适合理解
- 使用中文回答
- 如果涉及代码，给出完整可运行的代码示例
- 对于实时信息，你会自动搜索并提供最新数据
- 回答要准确、实用、有帮助"""
    
    @staticmethod
    def chat(message, history=None, model='glm-4-flash'):
        """与 AI 对话"""
        if history is None:
            history = []
        
        # 智谱 AI 不支持 system role，将系统提示放在第一条用户消息中
        messages = [{'role': 'user', 'content': AIAssistantService.SYSTEM_PROMPT}]
        
        for role, content in history[-10:]:
            messages.append({'role': role, 'content': content})
        
        messages.append({'role': 'user', 'content': message})
        
        try:
            # 直接使用智谱 AI 的联网搜索能力
            response = AIAssistantService._call_zhipu_api_with_search(messages, model)
            
            if response:
                return {
                    'success': True,
                    'response': response,
                    'model': model,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return AIAssistantService._generate_mock_response(message)
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'response': AIAssistantService._generate_mock_response(message)['response']
            }
    
    @staticmethod
    def _maybe_search(message):
        """判断是否需要联网搜索，并返回搜索结果"""
        # 扩大关键词范围，更多场景触发搜索
        search_keywords = [
            # 时间相关
            '新闻', '今天', '昨天', '最新', '当前', '现在', '实时',
            '近日', '日前', '刚刚', '今日', '本周', '本月', '今年',
            '2024', '2025', '2026', '2027',
            # 实时信息
            '天气', '温度', '股票', '股价', '汇率', '排名', '票房',
            '多少钱', '价格', '疫情', '比赛', '赛事', '比分',
            '谁赢了', '谁输了', '冠军', '获奖', '发布', '上市',
            '最新消息', '最新动态', '发生了什么', '怎么回事',
            # 人物事件
            '考察', '访问', '会议', '讲话', '宣布', '决定',
            '习近平', '李克强', '总理', '主席',
            # 英文关键词
            'what is the latest', 'latest news', 'current', 'today',
            'weather', 'stock', 'price', 'who won', 'who is'
        ]
        
        msg_lower = message.lower()
        need_search = any(kw in msg_lower for kw in search_keywords)
        
        # 如果消息较短且不是技术问题，也尝试搜索
        if not need_search and len(message) < 50:
            tech_keywords = ['代码', 'python', 'flask', 'sql', 'docker', 'bug', '错误', '怎么', '如何', '为什么']
            is_tech = any(kw in msg_lower for kw in tech_keywords)
            if not is_tech:
                need_search = True
        
        if not need_search:
            return None
        
        print(f"[AI搜索] 触发搜索: {message[:50]}")
        
        # 执行搜索
        try:
            search_results = AIAssistantService._web_search(message)
            if search_results:
                print(f"[AI搜索] 搜索成功，返回 {len(search_results)} 字符")
                return search_results
            else:
                print(f"[AI搜索] 搜索无结果")
        except Exception as e:
            print(f"[AI搜索] 搜索失败: {e}")
        
        return None
    
    @staticmethod
    def _web_search(query):
        """联网搜索 - 使用必应搜索（更稳定）"""
        try:
            # 使用必应搜索（国内可访问）
            search_url = f"https://www.bing.com/search?q={requests.utils.quote(query)}&count=5"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
            }
            
            response = requests.get(search_url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                return None
            
            import re
            html = response.text
            
            results = []
            
            # 必应搜索结果提取
            # 匹配 <li class="b_algo"> 中的标题和摘要
            pattern = r'<li[^>]*class="[^"]*b_algo[^"]*"[^>]*>.*?<h2[^>]*>.*?<a[^>]*>(.*?)</a>.*?</h2>.*?<div[^>]*class="[^"]*b_caption[^"]*"[^>]*>.*?<p[^>]*>(.*?)</p>'
            matches = re.findall(pattern, html, re.DOTALL)
            
            for title, snippet in matches[:5]:
                title_clean = re.sub(r'<[^>]+>', '', title).strip()
                snippet_clean = re.sub(r'<[^>]+>', '', snippet).strip()
                
                if title_clean:
                    if snippet_clean:
                        results.append(f"{title_clean}: {snippet_clean}")
                    else:
                        results.append(title_clean)
            
            # 备用方案：简单提取所有链接文本
            if not results:
                links = re.findall(r'<a[^>]*href="[^"]*"[^>]*>([^<]{10,100})</a>', html)
                for link in links[:8]:
                    clean = re.sub(r'<[^>]+>', '', link).strip()
                    if clean and len(clean) > 10 and 'bing.com' not in clean:
                        results.append(clean)
                        if len(results) >= 5:
                            break
            
            if results:
                return '\n'.join([f"- {r}" for r in results])
            
            return None
        except Exception as e:
            print(f"必应搜索失败: {e}")
            return None
    
    @staticmethod
    def _call_zhipu_api_with_search(messages, model='glm-4-flash'):
        """调用智谱 AI API 并启用联网搜索"""
        try:
            api_key = current_app.config.get('ZHIPU_API_KEY') or os.environ.get('ZHIPU_API_KEY')
            
            if not api_key:
                return None
            
            # 使用智谱 AI 官方 SDK
            from zhipuai import ZhipuAI
            client = ZhipuAI(api_key=api_key)
            
            # 使用支持联网搜索的模型
            # glm-4-plus 支持联网搜索
            response = client.chat.completions.create(
                model='glm-4-plus',
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
                # 启用联网搜索
                tools=[{"type": "web_search"}]
            )
            
            if response.choices and response.choices[0].message.content:
                print(f"[AI] 使用模型: glm-4-plus (支持联网搜索)")
                return response.choices[0].message.content
            
            return None
        except ImportError:
            # 如果没有安装 zhipuai SDK，使用 requests 直接调用
            return AIAssistantService._call_zhipu_api_requests_with_search(messages, model)
        except Exception as e:
            print(f"智谱 AI API 调用失败: {e}")
            return None
    
    @staticmethod
    def _call_zhipu_api_requests_with_search(messages, model='glm-4-flash'):
        """使用 requests 调用智谱 AI API 并启用联网搜索（备用方案）"""
        try:
            api_key = current_app.config.get('ZHIPU_API_KEY') or os.environ.get('ZHIPU_API_KEY')
            
            if not api_key:
                return None
            
            url = 'https://open.bigmodel.cn/api/paas/v4/chat/completions'
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
            data = {
                'model': 'glm-4-plus',
                'messages': messages,
                'temperature': 0.7,
                'max_tokens': 2000,
                'tools': [{"type": "web_search"}]
            }
            
            print(f"智谱 AI 请求: {data}")
            
            response = requests.post(url, headers=headers, json=data, timeout=60)
            
            if response.status_code != 200:
                print(f"智谱 AI 响应状态码: {response.status_code}")
                print(f"智谱 AI 响应内容: {response.text}")
            
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            print(f"智谱 AI API 调用失败: {e}")
            return None
    
    @staticmethod
    def _call_zhipu_api_requests(messages, model='glm-4-flash'):
        """使用 requests 调用智谱 AI API（备用方案）"""
        try:
            api_key = current_app.config.get('ZHIPU_API_KEY') or os.environ.get('ZHIPU_API_KEY')
            
            if not api_key:
                return None
            
            url = 'https://open.bigmodel.cn/api/paas/v4/chat/completions'
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
            data = {
                'model': model,
                'messages': messages,
                'temperature': 0.7,
                'max_tokens': 2000
            }
            
            print(f"智谱 AI 请求: {data}")
            
            response = requests.post(url, headers=headers, json=data, timeout=60)
            
            if response.status_code != 200:
                print(f"智谱 AI 响应状态码: {response.status_code}")
                print(f"智谱 AI 响应内容: {response.text}")
            
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            print(f"智谱 AI API 调用失败: {e}")
            return None
    
    @staticmethod
    def _generate_mock_response(message):
        """生成模拟回复（当 API 不可用时）"""
        message_lower = message.lower()
        
        if any(kw in message_lower for kw in ['flask', '路由', 'route']):
            response = "Flask 路由定义示例：\n\n```python\nfrom flask import Blueprint, render_template\n\nbp = Blueprint('main', __name__)\n\n@bp.route('/')\ndef index():\n    return render_template('index.html')\n```\n\n路由是 Flask 的核心概念，通过 `@app.route` 或 `@bp.route` 装饰器定义 URL 和处理函数的映射关系。"
        elif any(kw in message_lower for kw in ['sqlalchemy', '数据库', 'model']):
            response = "SQLAlchemy 模型定义示例：\n\n```python\nfrom app import db\nfrom datetime import datetime\n\nclass User(db.Model):\n    __tablename__ = 'users'\n    \n    id = db.Column(db.Integer, primary_key=True)\n    username = db.Column(db.String(64), unique=True, nullable=False)\n    created_at = db.Column(db.DateTime, default=datetime.utcnow)\n```\n\n记得使用 `db.create_all()` 或 `flask db migrate` 创建表。"
        elif any(kw in message_lower for kw in ['docker', '容器', '部署']):
            response = "Docker 部署 Flask 示例：\n\n**Dockerfile:**\n```dockerfile\nFROM python:3.11-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install -r requirements.txt\nCOPY . .\nCMD [\"gunicorn\", \"-b\", \"0.0.0.0:5000\", \"run:app\"]\n```\n\n使用 `docker-compose up -d` 启动。"
        elif any(kw in message_lower for kw in ['错误', '报错', 'error', '异常']):
            response = "遇到错误时，可以按以下步骤排查：\n\n1. **查看错误信息** - 仔细阅读 traceback\n2. **检查日志** - 查看应用日志和容器日志\n3. **常见错误：**\n   - `ModuleNotFoundError` - 缺少依赖\n   - `OperationalError` - 数据库连接问题\n   - `TemplateNotFound` - 模板文件路径错误\n\n把具体错误信息发给我，我帮你分析。"
        elif any(kw in message_lower for kw in ['你好', 'hello', 'hi']):
            response = "你好！我是 AI 开发助手，专门帮助你学习 Flask 和云计算开发。\n\n我可以帮你：\n- 解答技术问题\n- 分析代码错误\n- 提供开发建议\n- 解释技术概念\n\n请问有什么我可以帮你的？"
        else:
            response = f"这是一个很好的问题！\n\n关于「{message}」，我建议：\n\n1. 先查阅 Flask 官方文档：https://flask.palletsprojects.com/\n2. 查看项目代码结构\n3. 如果遇到问题，可以把具体错误信息发给我\n\n需要我进一步解释某个方面吗？"
        
        return {
            'success': True,
            'response': response,
            'model': 'mock',
            'timestamp': datetime.now().isoformat()
        }
    
    @staticmethod
    def analyze_code(code, question=''):
        """分析代码"""
        prompt = f"请分析以下代码：\n\n```python\n{code}\n```\n\n"
        if question:
            prompt += f"问题：{question}\n"
        else:
            prompt += "请指出代码中的问题并给出改进建议。"
        return AIAssistantService.chat(prompt)
    
    @staticmethod
    def explain_error(error_message, code_context=''):
        """解释错误"""
        prompt = f"请解释以下错误：\n\n错误信息：\n{error_message}\n"
        if code_context:
            prompt += f"\n相关代码：\n```python\n{code_context}\n```\n"
        return AIAssistantService.chat(prompt)
    
    @staticmethod
    def generate_prompt_template(scene):
        """生成提示词模板"""
        templates = {
            'code_generation': '请用 Python Flask 实现{功能}功能，要求：\n1. 使用 SQLAlchemy 操作数据库\n2. 包含错误处理\n3. 代码有注释',
            'debugging': '我遇到了以下错误：\n{错误信息}\n\n相关代码：\n{代码}\n\n请帮我分析原因并提供解决方案。',
            'documentation': '请为以下 Flask 路由编写 API 文档：\n{代码}\n\n包括：功能说明、请求参数、响应格式、示例。',
            'testing': '请为以下 Flask 视图函数编写单元测试：\n{代码}\n\n要求使用 pytest 框架。',
            'docker': '请为以下 Flask 项目编写 Dockerfile 和 docker-compose.yml：\n项目结构：\n{结构}'
        }
        return templates.get(scene, '请描述你的需求...')