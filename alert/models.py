import datetime
import os

from django.conf import settings
from django.db import models

# class Template(models.Model):
#     code = models.CharField(max_length=120, db_index=True)
#     name = models.CharField(max_length=255)
#     is_enable = models.BooleanField(default=True)
#
#     sort = models.IntegerField(default=1, db_index=True)
#
#     class Meta:
#         ordering = ['sort']


class Alert(models.Model):
    STATUS_CHOICES = (
        (-6, 'Is Force'),
        (-5, 'Timeout'),  # Report 20 minutes
        (-4, 'Error'),
        (-3, 'File Error'),
        (-2, 'Result Delete'),
        (-1, 'Fail'),
        (0, 'Upload'),
        (1, 'Wait'),
        (2, 'Process'),
        (3, 'Success'),
        (4, 'Download')
    )

    TYPE_CHOICES = (
        (0, 'other'),
        (1, 'export'),
        (2, 'import'),
        (3, 'update')
    )

    account = models.ForeignKey('account.Account', on_delete=models.CASCADE)
    # template = models.ForeignKey(Template, null=True, blank=True, default=None, on_delete=models.CASCADE)
    code = models.CharField(max_length=255, db_index=True)
    # event-{id}.participant
    # assignment-{id}-member
    # fwd.dashboard
    # fwd.event
    # fwd.event-2.account
    # fwd.event-2.instructor
    # fwd.account
    # fwd.account-3
    # fwd.instructor
    # fwd.instructor-4
    json_kwargs = models.TextField(blank=True, default='{}')  # status
    json_result = models.TextField(blank=True, default='{}')

    # uuid in media_private/alert/%Y/%m # Old at: 2018-04-19
    input_file = models.CharField(max_length=255, blank=True)  # media_private/{ input_file }
    input_filename = models.CharField(max_length=255, blank=True)

    output_file = models.CharField(max_length=255, blank=True)
    output_filename = models.CharField(max_length=255, blank=True, db_index=True)

    log_history_file_size = models.IntegerField(default=0)

    count_row_complete = models.IntegerField(default=0)  # Update Export Report
    count_row = models.IntegerField(default=0)  # Update Export Report

    duration = models.DurationField(default=datetime.timedelta(0))
    datetime_start = models.DateTimeField(null=True, default=None)
    datetime_end = models.DateTimeField(null=True, default=None)

    is_force = models.BooleanField(default=False)
    status = models.IntegerField(choices=STATUS_CHOICES)
    task_id = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    traceback = models.TextField(blank=True, null=True, default='{}')

    action_type = models.IntegerField(choices=TYPE_CHOICES, default=0)
    module_name = models.CharField(max_length=255, db_index=True, default=None, null=True)

    datetime_create = models.DateTimeField(auto_now_add=True, db_index=True)
    datetime_update = models.DateTimeField(auto_now=True)

    class Meta:
        default_permissions = ()
        ordering = ['-datetime_create']  # Do not change

    @property
    def status_label(self):
        return self.get_status_display()

    @property
    def kwarg(self):
        import json
        try:
            return json.loads(self.json_kwargs)
        except:
            return {}

    @property
    def result(self):
        import json
        try:
            return json.loads(self.json_result)
        except:
            return {}

    @property
    def step(self):
        try:
            _step = int(self.count_row / 25)
            if _step < 10:
                return 10
            else:
                return _step
        except:
            return 10

    @property
    def log_history_filename(self):
        from utils.datetime import convert_to_local
        return 'log_%s_%s_%s.xlsx' % (self.module_name, self.id, convert_to_local(self.datetime_create).strftime('%d-%m-%Y %H-%M'))

    @property
    def log_history_file_path(self):
        filename = self.log_history_filename
        path = os.path.join(settings.BASE_DIR, 'media_private', 'alert', 'log_history')
        return '%s/%s' % (path, filename)

    @staticmethod
    def pull(code):
        return Alert.objects.filter(code=code).first()

    @staticmethod
    def pull_check(account, code, is_force=False):
        from django.utils import timezone
        import datetime

        alert = Alert.pull(code)

        if alert is None or is_force:
            is_create = True
        elif alert.datetime_create < timezone.now() - datetime.timedelta(minutes=20):
            alert.status = -5
            alert.save()
            is_create = True
        else:
            is_create = False
        if is_create:
            alert = Alert.objects.create(
                account=account,
                code=code,
                is_force=is_force,
                status=1
            )
        return alert, is_create

    @staticmethod
    def push(account, code, action_type=0, module_name=None):
        from alert.dashboard.views_import_history import broadcast_import_history_progress
        alert = Alert.pull(code)
        if alert and alert.status in [0, 1, 2]:
            alert.status = -1
            alert.action_type = action_type
            alert.module_name = module_name
            alert.save(update_fields=['status', 'action_type', 'module_name', 'datetime_update'])
        alert = Alert.objects.create(
            account=account,
            code=code,
            status=1,
            action_type=action_type,
            module_name=module_name
        )
        broadcast_import_history_progress(alert, is_new=True)
        return alert

    @staticmethod
    def pull_by_id(task_id):
        return Alert.objects.filter(task_id=task_id).first()

    @staticmethod
    def pull_in_progress(account, content_type, content_id):
        from django.utils import timezone
        import datetime
        alert = Alert.objects.filter(account=account,
                                     content_type=content_type,
                                     content_id=content_id,
                                     status__in=[-1, 1, 2, 3]).first()
        if alert is not None and timezone.now() - alert.datetime_create > datetime.timedelta(minutes=5):
            Alert.objects.filter(account=account,
                                 content_type=content_type,
                                 content_id=content_id,
                                 status__in=[1, 2, 3]).update(status=-1)
            alert = None
        return alert

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields', None)
        if self.code != 'user-management-import-user':
            if self.status in [3, 4]:
                self.count_row_complete = self.count_row
            if update_fields is not None and 'count_row_complete' not in update_fields:
                update_fields.append('count_row_complete')
        super().save(*args, **kwargs)

    def download_file(self):
        from rest_framework import status
        from utils.response_dashboard import Response
        from alert.dashboard.serializers import AlertSerializer
        from utils.file_storages import get_media_private_file

        if self.status in [3, 4]:
            response = get_media_private_file(self.output_file, self.output_filename)
            if response:
                self.status = 4
                self.save()
                return response
            else:
                self.status = -2
                self.save()
                return Response(status=status.HTTP_417_EXPECTATION_FAILED)
        else:
            return Response(AlertSerializer(self).data, status=status.HTTP_202_ACCEPTED)

    def set_task_id(self, task_id):
        self.task_id = task_id
        self.save(update_fields=['task_id'])

    def get_export_path(self):
        path = os.path.join(settings.BASE_DIR, 'alert', 'export')
        if not os.path.isdir(path):
            os.makedirs(path)
        return path

    def get_upload_path(self):
        path = os.path.join(settings.BASE_DIR, 'alert', 'upload', self.input_file)
        if not os.path.isdir(path):
            os.makedirs(path)
        return path

    def set_failed(self, traceback=''):
        from alert.dashboard.views_import_history import broadcast_import_history_progress
        from django.utils import timezone
        self.datetime_end = timezone.now()
        self.status = -1
        if self.traceback:
            self.traceback = '%s\n\n%s\n\n## Failed' % (self.traceback, traceback)
        else:
            self.traceback = traceback
        self.save(update_fields=['datetime_end', 'status', 'traceback', 'datetime_update'])
        if self.action_type == 2:
            broadcast_import_history_progress(self)

    def get_output_file(self):
        return os.path.join(settings.BASE_DIR, self.output_file)

    def get_user_filename(self):
        from django.utils import timezone

        def _prefix():
            if self.status == -3:
                return 'FILE_ERROR_LOG'
            elif self.status == -4:
                return 'ERROR_LOG'
            else:
                return 'LOG'

        current_tz = timezone.get_current_timezone()
        local = current_tz.normalize(self.datetime_create.astimezone(current_tz))

        if self.code == 'fwd.event':
            filename = 'ClassReport_'
        elif self.code == 'fwd.instructor-%d':
            filename = 'TrainerProgressReport_'
        elif self.code == 'fwd.progress-account':
            filename = 'LearnerListReport_'
        elif self.code == 'department':
            filename = '%s_[%s]_%s.log' % (
                _prefix(),
                self.input_filename,
                local.strftime('%Y%m%d_%H%M%S')
            )
            return filename
        elif self.code == 'location.report.room-detail':
            filename = 'LocationUsageReport_'
        elif self.code == 'location.report.location-list':
            filename = 'LocationReport_'
        else:
            filename = ''

        filename += local.strftime('%Y-%m-%d-%H-%M')
        return '%s.xlsx' % filename

    def get_json_result(self):
        _json_result = getattr(self, '_json_result', None)
        if _json_result:
            return _json_result
        else:
            import json
            try:
                _json_result = json.loads(self.json_result)
            except:
                _json_result = {
                    'error': 0,
                    'warning': 0
                }
            setattr(self, '_json_result', _json_result)
            return _json_result
