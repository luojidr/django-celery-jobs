import logging

from django.shortcuts import render
from django.views.generic import TemplateView
from django.db.models import Q
from django.db import transaction
from django.contrib.auth import logout
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.contrib.auth import get_user_model, authenticate


from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from rest_framework.generics import RetrieveAPIView, ListAPIView, UpdateAPIView, CreateAPIView
from rest_framework_simplejwt.views import TokenObtainPairView

from . import serializers, models
from .jobScheduler.trigger.cron import CronTrigger
from .jobScheduler.utils import get_trigger_next_range
from django_celery_jobs.tasks.task_synchronous_jobs import sync_celery_native_tasks

logger = logging.getLogger('django')


class IndexView(TemplateView):
    # template_name = ''
    template_name = 'index.html'


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


class CronExpressionApi(APIView):
    def get(self, request, *args, **kwargs):
        job_id = request.query_params.get('job_id', 0)
        expression = request.query_params.get('cron_expr', '')
        max_run_cnt = int(request.query_params.get('max_run_cnt'))

        trigger = CronTrigger.from_crontab(expression)
        job = models.JobPeriodicModel.objects.filter(id=job_id or 0, is_del=False).first()
        run_next_range = get_trigger_next_range(trigger, start_time=job and job.first_run_time, run_times=max_run_cnt)

        return Response(data=run_next_range)


class ListJobPeriodicApi(ListAPIView):
    serializer_class = serializers.JobPeriodicSerializer

    def get_queryset(self):
        query_params = self.request.query_params
        title = query_params.get('title')
        remark = query_params.get('remark')

        q = Q(('is_del', False), _connector='AND')
        title and q.children.append(('title__contains', title))
        remark and q.children.append(('remark__contains', remark))

        return models.JobPeriodicModel.objects.filter(q).select_related("periodic_task")


class CreateJobPeriodicApi(CreateAPIView):
    serializer_class = serializers.JobPeriodicSerializer

    def perform_create(self, serializer):
        self.serializer_class.Meta.model.perform_save(serializer)


class UpdateDestroyJobPeriodicApi(UpdateAPIView):
    serializer_class = serializers.JobPeriodicSerializer

    def get_object(self):
        job_id = int(self.request.data.get('id') or 0)
        return models.JobPeriodicModel.objects.get(id=job_id, is_del=False)

    def perform_update(self, serializer):
        self.serializer_class.Meta.model.perform_save(serializer)

    def set_enabled(self, request, *args, **kwargs):
        job_id = int(self.request.data.get('id') or 0)
        is_enabled = self.request.data.get('is_enabled')
        job = models.JobPeriodicModel.objects.filter(id=job_id, is_del=False).first()

        if not job:
            return Response(data=dict(message=f'任务<id:{job_id}>不存在', code=6007))

        with transaction.atomic():
            job.is_enabled = is_enabled
            job.periodic_task.enabled = is_enabled

            job.periodic_task.save()
            job.save()

        action = is_enabled and "启动" or "暂停"
        return Response(data=dict(message=f'{action}任务<id:{job_id}>成功'))

    def delete(self, request, *args, **kwargs):
        job_id = int(self.request.data.get('id') or 0)
        job = models.JobPeriodicModel.objects.filter(id=job_id, is_del=False).first()

        if not job:
            return Response(data=dict(message=f'任务<id:{job_id}>不存在', code=6008))

        with transaction.atomic():
            job.is_del = False
            job.is_enabled = False
            job.periodic_task.enabled = False

            job.periodic_task.save()
            job.save()

        return Response(data=dict(message=f'删除任务<id:{job_id}>成功'))

    def post(self, request, *args, **kwargs):
        action = request.data.get('action')
        assert hasattr(self, action), '不合法的操作'

        return getattr(self, action)(request, *args, **kwargs)

