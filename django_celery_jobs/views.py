import logging

from django.db.models import Q
from django.contrib.auth import logout
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.contrib.auth import get_user_model, authenticate


from rest_framework.response import Response
from rest_framework.generics import GenericAPIView
from rest_framework.generics import RetrieveAPIView, ListAPIView, UpdateAPIView
from rest_framework_simplejwt.views import TokenObtainPairView

from . import serializers, models
from django_celery_jobs.tasks.task_shared_scheduler import sync_celery_native_tasks

logger = logging.getLogger('django')


class UserLoginApi(GenericAPIView):
    def post(self, request, *args, **kwargs):
        """ login api """
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

        return Response(data=None)


class UserJwtTokenApi(TokenObtainPairView):
    serializer_class = serializers.MyTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        """ Obtain user jwt token """
        return super().post(request, *args, **kwargs)


class DetailUserApi(RetrieveAPIView):
    serializer_class = serializers.UserSerializer

    def get_object(self):
        if isinstance(self.request.user, AnonymousUser):
            raise PermissionDenied("Token is invalid.")

        return self.request.user


class UserLogOutApi(GenericAPIView):
    def post(self, request, *args, **kwargs):
        """ log out """
        logout(request)
        return Response(data=None)


class ListNativeJobApi(ListAPIView):
    serializer_class = serializers.CeleryNativeTaskSerializer

    def get_queryset(self):
        name = self.request.query_params.get('name')
        task = self.request.query_params.get('task')

        native_task = sync_celery_native_tasks.name
        q = Q(('is_hidden', False), ('is_del', False), _connector='AND')

        name and q.children.append(('name__contains', name))
        task and q.children.append(('task__contains', task))

        return models.CeleryNativeTaskModel.objects.filter(~Q(task=native_task), q).all()


class UpdateNativeJobApi(UpdateAPIView):
    serializer_class = serializers.CeleryNativeTaskSerializer

    def get_object(self):
        job_id = self.request.data.get('id') or 0
        return models.CeleryNativeTaskModel.objects.get(id=job_id, is_del=False)

    def post(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

