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


```
``` {.python}
    
```

### Downloading and installing from source

Download the latest version of django-celery-jobs from
<http://pypi.python.org/pypi/django-celery-jobs>

You can install it by doing the following,:

    $ tar xvfz django-celery-jobs-0.0.0.tar.gz
    $ cd django-celery-jobs-0.0.0
    $ python setup.py build
    # python setup.py install

The last command must be executed as a privileged user if you are not
currently using a virtualenv.
