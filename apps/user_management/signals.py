from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
import os
import logging

logger = logging.getLogger(__name__)


@receiver(post_migrate)
def create_initial_admin(sender, **kwargs):
    if sender.name == 'apps.user_management':
        User = get_user_model()
        admin_account = os.environ.get('ADMIN_ACCOUNT', 'admin')
        admin_password = os.environ.get('ADMIN_INITIAL_PASSWORD')

        if not admin_password:
            if os.environ.get('DJANGO_ENV') == 'production':
                raise ImproperlyConfigured("生产环境必须设置 ADMIN_INITIAL_PASSWORD 环境变量！")
            else:
                admin_password = 'Admin123'     # 开发环境的默认密码
                logger.warning("使用默认管理员密码，仅限开发环境！")

        # 检查管理员账户是否已经存在
        if not User.objects.filter(user_account=admin_account).exists():
            logger.info("创建初始管理员账号...")

            # 使用create_superuser方法
            User.objects.create_superuser(
                user_account=admin_account,
                password=admin_password,
                user_name='系统管理员',
                force_password_change=True  # 添加强制密码修改标志
            )
            logger.info(f"管理员账号创建成功！账号: {admin_account}")
        else:
            logger.info("管理员账号已存在，跳过创建")
