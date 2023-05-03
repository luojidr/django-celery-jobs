from django.urls import re_path
from . import views

urlpatterns = [
    re_path("^user/login$", view=views.UserLoginApi.as_view(), name='jobScheduler_login'),
    re_path("^user/token$", view=views.UserJwtTokenApi.as_view(), name='jobScheduler_token_obtain'),
    re_path("^user/info$", view=views.DetailUserApi.as_view(), name='jobScheduler_user_info'),
    re_path("^user/logout$", view=views.UserLogOutApi.as_view(), name='jobScheduler_user_logout'),
]
