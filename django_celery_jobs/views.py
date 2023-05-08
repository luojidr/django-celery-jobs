import json
import logging

import croniter

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
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


class CronExpressionApi(APIView):
    @staticmethod
    def get_run_next_time_list(cron_expr, max_run_cnt, job_id=None):
        cron_expr_list = [s.strip() for s in cron_expr.split(" ") if s.strip()]
        if len(cron_expr_list) != 5:
            return Response(data=dict(data=[], code=6001, message='Cron表达式格式错误'))

        dt_fmt = "%Y-%m-%d %H:%M:%S"
        job = models.JobPeriodicModel.objects.filter(id=job_id or 0, is_del=False).first()

        if job:
            first_time = job.first_run_time
            start_time = timezone.datetime.strptime(first_time, dt_fmt) if first_time else timezone.datetime.now()
        else:
            start_time = timezone.datetime.now()

        run_time_list = []
        cron = croniter.croniter(" ".join(cron_expr_list), start_time)

        # 显示最近10次执行时间
        for i in range(max_run_cnt):
            next_run_time = cron.get_next(timezone.datetime)
            run_time_list.append(next_run_time.strftime(dt_fmt))

        return run_time_list

    def get(self, request, *args, **kwargs):
        job_id = request.query_params.get('job_id', 0)
        expression = request.query_params.get('cron_expr', '')
        max_run_cnt = int(request.query_params.get('max_run_cnt')) or 10

        run_time_list = self.get_run_next_time_list(expression, max_run_cnt, job_id=job_id)
        return Response(data=run_time_list)


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
        native_job_id = serializer.initial_data['native_job_id']
        native_job = models.CeleryNativeTaskModel.objects.get(id=native_job_id)

        beat_task_name = native_job.task
        beat_task_obj = models.BeatPeriodicTaskModel.objects.get(name=beat_task_name, enabled=True)

        cron_expr = serializer.initial_data['cron_expr']
        trigger = CronTrigger.from_crontab(expr=cron_expr)
        crontab_id = trigger.get_trigger_schedule()['crontab_id']

        # Other kwargs
        max_run_cnt = serializer.validated_data.get('max_run_cnt', 0)
        is_enabled = serializer.validated_data.get('is_enabled', False)
        run_next_time_list = CronExpressionApi.get_run_next_time_list(cron_expr, max_run_cnt)
        kwargs = dict(
            periodic_task_id=beat_task_obj.id,
            first_run_time=timezone.datetime.now(),
            deadline_run_time=None if not max_run_cnt
            else timezone.datetime.strptime(run_next_time_list[-1], "%Y-%m-%d %H:%M:%S")
        )

        with transaction.atomic():
            current_now = timezone.datetime.now()
            simple_task_name = beat_task_name.rsplit('.', 1)[-1] + current_now.strftime("_%Y%m%d%H%M%S_%f")

            job_obj = serializer.save(**kwargs)

            periodic_task_obj = models.BeatPeriodicTaskModel.objects.create(
                name=simple_task_name, task=beat_task_name,
                enabled=is_enabled, crontab_id=crontab_id,
                kwargs=json.dumps(dict(job_id=job_obj.id)),
            )

            job_obj.periodic_task_id = periodic_task_obj.id
            job_obj.save()


class UpdateDestroyJobPeriodicApi(GenericAPIView):
    serializer_class = serializers.JobPeriodicSerializer

    def post(self, request, *args, **kwargs):
        pass
