from django_celery_jobs.jobScheduler.util import get_celery_app

celery_app = get_celery_app()


@celery_app.task
def shared_scheduler(**kwargs):
    print('shared_schedule')
