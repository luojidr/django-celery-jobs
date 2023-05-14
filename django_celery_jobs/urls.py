import pathlib

from django.urls import re_path
from django.views.static import serve

from . import views

API_PREFIX = 'api/job-scheduler'
DOCUMENT_ROOT = '%s/templates/jobAssets' % str(pathlib.Path(__file__).parent)


urlpatterns = [
    re_path('^job-scheduler/$', view=views.JobIndexView.as_view(), name='job_index'),
    re_path('^jobAssets/(?P<path>.*)$', serve, {'document_root': DOCUMENT_ROOT}, name='job_asserts'),

    re_path(f"^job-scheduler/user/login$", view=views.JobUserLoginApi.as_view(), name='job_login'),
    re_path(f"^{API_PREFIX}/user/token$", view=views.JobUserJwtTokenApi.as_view(), name='api_job_token_obtain'),
    re_path(f"^{API_PREFIX}/user/info$", view=views.DetailJobUserApi.as_view(), name='api_job_user_info'),
    re_path(f"^{API_PREFIX}/user/logout$", view=views.JobUserLogOutApi.as_view(), name='api_job_user_logout'),

    re_path(f"^{API_PREFIX}/native/job/list$", view=views.ListNativeJobApi.as_view(), name='api_job_native_list'),
    re_path(f"^{API_PREFIX}/native/job/update$", view=views.UpdateNativeJobApi.as_view(), name='api_job_native_update'),

    re_path(f"^{API_PREFIX}/periodic/job/cron/parse$", view=views.CronExpressionApi.as_view(), name='api_job_cron_parse'),
    re_path(f"^{API_PREFIX}/periodic/job/list$", view=views.ListJobPeriodicApi.as_view(), name='api_job_list'),
    re_path(f"^{API_PREFIX}/periodic/job/add$", view=views.CreateJobPeriodicApi.as_view(), name='api_job_create'),
    re_path(f"^{API_PREFIX}/periodic/job/update$", view=views.UpdateDestroyJobPeriodicApi.as_view(), name='api_job_update'),
]
