import logging
import traceback

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.template.response import TemplateResponse
from django.http import JsonResponse, StreamingHttpResponse, HttpResponseBase, HttpResponseNotFound

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


class MyJWTAuthentication(JWTAuthentication):
    def get_header(self, request):
        key = api_settings.AUTH_HEADER_TYPES[0]
        x_token = request.headers.get(key)

        if not x_token:
            raise InvalidToken('Path: %s not token in headers', request.path)

        return (key + " " + x_token).encode('utf-8')


class ResponseMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        if isinstance(response, (StreamingHttpResponse, TemplateResponse, HttpResponseNotFound)):
            return response

        if isinstance(response, HttpResponseBase) and response.get("Content-Disposition"):
            return response

        if 'application/json' not in response.headers.get('Content-Type'):
            return response

        data = dict(code=200, message='ok', data=None)
        raw_result = response.data

        # Api response
        if status.is_success(response.status_code):
            data.update(data=raw_result)
        else:
            data.update(
                code=raw_result.pop("code", None) or response.status_code,
                message=str(raw_result.pop("message", ""))
            )

        return JsonResponse(data=data)


setattr(drf_views, 'exception_handler', exception_handler)
JWTAuthentication.get_header = MyJWTAuthentication.get_header

middleware = 'django_celery_jobs.hooks.ResponseMiddleware'
if middleware not in settings.MIDDLEWARE:
    settings.MIDDLEWARE.append(middleware)


