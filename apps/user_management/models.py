# 自定义用户模型
from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid


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

    class Meta:
        db_table = 'users'    # 手动指定数据库表名
