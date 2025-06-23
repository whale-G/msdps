from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from celery.result import AsyncResult
import datetime
from .tasks import process_gc_files


class GcProcess(APIView):
    """安捷伦气相数据处理视图"""
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        """
        验证上传的安捷伦气相数据文件
        """
        user = request.user
        # 判断是否登录
        if not user.is_authenticated:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        # 获取上传的文件
        uploaded_files = request.FILES.getlist('files')
        if not uploaded_files:
            return Response({"status": "error", "message": "未检测到文件"}, status=400)

        try:
            # 检验文件类型并读取内容
            file_contents = []
            for file_obj in uploaded_files:
                if not file_obj.name.lower().endswith(('.xls', '.xlsx')):
                    # 如果不是Excel文件，则跳过
                    continue
                # 读取文件内容
                file_contents.append({
                    'name': file_obj.name,
                    'content': file_obj.read().hex()  # 将二进制内容转换为十六进制字符串
                })

            # 获取用户uuid并生成处理ID
            uuid = user.uuid
            current_time = datetime.datetime.now()
            current_time_str = (f"{current_time.year}{current_time.month}{current_time.day}"
                            f"{current_time.hour}{current_time.minute}{current_time.second}")
            process_id = f"{uuid}{current_time_str}gc"

            # 启动异步任务，任务信息存入Redis
            try:
                task = process_gc_files.delay(file_contents, str(uuid), process_id)
            except Exception as e:
                return Response({
                    "status": "error",
                    "message": "创建异步任务失败",
                    "detail": str(e)
                }, status=500)
                
            # 立即返回响应，不等待处理任务完成
            return Response({
                "status": "processing",
                "message": "文件处理已开始",
                "task_id": task.id,             # 任务ID，供后续查询
                "process_id": process_id        # 处理ID
            }, status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            return Response({
                "status": "error",
                "message": "服务器处理异常",
                "detail": str(e)
            }, status=500)


# 前端通过状态API查询进度
class GcProcessStatus(APIView):
    """查询安捷伦气相处理任务状态的视图"""
    
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

        # 从Redis获取任务结果
        task_result = AsyncResult(task_id)
        
        if task_result.ready():
            if task_result.successful():
                # 任务成功完成，直接返回任务结果，保证响应字段完整
                return Response(task_result.get())
            else:
                # 任务失败，保持与成功时相同的字段结构
                return Response({
                    "status": "failed",
                    "message": "服务器处理失败，请重试",
                    "total_files": 0,
                    "single_results": [],
                    "total_result": []
                }, status=500)
        else:
            # 任务正在进行中
            progress_info = task_result.info if task_result.state == 'PROGRESS' else {
                'current': 0,
                'total_files': 0,
                'file_name': '',
                'status': task_result.state
            }
            return Response({
                "status": "processing",
                "progress_info": progress_info
            })
