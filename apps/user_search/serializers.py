# 序列化

from rest_framework import serializers


class BaseFileSerializer(serializers.Serializer):
    single_file_json = serializers.JSONField()
    file_type = serializers.CharField()
    created_at = serializers.DateTimeField()
    model_source = serializers.CharField()  # 标识数据来源模型


# 为每个模型创建专用序列化器
class GcFileSerializer(BaseFileSerializer):
    total_file_json = serializers.JSONField()
    model_source = serializers.CharField(default="gc")


class GcmsFileSerializer(BaseFileSerializer):
    total_file_json = serializers.JSONField()
    model_source = serializers.CharField(default="gcms")


class LcFileSerializer(BaseFileSerializer):
    total_file_json = serializers.JSONField()
    model_source = serializers.CharField(default="lc")


class LcmsFileSerializer(BaseFileSerializer):
    model_source = serializers.CharField(default="lcms")
