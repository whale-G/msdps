from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

# 引入序列化器
from .serializers import GcFileSerializer, GcmsFileSerializer, LcFileSerializer, LcmsFileSerializer
# 引入各处理模型
from apps.gc_dt.models import Gc_UserFiles
from apps.gcms_dt.models import Gcms_UserFiles
from apps.lc_dt.models import Lc_UserFiles
from apps.lcms_dt.models import Lcms_UserFiles


# 返回当前用户所有数据
class searchByUser(APIView):
    def get(self, request):
        try:
            user = request.user

            if not user.is_authenticated:
                return Response(
                    {"error": "Authentication required"},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # 查询所有相关模型
            gc_files = Gc_UserFiles.objects.filter(user=user).values('single_file_json', 'total_file_json', 'file_type', 'created_at')
            gcms_files = Gcms_UserFiles.objects.filter(user=user).values('single_file_json', 'total_file_json', 'file_type', 'created_at')
            lc_files = Lc_UserFiles.objects.filter(user=user).values('single_file_json', 'total_file_json', 'file_type', 'created_at')
            lcms_files = Lcms_UserFiles.objects.filter(user=user).values('single_file_json', 'file_type', 'created_at')

            # 序列化数据并添加来源标识
            serialized_data = []

            for item in gc_files:
                serialized_item = GcFileSerializer(item).data
                serialized_data.append(serialized_item)

            for item in gcms_files:
                serialized_item = GcmsFileSerializer(item).data
                serialized_data.append(serialized_item)

            for item in lc_files:
                serialized_item = LcFileSerializer(item).data
                serialized_data.append(serialized_item)

            for item in lcms_files:
                serialized_item = LcmsFileSerializer(item).data
                serialized_data.append(serialized_item)

            # 按创建时间排序
            sorted_data = sorted(
                serialized_data,
                key=lambda x: x['created_at'],
                reverse=True
            )

            # for data in sorted_data:
            #     print(data)

            return Response({"results": sorted_data}, status=status.HTTP_200_OK)

        except Exception as e:
            print(e)
