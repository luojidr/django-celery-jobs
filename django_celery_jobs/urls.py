from django.urls import re_path
from . import views

urlpatterns = [
    re_path("^user/login$", view=views.UserLoginApi.as_view(), name='jobScheduler_login'),
    re_path("^user/token$", view=views.UserJwtTokenApi.as_view(), name='jobScheduler_token_obtain'),
    re_path("^user/info$", view=views.DetailUserApi.as_view(), name='jobScheduler_user_info'),
    re_path("^user/logout$", view=views.UserLogOutApi.as_view(), name='jobScheduler_user_logout'),

    re_path("^native/job/list$", view=views.ListNativeJobApi.as_view(), name='jobScheduler_native_job_list'),
    re_path("^native/job/update$", view=views.UpdateNativeJobApi.as_view(), name='jobScheduler_native_job_update'),

    # 周期性人物
    re_path("^periodic/job/cron/parse$", view=views.CronExpressionApi.as_view(), name='jobScheduler_cron_parse'),
    re_path("^periodic/job/list$", view=views.ListJobPeriodicApi.as_view(), name='jobScheduler_job_list'),
    re_path("^periodic/job/add$", view=views.CreateJobPeriodicApi.as_view(), name='jobScheduler_job_create'),
    re_path("^periodic/job/update$", view=views.UpdateDestroyJobPeriodicApi.as_view(), name='jobScheduler_job_update_delete'),
]
