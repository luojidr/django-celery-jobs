from django.contrib.auth import get_user_model

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from . import models


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)

        refresh_token = data.pop('refresh')
        data["token"] = data.pop('access')

        return data


class UserSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()
    name = serializers.CharField(source='username')  # 将 orm 中 username 字段重命名为 name

    class Meta:
        model = get_user_model()
        fields = ['name', 'is_superuser', 'avatar']

    def get_avatar(self, obj):
        return 'https://wpimg.wallstcn.com/f778738c-e4f8-4870-b634-56703b4acafe.gif'


class CeleryNativeTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CeleryNativeTaskModel
        fields = model.fields()
