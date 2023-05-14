import re
import logging
import traceback
from pathlib import Path

from django.conf import settings
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin
from django.core.handlers.wsgi import WSGIHandler
from django.template.response import TemplateResponse
from django.template.backends.django import DjangoTemplates
from django.http.response import HttpResponseBase
from django.http import JsonResponse, StreamingHttpResponse, HttpResponseNotFound

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework import views as drf_views

from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.authentication import JWTAuthentication

logger = logging.getLogger("django")


def _get_traceback(exc):
    """ 获取异常信息 """
    code = None

    if isinstance(exc, APIException):
        # rest_framework.exceptions.APIException 中抛出的异常
        message_list = []
        errors = exc.args[0].serializer.errors if hasattr(exc.args[0], "serializer") else {}

        for err_key, err_msg_list in errors.items():
            msg = err_key + " -> " + "|".join(err_msg_list)
            message_list.append(msg)

        message = "\n".join(message_list) or str(exc)
    else:
        exc_args = exc.args
        message = (exc_args[1] if len(exc_args) > 1 else exc_args[0]) if exc_args else str(exc)

    return code or 5004, message


def exception_handler(exc, context):
    """
        Custom exception handling
        :param exc: exception instance
        :param context: throw exception context
        :return: Response
        """
    view = context['view']
    logger.error("drf.exceptions.exception_handler -> view: %s, exc: %s", view, exc)
    code, message = _get_traceback(exc)

    logger.error(traceback.format_exc())

    response = Response(data=dict(code=code, message=message), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return response


class MyDjangoTemplates(DjangoTemplates):
    pass


class MyJWTAuthentication(JWTAuthentication):
    def get_header(self, request):
        x_token = request.META.get(api_settings.AUTH_HEADER_NAME)  # Auth Header: Bearer eyjuew68sjdj

        if x_token:
            return x_token

        auth_header_key = api_settings.AUTH_HEADER_TYPES[0]
        x_token = request.headers.get(auth_header_key) or request.META.get(auth_header_key)

        if not x_token:
            raise InvalidToken('Path: %s not token in headers', request.path)

        return (auth_header_key + " " + x_token).encode('utf-8')


class JobResponseMiddleware(MiddlewareMixin):
    JSON_CONTENT_TYPE = 'application/json'
    resolve_request = WSGIHandler.resolve_request

    @property
    def exempt_request_path(self):
        attr = "_exempt_request_path"

        if attr not in self.__dict__:
            exempt_path_list = [
                reverse('job_index'),
                reverse('job_login'),
                reverse('job_token_obtain'),
                reverse('job_asserts', kwargs=dict(path=''))
            ]
            self.__dict__[attr] = exempt_path_list

        return self.__dict__[attr]

    def _get_response(self, request):
        callback, callback_args, callback_kwargs = self.resolve_request(request)
        response = callback(request, *callback_args, **callback_kwargs)

        if hasattr(response, 'render') and callable(response.render):
            response = response.render()

        return response

    def process_request(self, request):
        path = request.path

        if any([path.startswith(prefix_path) for prefix_path in self.exempt_request_path]):
            return self._get_response(request)

        authenticator = MyJWTAuthentication()
        request.user, _ = authenticator.authenticate(request)
        return self._get_response(request)

    def process_response(self, request, response):
        if isinstance(response, (StreamingHttpResponse, TemplateResponse, HttpResponseNotFound)):
            return response

        if isinstance(response, HttpResponseBase) and response.get("Content-Disposition"):
            return response

        try:
            content_type = response.headers.get('Content-Type')
        except AttributeError:
            content_type = getattr(response, 'accepted_media_type', None)

            if not content_type:
                if re.compile(rb"<!DOCTYPE").search(response.content):
                    content_type = 'text/plain'
                else:
                    content_type = request.META.get('CONTENT_TYPE')  # Or request.headers.get('CONTENT_TYPE')

        if self.JSON_CONTENT_TYPE not in content_type:
            return response

        data = dict(code=200, message='success', data=None)
        raw_result = response.data
        status_code = response.status_code

        # Api response
        if status.is_success(status_code):
            data.update(data=raw_result)
        else:
            data.update(
                code=raw_result.pop("code", None) or status_code,
                message=str(raw_result.pop("message", "success"))
            )

        return JsonResponse(data=data)


setattr(drf_views, 'exception_handler', exception_handler)
middleware = 'django_celery_jobs.hooks.JobResponseMiddleware'
template_backend = 'django_celery_jobs.hooks.MyDjangoTemplates'

if middleware not in settings.MIDDLEWARE:
    settings.MIDDLEWARE.insert(0, middleware)

if not any([True for template in settings.TEMPLATES if template['BACKEND'] == template_backend]):
    settings.TEMPLATES.insert(0, {
        'BACKEND': template_backend,
        'DIRS': [str(Path(__file__).parent / 'templates')],
        'APP_DIRS': False,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        }
    })
