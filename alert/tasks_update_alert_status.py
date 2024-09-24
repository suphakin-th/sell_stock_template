from celery import shared_task

from alert.models import Alert
from django.utils import timezone
from datetime import timedelta


@shared_task(bind=True, queue='dashboard')
def task_update_alert_status(self):
    processing_alert = Alert.objects.filter(status=2, datetime_update__lte=timezone.now() - timedelta(hours=24)).exclude(code='progress_account.report.export-summary')
    for alert in processing_alert:
        alert.datetime_end = timezone.now()
        if alert.datetime_start:
            alert.duration = alert.datetime_end - alert.datetime_start
        alert.status = -5
        alert.save(update_fields=['status', 'datetime_update', 'datetime_end'])
    return 'Alert updated successfully.'
