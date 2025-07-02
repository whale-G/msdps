import os
from celery import Celery

# 设置Django默认配置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MSDPT_BE.settings')

# 创建Celery实例
celery_app = Celery('MSDPT_BE')

# 从Django设置文件中加载Celery配置
celery_app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现并注册任务
celery_app.autodiscover_tasks()

# 测试任务
@celery_app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
