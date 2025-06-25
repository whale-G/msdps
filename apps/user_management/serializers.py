from rest_framework import serializers
from .models import Users


class UsersSerializer(serializers.ModelSerializer):
    class Meta:
        model = Users
        fields = [
            'uuid',                     # 主键
            'user_name',                # 用户昵称
            'user_account',             # 账号
            'avatar_url',               # 头像
            'is_staff',                 # 是否为管理员
            'is_delete',                # 是否删除
            'created_at',               # 创建时间
            'force_password_change'     # 是否强制修改密码
        ]
        read_only_fields = ['uuid', 'created_at']   # 这些字段只读，不允许修改
        extra_kwargs = {
            'password': {'write_only': True}        # 密码字段只写，不会在返回数据中显示
        }

    def create(self, validated_data):
        """创建用户时的特殊处理"""
        password = validated_data.pop('password', None)
        user = Users.objects.create_user(
            user_account=validated_data.pop('user_account'),
            password=password,
            **validated_data
        )
        return user

    def update(self, instance, validated_data):
        """更新用户时的特殊处理"""
        # 如果更新包含密码，需要特殊处理
        if 'password' in validated_data:
            password = validated_data.pop('password')
            instance.set_password(password)

        # 更新其他字段
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance

    def to_representation(self, instance):
        """自定义返回数据的格式"""
        data = super().to_representation(instance)
        # 添加一些计算字段或格式化数据
        data['created_at'] = instance.created_at.strftime('%Y-%m-%d %H:%M:%S')
        return data
