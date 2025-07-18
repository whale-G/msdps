from django.db.models import Max
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

# 引入序列化器
from .serializers import GcFileBaseSerializer, GcmsFileBaseSerializer, LcFileBaseSerializer, LcmsFileBaseSerializer
from .serializers import GcFileDetailSerializer, GcmsFileDetailSerializer, LcFileDetailSerializer, LcmsFileDetailSerializer
# 引入各处理模型
from apps.gc_dt.models import Gc_UserFiles
from apps.gcms_dt.models import Gcms_UserFiles
from apps.lc_dt.models import Lc_UserFiles
from apps.lcms_dt.models import Lcms_UserFiles
# 引入自定义异常类
from .exceptions import RecordNotFound


# 返回当前用户所有数据的信息列表
class searchForDataList(APIView):
    def get(self, request):
        try:
            user = request.user

            if not user.is_authenticated:
                return Response(
                    {"error": "Authentication required"},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # 查询所有相关模型的部分数据
            gc_files = Gc_UserFiles.objects.filter(user=user).values('process_id', 'file_type', 'created_at')
            gcms_files = Gcms_UserFiles.objects.filter(user=user).values('process_id', 'file_type', 'created_at')
            lc_files = Lc_UserFiles.objects.filter(user=user).values('process_id', 'file_type', 'created_at')
            lcms_files = Lcms_UserFiles.objects.filter(user=user).values('process_id', 'file_type', 'created_at')

            # 序列化数据
            serialized_data = []

            for item in gc_files:
                serialized_item = GcFileBaseSerializer(item).data
                serialized_data.append(serialized_item)

            for item in gcms_files:
                serialized_item = GcmsFileBaseSerializer(item).data
                serialized_data.append(serialized_item)

            for item in lc_files:
                serialized_item = LcFileBaseSerializer(item).data
                serialized_data.append(serialized_item)

            for item in lcms_files:
                serialized_item = LcmsFileBaseSerializer(item).data
                serialized_data.append(serialized_item)

            return Response({
                "status": "success",
                "result": serialized_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


# 返回指定信息的详细数据
class searchForDataDetail(APIView):
    def get(self, request):
        try:
            user = request.user

            if not user.is_authenticated:
                return Response(
                    {"error": "Authentication required"},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # 获取请求参数
            process_id = request.GET.get("process_id")
            process_type = request.GET.get("process_type")
            file_record = {}

            if process_type == "gc":
                # 查询记录
                try:
                    gc_file_record = Gc_UserFiles.objects.get(
                        user=user,
                        process_id=process_id
                    )
                except Gc_UserFiles.DoesNotExist:
                    raise RecordNotFound(detail="GC 处理记录不存在")
                # 序列化记录
                file_record = GcFileDetailSerializer(gc_file_record)
            elif process_type == "gcms":
                # 查询记录
                try:
                    gcms_file_record = Gcms_UserFiles.objects.get(
                        user=user,
                        process_id=process_id
                    )
                except Gcms_UserFiles.DoesNotExist:
                    raise RecordNotFound(detail="GCMS 处理记录不存在")
                # 序列化记录
                file_record = GcmsFileDetailSerializer(gcms_file_record)
            elif process_type == "lc":
                # 查询记录
                try:
                    lc_file_record = Lc_UserFiles.objects.get(
                        user=user,
                        process_id=process_id
                    )
                except Lc_UserFiles.DoesNotExist:
                    raise RecordNotFound(detail="LC 处理记录不存在")
                # 序列化记录
                file_record = GcmsFileDetailSerializer(lc_file_record)
            elif process_type == "lcms":
                # 查询记录
                try:
                    lcms_file_record = Lcms_UserFiles.objects.get(
                        user=user,
                        process_id=process_id
                    )
                except Lcms_UserFiles.DoesNotExist:
                    raise RecordNotFound(detail="LCMS 处理记录不存在")
                # 序列化记录
                file_record = LcmsFileDetailSerializer(lcms_file_record)
            else:
                raise ValueError("Invalid process type")

            return Response({
                "status": "success",
                "result": file_record.data
            },status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "status": "error",
                'message': str(e)
            }, status=status.HTTP_404_NOT_FOUND)


# 返回系统中数据处理的统计数据
class dataProcessStatistics(APIView):
    def get(self, request):
        try:
            user = request.user

            if not user.is_authenticated:
                return Response(
                    {"error": "Authentication required"},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # 获取当前日期
            today = timezone.now().date()

            # 待统计模型
            model_list = [Gc_UserFiles, Gcms_UserFiles, Lc_UserFiles, Lcms_UserFiles]

            # 计算各数据处理模型数据量
            model_stats = {}
            total_count = 0
            today_total_count = 0

            # 统计每个模型数据量以及总数据量
            for model in model_list:
                model_name = model.__name__
                # max_id 即 当前表中处理过的数据量总数
                max_id = model.objects.aggregate(Max('id')).get('id__max') or 0
                today_count = model.objects.filter(created_at__date=today).count()

                model_stats[model_name] = {
                    'count': max_id,
                    'today_count': today_count,
                }
                total_count += max_id
                today_total_count += today_count

            # 计算百分比
            for model_name, data in model_stats.items():
                percentage = (data['count'] / total_count) * 100 if total_count > 0 else 0
                data['percentage'] = round(percentage, 2)   # 保留两位小数

            return Response({
                'status': 'success',
                'total_count': total_count,
                'today_total_count': today_total_count,
                'model_stats': model_stats
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
