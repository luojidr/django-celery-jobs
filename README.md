A distributed framework of task scheduler  based on django celery.
===============================================================

[![MIT License](https://img.shields.io/pypi/l/django-celery-jobs.svg)](https://opensource.org/licenses/MIT)
[![django-celery-jobs can be installed via wheel](https://img.shields.io/pypi/wheel/django-celery-jobs.svg)](http://pypi.python.org/pypi/django-celery-jobs/)
[![Supported Python versions.](https://img.shields.io/pypi/pyversions/django-celery-jobs.svg)](http://pypi.python.org/pypi/django-celery-jobs/)

|          |                                                  |   
| ---------|:-------------------------------------------------| 
| Version  |1.0.0                                             | 
| Web      |                                                  |  
| Download |<http://pypi.python.org/pypi/django-celery-jobs>  |  
| Source   |<https://github.com/luojidr/django-celery-jobs>   | 
| Keywords |django, celery, jobs scheduler                    | 


About
-----

A distributed framework of task scheduler  based on django celery. Manages periodic tasks and sends messages to the broker

Installation
------------

You can install django-celery-jobs either via the Python Package Index
(PyPI) or from source.

To install using **pip**:

``` {.sh}
$ pip install -U django-celery-jobs
```

and then add it to your installed apps:

``` {.python}
INSTALLED_APPS = [
    ...,
    'django_celery_jobs', 
    ...,
]

from django.urls import path

urlpatterns = [
    ...,
    path('', include('django_celery_jobs.urls'))
]

CELERY_APP = '<your_project>.config.celery:celery_app'




```
``` {.python}
    
```

中间件中 process_response  需要豁免的请求
from django.urls import reverse

exempt_request_path = [
    reverse('job_index'),
    '/jobAssets/',
]


Errors:  
(1): Celery beat start :  
```
    File "D:\workplace\py_workship\django-celery-jobs\venv\lib\site-packages\celery\bin\beat.py", line 72, in beat
        return beat().run()
    File "D:\workplace\py_workship\django-celery-jobs\venv\lib\site-packages\celery\apps\beat.py", line 77, in run
        self.start_scheduler()
    File "D:\workplace\py_workship\django-celery-jobs\venv\lib\site-packages\celery\apps\beat.py", line 105, in start_scheduler
        service.start()
    File "D:\workplace\py_workship\django-celery-jobs\venv\lib\site-packages\celery\beat.py", line 651, in start
        self.scheduler._do_sync()
    ......
    File "D:\workplace\py_workship\django-celery-jobs\venv\lib\site-packages\django\db\backends\mysql\operations.py", line 268, in adapt_datetimefield_value
        raise ValueError(
    ValueError: MySQL backend does not support timezone-aware datetimes when USE_TZ is False.
```  

celery conf:  
 ```python
    timezone = 'Asia/Shanghai'  
    enable_utc = False 
```  
django conf:  
```python
    DJANGO_CELERY_BEAT_TZ_AWARE  = False
```
