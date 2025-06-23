import datetime
from celery.result import AsyncResult
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from .tasks import process_lc_shimazu_files, process_lc_agilent_files


class LcProcessShimazu(APIView):
    """岛津液相数据处理视图"""
    parser_classes = [MultiPartParser, FormParser]

    # 岛津液相lc30&2030
    def post(self, request):
        """
        验证上传的岛津液相数据文件
        """
        user = request.user
        # 判断是否登录
        if not user.is_authenticated:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED
            )


        # 获取所有上传文件对象
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

            # 获取用户uuid
            uuid = user.uuid
            # 生成本次处理记录的id（系统唯一）
            process_id = ""
            current_time = datetime.datetime.now()
            current_time_str = str(current_time.year) + str(current_time.month) + str(current_time.day) + str(
                current_time.hour) + str(current_time.minute) + str(current_time.second)
            process_id = str(uuid) + current_time_str + "lc"
            # 获取用户设置的RT浮动参数（默认为0.1）
            float_parameter = float(request.data.get("float_parameter"))

            # 启动异步任务，任务信息存入Redis
            try:
                task = process_lc_shimazu_files.delay(file_contents, str(uuid), process_id, float_parameter)
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
                "task_id": task.id,         # 任务ID，供后续查询
                "process_id": process_id    # 处理ID
            }, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            return Response({
                "status": "error",
                "message": "服务器处理异常",
                "detail": str(e)
            }, status=500)


class LcProcessShimazuStatus(APIView):
    """查询岛津液相处理任务状态的视图"""

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
                    "message": str(task_result.result),
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


class LcProcessAgilent(APIView):
    """安捷伦液相数据处理视图"""
    parser_classes = [MultiPartParser, FormParser]

    # 安捷伦液相（1290）
    def post(self, request):
        """
        验证上传的安捷伦液相数据文件
        """
        user = request.user
        # 判断是否登录
        if not user.is_authenticated:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # 获取所有上传文件对象
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

            # 获取用户uuid
            uuid = user.uuid
            # 生成本次处理记录的id（系统唯一）
            process_id = ""
            current_time = datetime.datetime.now()
            current_time_str = str(current_time.year) + str(current_time.month) + str(current_time.day) + str(
                current_time.hour) + str(current_time.minute) + str(current_time.second)
            process_id = str(uuid) + current_time_str + "lc"
            # 获取用户设置的RT浮动参数（默认为0.1）
            float_parameter = float(request.data.get("float_parameter"))

            # 启动异步任务，任务信息存入Redis
            try:
                task = process_lc_agilent_files.delay(file_contents, str(uuid), process_id, float_parameter)
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
                "task_id": task.id,  # 任务ID，供后续查询
                "process_id": process_id  # 处理ID
            }, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            return Response({
                "status": "error",
                "message": "服务器处理异常",
                "detail": str(e)
            }, status=500)


class LcProcessAailentStatus(APIView):
    """查询安捷伦液相处理任务状态的视图"""

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
                    "message": str(task_result.result),
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
