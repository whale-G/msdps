from django.db import models
from django.conf import settings


class Gcms_UserFiles(models.Model):
    # 处理记录索引（主键）
    process_id = models.CharField(max_length=256, primary_key=True)
    # 添加用户关联（使用UUID作为外键）
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,    # 用户删除时删除相关文件
        related_name='gcms_files',   # 反向关系名称
        db_column='user_uuid',       # 数据库列名
        to_field='uuid'              # 关联到Users的uuid字段
    )
    # 文件类型（实验类型）
    file_type = models.CharField(default='unknown', max_length=50)
    # 单次处理中——单个文件处理结果
    single_file_json = models.JSONField()
    # 单次处理中——整理后总处理结果
    total_file_json = models.JSONField()
    # 记录产生时间
    created_at = models.DateTimeField(auto_now_add=True)

    needs_cleaning = True  # 标记该模型需要清理
    cleaning_field = 'created_at'  # 指定时间戳字段名
    fields_to_print = ['user', 'file_type', 'created_at']  # 指定需要打印的字段（自动清理）

    class Meta:
        db_table = 'gcms_dt_userfiles'    # 手动指定数据库表名
