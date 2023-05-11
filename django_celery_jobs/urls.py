from django.urls import re_path
from django.views.static import serve

from . import views
from .apps import DjangoCeleryJobsConfig

API_PREFIX = 'api/job-scheduler'
APP_NAME = DjangoCeleryJobsConfig.name

urlpatterns = [
    re_path('^job-scheduler/$', view=views.IndexView.as_view(), name='job_index'),
    re_path('^jobAssets/(?P<path>.*)$', serve, {'document_root': f'{APP_NAME}/templates/jobAssets'}, name='static_asserts'),

    re_path(f"^{API_PREFIX}/user/login$", view=views.UserLoginApi.as_view(), name='jobScheduler_login'),
    re_path(f"^{API_PREFIX}/user/token$", view=views.UserJwtTokenApi.as_view(), name='jobScheduler_token_obtain'),
    re_path(f"^{API_PREFIX}/user/info$", view=views.DetailUserApi.as_view(), name='jobScheduler_user_info'),
    re_path(f"^{API_PREFIX}/user/logout$", view=views.UserLogOutApi.as_view(), name='jobScheduler_user_logout'),

    re_path(f"^{API_PREFIX}/native/job/list$", view=views.ListNativeJobApi.as_view(), name='jobScheduler_native_job_list'),
    re_path(f"^{API_PREFIX}/native/job/update$", view=views.UpdateNativeJobApi.as_view(), name='jobScheduler_native_job_update'),

    re_path(f"^{API_PREFIX}/periodic/job/cron/parse$", view=views.CronExpressionApi.as_view(), name='jobScheduler_cron_parse'),
    re_path(f"^{API_PREFIX}/periodic/job/list$", view=views.ListJobPeriodicApi.as_view(), name='jobScheduler_job_list'),
    re_path(f"^{API_PREFIX}/periodic/job/add$", view=views.CreateJobPeriodicApi.as_view(), name='jobScheduler_job_create'),
    re_path(f"^{API_PREFIX}/periodic/job/update$", view=views.UpdateDestroyJobPeriodicApi.as_view(), name='jobScheduler_job_update'),
]
