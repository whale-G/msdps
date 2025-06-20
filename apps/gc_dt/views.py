from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from celery.result import AsyncResult
import datetime
import xlrd3 as xlrd
from .models import Gc_UserFiles
from .tasks import process_gc_files


class GcProcess(APIView):
    """气相色谱数据处理视图"""
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        """
        处理上传的气相色谱数据文件
        """
        user = request.user
        # 判断是否登录
        if not user.is_authenticated:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # 获取用户uuid并生成处理ID
        uuid = user.uuid
        current_time = datetime.datetime.now()
        current_time_str = (f"{current_time.year}{current_time.month}{current_time.day}"
                          f"{current_time.hour}{current_time.minute}{current_time.second}")
        process_id = f"{uuid}{current_time_str}gc"

        # 获取上传的文件
        uploaded_files = request.FILES.getlist('files')
        if not uploaded_files:
            return Response({"status": "error", "message": "未检测到文件"}, status=400)

        try:
            # 检验文件类型并读取内容
            file_contents = []
            for file_obj in uploaded_files:
                if not file_obj.name.lower().endswith(('.xls', '.xlsx')):
                    return Response({
                        "status": "error",
                        "message": f"文件 {file_obj.name} 不是Excel文件"
                    }, status=400)
                
                # 读取文件内容
                file_contents.append({
                    'name': file_obj.name,
                    'content': file_obj.read()
                })

            # 启动异步任务
            task = process_gc_files.delay(file_contents, str(user.uuid), process_id)

            return Response({
                "status": "processing",
                "message": "文件处理已开始",
                "task_id": task.id,
                "process_id": process_id
            }, status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            return Response({
                "status": "error",
                "message": "服务器处理异常",
                "detail": str(e)
            }, status=500)


class GcProcessStatus(APIView):
    """查询处理任务状态的视图"""
    
    def get(self, request):
        """
        获取任务处理状态
        """
        task_id = request.query_params.get('task_id')
        if not task_id:
            return Response({
                "status": "error",
                "message": "缺少task_id参数"
            }, status=400)

        # 获取任务结果
        task_result = AsyncResult(task_id)
        
        if task_result.ready():
            if task_result.successful():
                # 任务成功完成
                result = task_result.get()
                return Response({
                    "status": "completed",
                    "result": result
                })
            else:
                # 任务失败
                return Response({
                    "status": "failed",
                    "error": str(task_result.result)
                }, status=500)
        else:
            # 任务正在进行中
            if task_result.state == 'PROGRESS':
                return Response({
                    "status": "processing",
                    "progress": task_result.info
                })
            return Response({
                "status": "processing",
                "state": task_result.state
            })
