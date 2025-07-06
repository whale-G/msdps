# 自定义用户模型
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
import uuid


# 自定义管理器
class CustomUserManager(BaseUserManager):
    def create_superuser(self, user_account, password, **extra_fields):
        # 设置管理员标志
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('force_password_change', True)  # 添加强制修改密码标志

        if extra_fields.get('is_staff') is not True:
            raise ValueError('超级用户必须设置 is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('超级用户必须设置 is_superuser=True')

        return self.create_user(user_account, password, **extra_fields)

    def create_user(self, user_account, password=None, **extra_fields):
        if not user_account:
            raise ValueError('必须提供用户账号！')

        # 设置默认值
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)

        user = self.model(
            user_account=user_account,
            **extra_fields
        )
        # 自动哈希
        user.set_password(password)
        # 保存到数据库
        user.save(using=self._db)
        return user


class Users(AbstractUser):
    # uuid（主键，系统用户唯一标识）
    uuid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        unique=True
    )
    # 用户昵称（可以为空）
    user_name = models.CharField(max_length=256, null=True)
    # 用户头像（可以为空）
    avatar_url = models.CharField(max_length=1024, null=True)
    # 账号（手机号或者邮箱）
    user_account = models.CharField(max_length=50, unique=True)
    # 密码字段使用默认的password

    # 强制修改密码标志
    force_password_change = models.BooleanField(default=False)

    # 数据插入时间
    created_at = models.DateTimeField(auto_now_add=True)
    # 逻辑删除
    is_delete = models.BooleanField(default=False)

    # 禁用默认字段
    username = None
    USERNAME_FIELD = 'user_account'
    # 创建超级用户时必填字段
    REQUIRED_FIELDS = []

    # 自动清理标志
    needs_cleaning = False  # 标记该模型不需要自动清理

    # 使用自定义管理器
    objects = CustomUserManager()

    class Meta:
        db_table = 'users'    # 手动指定数据库表名

    def save(self, *args, **kwargs):
        # 确保 is_staff 与 is_superuser 保持一致
        self.is_staff = self.is_superuser
        super().save(*args, **kwargs)
