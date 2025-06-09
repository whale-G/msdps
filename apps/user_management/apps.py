from django.apps import AppConfig
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class UserManagementConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.user_management"

    def ready(self):
        # 开发环境下打印启动日志
        if settings.DEBUG:
            logger.debug("正在初始化用户管理信号...")

        from . import signals   # 导入信号处理器

        if settings.DEBUG:
            logger.debug("用户管理信号初始化完成")
