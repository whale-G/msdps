import re
from django.contrib.auth.hashers import make_password, check_password
from django.core.validators import validate_email
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework_simplejwt.tokens import RefreshToken

from django.db.models import Q
from .models import Users
from .serializers import UsersSerializer


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
                return Response({
                    "status": "error",
                    "message": "请输入账号或者密码"
                }, status=status.HTTP_400_BAD_REQUEST)

            # 校验账号是否合法
            if account_type == 'phone':
                # 基础正则校验（中国手机号）
                if not re.match(r'^1[3-9]\d{9}$', user_account):
                    return Response({
                        'status': 'error',
                        'message': '手机号格式错误'
                    }, status=status.HTTP_400_BAD_REQUEST)
            elif account_type == 'email':
                try:
                    validate_email(user_account)  # 使用Django内置验证
                except Exception:
                    return Response({
                        'status': 'error',
                        'message': '邮箱格式错误'
                    }, status=status.HTTP_400_BAD_REQUEST)

            # 检查是否重复注册
            if Users.objects.filter(user_account=user_account).exists():
                return Response({
                    'status': 'error',
                    'message': '账号已注册'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 基础正则校验密码（8-16位，包含大小写和数字，允许特殊字符）
            if not re.match(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)[A-Za-z\d!@#$%^&*()]{8,16}$', user_password):
                return Response({
                    'status': 'error',
                    'message': '密码不符合要求'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 使用create_user创建用户（自动处理密码哈希）
            Users.objects.create_user(
                user_account=user_account,
                password=user_password      # 传入明文密码
            )

            return Response({
                "status": "success",
                "message": "注册成功"
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


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
                return Response({
                    "status": "error",
                    "message": "账号或密码不能为空"
                }, status=status.HTTP_400_BAD_REQUEST)

            # 检查用户是否存在
            try:
                user = Users.objects.get(user_account=user_account)
                # 检查用户是否被删除
                if user.is_delete:
                    return Response({
                        "status": "error",
                        "code": "user_deleted",
                        "message": "该账号已被删除，请联系管理员"
                    }, status=status.HTTP_403_FORBIDDEN)
            except Exception:
                return Response({
                    "status": "error",
                    "message": "账号不存在"
                }, status=status.HTTP_400_BAD_REQUEST)

            # 验证密码
            if not check_password(password=user_password, encoded=user.password):  # 对比哈希值
                return Response({
                    "status": "error",
                    "message": "密码错误"
                }, status=status.HTTP_400_BAD_REQUEST)

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
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


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
                return Response({
                    "status": "error",
                    "message": "旧密码或新密码不能为空"
                }, status=status.HTTP_400_BAD_REQUEST)

            # 验证旧密码
            user = request.user  # 从Token中自动解析的用户对象
            if not check_password(old_password, user.password):
                return Response({
                    "status": "error",
                    "message": "原密码错误"
                }, status=status.HTTP_400_BAD_REQUEST)

            # 基础正则校验新密码（8-16位，包含大小写和数字，允许特殊字符）
            if not re.match(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)[A-Za-z\d!@#$%^&*()]{8,16}$', new_password):
                return Response({
                    'status': 'error',
                    'message': '密码不符合要求'
                }, status=status.HTTP_400_BAD_REQUEST)
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
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


# 管理员获取系统用户列表
class UserListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        """
        获取用户列表，支持分页和搜索
        GET /admin/users/
        参数：
        - page: 页码（默认1）
        - size: 每页数量（默认10）
        - search: 搜索关键词（用户名/账号）
        """
        try:
            page = int(request.query_params.get('page', 1))
            size = int(request.query_params.get('size', 10))
            search = request.query_params.get('search', '')

            # 构建查询
            queryset = Users.objects.all()  # 获取所有用户
            if search:
                queryset = queryset.filter(
                    Q(user_account__icontains=search) |     # 使用user_account替代username
                    Q(user_name__icontains=search)          # 对user_name的搜索
                )

            total = queryset.count()

            # 分页
            start = (page - 1) * size
            end = start + size
            users = queryset[start:end]

            # 序列化
            serializer = UsersSerializer(users, many=True)

            return Response({
                'status': 'success',
                'total': total,
                'results': serializer.data
            })
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'获取用户列表失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 管理员新增用户
class UserCreateView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        """
        创建新用户
        POST /admin/users/create/
        请求体：
        {
            "user_account": "string",    # 必填，用户账号（手机号或邮箱）
            "password": "string",        # 必填，密码
            "is_superuser": boolean,     # 必填，是否为管理员
        }
        """
        try:
            # 检查用户账号是否已存在
            user_account = request.data.get('user_account')
            if Users.objects.filter(user_account=user_account).exists():
                return Response({
                    'status': 'error',
                    'message': f'用户账号 {user_account} 已存在'
                }, status=status.HTTP_400_BAD_REQUEST)

            serializer = UsersSerializer(data=request.data)
            if serializer.is_valid():
                # 创建用户
                serializer.save()
                return Response({
                    'status': 'success',
                    'message': '创建用户成功',
                    'data': serializer.data
                }, status=status.HTTP_201_CREATED)

            return Response({
                'status': 'error',
                'message': '数据验证失败',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'创建用户失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 管理员删除用户（逻辑删除）
class UserDeleteView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, uuid):
        """
        逻辑删除用户
        POST /admin/users/<uuid:uuid>/delete/
        """
        try:
            user = Users.objects.get(uuid=uuid, is_delete=False)

            # 不允许删除超级管理员
            if user.is_superuser:
                return Response({
                    'status': 'error',
                    'message': '不能删除超级管理员账户'
                }, status=status.HTTP_403_FORBIDDEN)

            # 不允许删除自己
            if user == request.user:
                return Response({
                    'status': 'error',
                    'message': '不能删除当前登录的账户'
                }, status=status.HTTP_403_FORBIDDEN)

            # 逻辑删除
            user.is_delete = True
            user.save()

            return Response({
                'status': 'success',
                'message': '删除用户成功'
            })

        except Users.DoesNotExist:
            return Response({
                'status': 'error',
                'message': '用户不存在'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'删除用户失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 管理员更新用户信息
class UserUpdateView(APIView):
    permission_classes = [IsAdminUser]

    def put(self, request, uuid):
        """
        更新用户信息
        PUT /admin/users/<uuid:uuid>/update/
        请求体：
        {
            "user_account": "string",    # 选填：用户账号
            "is_superuser": boolean,     # 选填，是否为管理员
            "password": "string"         # 选填，新密码
        }
        """
        try:
            user = Users.objects.get(uuid=uuid, is_delete=False)

            # 不允许修改超级管理员的管理员权限
            if user.is_superuser and 'is_superuser' in request.data:
                return Response({
                    'status': 'error',
                    'message': '不能修改超级管理员的权限'
                }, status=status.HTTP_403_FORBIDDEN)

            # 如果要修改管理员权限，确保至少保留一个管理员
            if 'is_superuser' in request.data and not request.data['is_superuser']:
                admin_count = Users.objects.filter(
                    is_superuser=True,
                    is_delete=False
                ).exclude(uuid=uuid).count()
                if admin_count == 0:
                    return Response({
                        'status': 'error',
                        'message': '系统必须至少保留一个管理员账户'
                    }, status=status.HTTP_403_FORBIDDEN)

            serializer = UsersSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'status': 'success',
                    'message': '更新用户信息成功',
                    'data': serializer.data
                })

            return Response({
                'status': 'error',
                'message': '数据验证失败',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        except Users.DoesNotExist:
            return Response({
                'status': 'error',
                'message': '用户不存在'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'更新用户信息失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
