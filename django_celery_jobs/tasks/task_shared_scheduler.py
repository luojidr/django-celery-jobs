from ..jobScheduler.core.celery.utils import get_celery_app

celery_app = get_celery_app()


@celery_app.task(ignore_result=False)
def shared_scheduler(**kwargs):
    print('shared_schedule')
