# 定时任务定义

from django.apps import apps
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


def clean_all_expired_data(days_ago=7):
    """清理所有应用中标记为需要清理的模型数据"""
    logger.info(f"Starting cleanup for records older than {days_ago} days")

    expired_date = timezone.now() - timezone.timedelta(days=days_ago)

    # 遍历所有已注册的应用
    for app_config in apps.get_app_configs():
        # 遍历应用中的所有模型
        for model in app_config.get_models():
            # 检查模型是否需要清理（通过类属性标记）
            if getattr(model, 'needs_cleaning', False):
                # 获取时间戳字段名（默认为 created_at）
                field_name = getattr(model, 'cleaning_field', 'created_at')

                # 查询需要清理的记录（不加载到内存）
                queryset = model.objects.filter(**{f"{field_name}__lt": expired_date})

                # 计算总记录数（不执行实际查询）
                total_count = queryset.count()
                # 没有记录，跳过当前模型
                if total_count == 0:
                    logger.info(f"No records to delete from {model.__name__}")
                    logger.info("----------------------------------------------------------")
                    continue

                # 获取需要打印的字段列表（默认为 created_at）
                field_print = getattr(model, 'fields_to_print', 'created_at')

                # 打印即将删除的记录信息
                if queryset.exists():
                    logger.info(f"Found {total_count} records to delete from {model.__name__}")
                    # 遍历记录并打印
                    for obj in queryset:
                        obj_info = {field: getattr(obj, field) for field in field_print}
                        logger.info(f"Deleting record: {obj_info}")

                # 根据总记录数动态调整删除批量大小（批量删除，避免锁表）
                batch_size = min(100, total_count)   # 一次最多删除100条记录
                total_deleted = 0

                while total_deleted < batch_size:
                    count, _ = queryset.delete()
                    total_deleted += count
                    logger.info(f"Successfully Deleted {count} records from {model.__name__} (batch {total_deleted}/{total_count})")

                logger.info(f"Successfully deleted {total_deleted} records from {model.__name__}")
                logger.info("----------------------------------------------------------")
