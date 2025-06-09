import re
from django.contrib.auth.hashers import make_password, check_password
from django.core.validators import validate_email
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Users


# 用户注册
class UserRegister(APIView):
    parser_classes = [JSONParser]

    def post(self, request):
        try:
            # 获取用户数据
            user_account = request.data.get('user_account', '').strip()
            account_type = request.data.get('account_type', '')
            user_password = request.data.get('password', '').strip()
            # 校验非空
            if user_account == '' or user_password == '':
                return Response({"status": "error", "message": "请输入账号或者密码"}, status=400)
            # 校验账号是否合法
            if account_type == 'phone':
                # 基础正则校验（中国手机号）
                if not re.match(r'^1[3-9]\d{9}$', user_account):
                    return Response({'code': 400, 'message': '手机号格式错误'})
            elif account_type == 'email':
                try:
                    validate_email(user_account)  # 使用Django内置验证
                except Exception:
                    return Response({'code': 400, 'message': '邮箱格式错误'})
            # 检查是否重复注册
            if Users.objects.filter(user_account=user_account).exists():
                return Response({'code': 400, 'message': '账号已注册'})
            # 基础正则校验密码（8-16位，包含大小写和数字，允许特殊字符）
            if not re.match(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)[A-Za-z\d!@#$%^&*()]{8,16}$', user_password):
                return Response({'code': 400, 'message': '密码不符合要求'})

            # 使用create_user创建用户（自动处理密码哈希）
            Users.objects.create_user(
                user_account=user_account,
                password=user_password      # 传入明文密码
            )

            return Response({"status": "success", "message": "注册成功"})

        except Exception as e:
            return Response({"status": "error", "message": str(e)})


# 用户登录
class UserLogin(APIView):
    parser_classes = [JSONParser, MultiPartParser]

    def post(self, request):
        try:
            # 获取用户输入
            user_account = request.data.get('user_account', '').strip()
            user_password = request.data.get('password', '').strip()
            # 非空检查
            if not user_account or not user_password:
                return Response({"message": "账号或密码不能为空"}, status=status.HTTP_400_BAD_REQUEST)
            # 检查用户是否存在
            try:
                user = Users.objects.get(user_account=user_account)
            except Exception:
                return Response({"message": "账号不存在"}, status=status.HTTP_400_BAD_REQUEST)
            # 验证密码
            if not check_password(password=user_password, encoded=user.password):  # 对比哈希值
                return Response({"message": "密码错误"}, status=status.HTTP_400_BAD_REQUEST)

            # 生成JWT Token
            refresh = RefreshToken.for_user(user)
            # 将user_id写入token负载
            refresh['uuid'] = str(user.uuid)

            return Response({
                "status": "success",
                "message": "登录成功",
                "access": str(refresh.access_token),    # 短期Token
                "refresh": str(refresh),                # 长期Token（用于刷新）
                "force_password_change": user.force_password_change  # 返回强制修改密码标志
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"status": "error", "message": str(e)})


# 修改密码
class ChangePassword(APIView):
    permission_classes = [IsAuthenticated]  # 必须登录后才可以使用

    def post(self, request):
        try:
            # 获取参数
            old_password = request.data.get('old_password', '').strip()
            new_password = request.data.get('new_password', '').strip()

            # 校验非空
            if not old_password or not new_password:
                return Response({"message": "旧密码或新密码不能为空"}, status=status.HTTP_400_BAD_REQUEST)

            # 验证旧密码
            user = request.user  # 从Token中自动解析的用户对象
            if not check_password(old_password, user.password):
                return Response({"message": "旧密码错误"}, status=status.HTTP_400_BAD_REQUEST)

            # 基础正则校验新密码（8-16位，包含大小写和数字，允许特殊字符）
            if not re.match(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)[A-Za-z\d!@#$%^&*()]{8,16}$', new_password):
                return Response({'code': 400, 'message': '密码不符合要求'})
            # 更新密码并保存
            user.password = make_password(new_password)

            # 如果是强制修改密码，清除标志
            if user.force_password_change:
                user.force_password_change = False

            user.save()

            return Response({
                "status": "success",
                "message": "密码修改成功",
                "force_password_change": user.force_password_change  # 返回更新后的状态
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"status": "error", "message": str(e)})
