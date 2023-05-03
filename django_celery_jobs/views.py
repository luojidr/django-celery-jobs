import logging

from django.contrib.auth import logout
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.contrib.auth import get_user_model, authenticate

from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from rest_framework.generics import RetrieveAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import MyTokenObtainPairSerializer, UserSerializer
from .jobScheduler.scheduler import default_scheduler

logger = logging.getLogger('django')


class UserLoginApi(GenericAPIView):
    def post(self, request, *args, **kwargs):
        """ login api """
        data = dict(code=200, message='ok')
        login_form = request.data

        try:
            User = get_user_model()
            username_field = User._meta.get_field(User.USERNAME_FIELD)
            credentials = {
                username_field.name: login_form['username'],
                'password': login_form['password']
            }
            user = authenticate(request, **credentials)

            if user is None:
                raise PermissionDenied('')
        except Exception as e:
            msg = 'Username: %s or Password is incorrect.' % login_form['username']
            logger.error(msg + " Error: %s", e)
            data.update(code=500, message=msg)

        return Response(data=data)


class UserJwtTokenApi(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        """ Obtain user jwt token
        data(Standard format):
            {
                'code': 200,
                'message': 'ok,
                'data': None
            }
        """
        response = super().post(request, *args, **kwargs)
        token_data = response.data

        if token_data.get('token'):
            data = dict(code=200, message='ok', data=token_data)
        else:
            data = dict(code=5001, message=token_data.get('detail', ''), data=None)

        return Response(data=data)


class DetailUserApi(RetrieveAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        if isinstance(self.request.user, AnonymousUser):
            raise PermissionDenied("Token is invalid.")

        return self.request.user


class UserLogOutApi(GenericAPIView):
    def post(self, request, *args, **kwargs):
        """ log out """
        logout(request)
        return Response(data=dict(code=200, message='ok', data=None))


class ListNativeJobApi(ListAPIView):
    def get(self, request, *args, **kwargs):
        """ native task list """
        # tasks = default_scheduler.get_celery_native_tasks()
        # return Response(data=dict(code=200, message='ok', data=tasks))



