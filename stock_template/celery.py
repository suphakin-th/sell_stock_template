from __future__ import absolute_import, unicode_literals
import logging
import os
from celery import Celery, signals, Task

from .settings import INSTALLED_APPS, TIME_ZONE, CELERY_ACKS_LATE, CELERYD_PREFETCH_MULTIPLIER, ENABLE_LOGGING, \
    RESULT_BACKEND

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stock_template.settings')
from utils.base_task import BaseAlertTask

app = Celery('stock_template')


# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.

# https://docs.celeryproject.org/en/stable/userguide/application.html
# https://docs.celeryproject.org/en/stable/userguide/configuration.html#std:setting-task_acks_late
# https://docs.celeryproject.org/en/stable/userguide/routing.html#routing-options-rabbitmq-priorities
# https://medium.com/better-programming/python-celery-best-practices-ae182730bb81
# https://github.com/vijeth-aradhya/celery-priority-tasking
# https://www.rabbitmq.com/queues.html#optional-arguments
# https://www.rabbitmq.com/consumer-priority.html
# Load task modules from all registered Django app configs.
# task_queue_max_priority -> highest priority
# celery -A xxx amqp queue.delete user
# celery -A xxx amqp queue.delete user_priority
# celery -A xxx amqp queue.delete dashboard
# celery -A xxx amqp queue.delete encode
# celery -A xxx amqp queue.delete export
# celery -A xxx amqp queue.delete config
# celery -A xxx amqp queue.delete permission

app.conf.update(
    timezone=TIME_ZONE,
    result_expires=30,
    result_backend=RESULT_BACKEND,
    task_default_priority=5,
    task_acks_late=CELERY_ACKS_LATE,
    worker_prefetch_multiplier=CELERYD_PREFETCH_MULTIPLIER,
    task_queue_max_priority=10,
)

app.Task = BaseAlertTask
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Logging
if ENABLE_LOGGING:
    @signals.setup_logging.connect
    def on_celery_setup_logging(loglevel, logfile, format, colorize, **kwargs):
        pass


def _auto_dicovery(app_name, path):
    if os.path.isdir(path):
        for _path in os.listdir(path):
            _auto_dicovery(app_name, os.path.join(path, _path))
    else:
        path_file = path.split('/')[-1]
        if (path_file.startswith('tasks') or path_file.startswith('task')) and '.pyc' not in path_file and \
                path_file.endswith('.py'):
            relate_name = path.replace((app_name + '/'), '', 1).replace('/', '.')
            app.autodiscover_tasks([app_name], related_name=relate_name)


for app_name in INSTALLED_APPS:
    if app_name.startswith('django'):
        continue
    if os.path.isdir(app_name) or os.path.isfile(app_name):
        try:
            _auto_dicovery(app_name, app_name)
        except:
            pass


@app.task(bind=True, queue='dashboard')
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
