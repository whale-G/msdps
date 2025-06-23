import pymysql
from .celery import celery_app

pymysql.install_as_MySQLdb()    # pyMySQL取代MySQLDB
__all__ = ['celery_app']        # 确保 Celery 应用在 Django 启动时被正确初始化
