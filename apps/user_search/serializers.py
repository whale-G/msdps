# 序列化

from rest_framework import serializers


class BaseFileSerializer(serializers.Serializer):
    process_id = serializers.CharField()
    file_type = serializers.CharField()
    created_at = serializers.DateTimeField()
    model_source = serializers.CharField()  # 标识数据来源模型


# 为每个模型创建专用序列化器

# gc类型的列表请求序列化器
class GcFileBaseSerializer(BaseFileSerializer):
    model_source = serializers.CharField(default="gc")


# gc类型的详细请求序列化器
class GcFileDetailSerializer(BaseFileSerializer):
    single_results = serializers.JSONField(source='single_file_json')
    total_result = serializers.JSONField(source='total_file_json')
    model_source = serializers.CharField(default="gc")


# gcms类型的列表请求序列化器
class GcmsFileBaseSerializer(BaseFileSerializer):
    model_source = serializers.CharField(default="gcms")


# gcms类型的详细请求序列化器
class GcmsFileDetailSerializer(BaseFileSerializer):
    single_results = serializers.JSONField(source='single_file_json')
    total_result = serializers.JSONField(source='total_file_json')
    model_source = serializers.CharField(default="gcms")


# lc类型的列表请求序列化器
class LcFileBaseSerializer(BaseFileSerializer):
    model_source = serializers.CharField(default="lc")


# lc类型的详细请求序列化器
class LcFileDetailSerializer(BaseFileSerializer):
    single_results = serializers.JSONField(source='single_file_json')
    total_result = serializers.JSONField(source='total_file_json')
    model_source = serializers.CharField(default="lc")


# lcms类型的列表请求序列化器
class LcmsFileBaseSerializer(BaseFileSerializer):
    model_source = serializers.CharField(default="lcms")


# lcms类型的详细请求序列化器
class LcmsFileDetailSerializer(BaseFileSerializer):
    single_results = serializers.JSONField(source='single_file_json')
    model_source = serializers.CharField(default="lcms")
