from celery import Task
import logging

from django.conf import settings as _settings
from itertools import chain, groupby

logger_celery = logging.getLogger('stock_template')


class BaseAlertTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        from alert.models import Alert
        log_data = {
            "task_id": task_id,
            "task_name": self.name,
            "return_message": exc,
            "args": args,
            "kwargs": kwargs,
            "error_info": str(einfo)
        }
        logger_celery.info(msg=log_data)
        alert = Alert.pull_by_id(task_id)
        if alert:
            alert.set_failed(einfo)

    def on_success(self, retval, task_id, args, kwargs):
        log_data = {
            "task_id": task_id,
            "task_name": self.name,
            "return_message": retval,
            "args": args,
            "kwargs": kwargs,
        }
        logger_celery.info(msg=log_data)

#
# class BaseAlertTaskWithLog(Task):
#
#     def on_failure(self, exc, task_id, args, kwargs, einfo):
#         alert = Alert.pull_by_id(task_id)
#         if alert:
#             alert.set_failed(einfo)
#             if alert.action_type == 2:
#                 broadcast_import_history_progress(alert)
#
#     def on_success(self, retval, task_id, args, kwargs):
#         from django.db import connection
#         from log.models import RequestLog
#
#         total_time = 0
#         try:
#             if len(connection.queries) == 1:
#                 if connection.queries[0]['raw_sql'].startswith('SELECT "django_session"'):
#                     pass
#         except:
#             pass
#         sql_log = []
#         unique_table = []
#         for query in connection.queries:
#             query_time = float(query.get('time'))
#             if query_time is None:
#                 query_time = query.get('duration', 0) / 1000
#             sql_log.append(query['sql'])
#             _sql = query['sql'].replace('`', '')
#             _sql_list = _sql.split('FROM')
#             _table_list = [x.split()[0] for x in _sql_list[1:]] if len(_sql_list) > 1 else []
#             unique_table.append(_table_list)
#
#             total_time += float(query_time)
#         unique_table = list(chain.from_iterable(unique_table))
#         total_table = len(set(unique_table))
#         total_query = len(connection.queries)
#         _score = ((total_query - 2) / total_table) if total_table > 0 else -1
#         score = get_score(_score)
#         result = {k: len(list(v)) for k, v in groupby(list(sorted(unique_table)), lambda x: x)}
#
#         RequestLog.objects.create(
#             account=None,
#             method='task',
#             path=self.name,
#             payload=str(result),
#             status_code='%.2f/%s/%s => %d' % (total_time, total_query, total_table, score)
#         )
#         # print('%.2f/%s/%s => %d' % (total_time, total_query, total_table, score))
#         # print(unique_table)
#         # print(sql_log)
#         print('\x1b[1;;43;30m==> %s queries run, total %s seconds    \x1b[0m' % (len(connection.queries), total_time))
#
# def get_score(_score):
#     score = 0
#     if _score <= 1:
#         score = 10
#     elif _score > 4:
#         score = 0
#     elif _score > 3.5:
#         score = 2
#     elif _score > 2.5:
#         score = 4
#     elif _score >= 2:
#         score = 5
#     elif _score > 1.8:
#         score = 6
#     elif _score > 1.5:
#         score = 7
#     elif _score > 1.25:
#         score = 8
#     elif _score > 1:
#         score = 9
#     return score