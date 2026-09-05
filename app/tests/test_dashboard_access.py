import unittest
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from flask import url_for
from app import create_app, db
from app.models import User, Student

class DashboardAccessTestCase(unittest.TestCase):
    def setUp(self):
        # 创建测试应用
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        
        # 创建测试数据库
        db.create_all()
        
        # 创建测试学生用户
        self.student_user = User(username='student_test', password='password123', role='student')
        db.session.add(self.student_user)
        
        # 创建测试教师用户
        self.teacher_user = User(username='teacher_test', password='password123', role='teacher')
        db.session.add(self.teacher_user)
        
        # 创建测试管理员用户
        self.admin_user = User(username='admin_test', password='password123', role='admin')
        db.session.add(self.admin_user)
        
        db.session.commit()
    
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_student_cannot_access_dashboard(self):
        # 登录学生用户
        response = self.client.post('/login', data={
            'username': 'student_test',
            'password': 'password123'
        }, follow_redirects=True)
        
        # 尝试访问仪表盘
        response = self.client.get('/dashboard', follow_redirects=True)
        
        # 检查是否被重定向到登录页（因为没有权限）
        self.assertIn('请先登录', response.data.decode('utf-8'))
    
    def test_teacher_can_access_dashboard(self):
        # 登录教师用户
        response = self.client.post('/login', data={
            'username': 'teacher_test',
            'password': 'password123'
        }, follow_redirects=True)
        
        # 尝试访问仪表盘
        response = self.client.get('/dashboard')
        
        # 检查是否成功访问
        self.assertEqual(response.status_code, 200)
        self.assertIn('仪表盘', response.data.decode('utf-8'))
    
    def test_admin_can_access_dashboard(self):
        # 登录管理员用户
        response = self.client.post('/login', data={
            'username': 'admin_test',
            'password': 'password123'
        }, follow_redirects=True)
        
        # 尝试访问仪表盘
        response = self.client.get('/dashboard')
        
        # 检查是否成功访问
        self.assertEqual(response.status_code, 200)
        self.assertIn('仪表盘', response.data.decode('utf-8'))

if __name__ == '__main__':
    unittest.main()