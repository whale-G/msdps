# 调度器配置

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from django.conf import settings
from .tasks import clean_all_expired_data
import logging

logger = logging.getLogger(__name__)


def get_scheduler():
    """创建并配置调度器"""
    scheduler = BlockingScheduler()

    # 测试环境（每10秒执行一次）
    # scheduler.add_job(
    #     func=clean_all_expired_data,
    #     trigger='interval',
    #     seconds=10,
    #     id='clean_all_expired_data_dev',
    #     max_instances=1,
    #     replace_existing=True
    # )

    # 添加清理任务（每天凌晨 2 点执行）
    scheduler.add_job(
        # 要执行的函数
        func=clean_all_expired_data,
        # 触发方式（Cron表达式）
        trigger=CronTrigger(hour=2, minute=0),
        # 任务唯一标识
        id='clean_all_expired_data',
        # 最多同时运行1个实例（解决多线程问题）
        max_instances=1,
        # 覆盖已经存在的同名任务
        replace_existing=True
    )

    return scheduler


def start_scheduler():
    """启动调度器"""
    if settings.DEBUG:
        logger.warning("Running scheduler in DEBUG mode! Tasks will execute in development environment.")

    scheduler = get_scheduler()

    try:
        logger.info("Starting APScheduler...")
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Stopping APScheduler...")
        scheduler.shutdown()