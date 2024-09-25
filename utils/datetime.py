from datetime import datetime
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

def convert_timedelta_to_float(td):
    year = int(td.days / 365)
    month = int((td.days - (year * 365)) / 31) / 100
    return year + month


def convert_float_to_timedelta(data):
    year, month = str(float(data)).split('.')
    return timedelta(seconds=(int(year) * 365 * 24 * 60 * 60) + (int(month) * 30 * 24 * 60 * 60))


def is_valid_date(year, month, day):
    is_valid = True
    try:
        d = datetime.date(int(year), int(month), int(day))
    except ValueError as e:
        is_valid = False
    return is_valid


def convert_to_local(utc_time):
    from dateutil import tz
    from_zone = tz.gettz('UTC')
    to_zone = tz.gettz(settings.TIME_ZONE)

    try:
        utc = utc_time.replace(tzinfo=from_zone)
    except:
        return None
    return utc.astimezone(to_zone)


def duration_format(duration, is_second_included=False):
    if isinstance(duration, timedelta):
        s = duration.total_seconds()
    elif isinstance(duration, float) or isinstance(duration, int):
        s = duration
    else:
        s = 0

    if s < 0:
        s = 0

    h, r = divmod(s, 3600)
    m, s = divmod(r, 60)

    if h > 0:
        return '%d:%02d' % (h, m) if not is_second_included else '%d:%02d:%02d' % (h, m, s)
    else:
        return '00:%02d' % m if not is_second_included else '00:%02d:%02d' % (m, s)


def get_date(str_date):
    try:
        return datetime.strptime(str_date, '%Y-%m-%d').date()
    except:
        return None


def get_local_datetime(str_date):
    local_timezone = timezone.get_current_timezone()
    try:
        _datetime_obj = datetime.strptime(str_date, '%Y-%m-%d')
        _datetime_obj = local_timezone.localize(_datetime_obj)
        return _datetime_obj
    except:
        return None


def get_date_format_certificate_thai(date):
    list_month = ['มกราคม', 'กุมภาพันธ์', 'มีนาคม', 'เมษายน', 'พฤษภาคม', 'มิถุนายน', 'กรกฎาคม',
                  'สิงหาคม', 'กันยายน', 'ตุลาคม', 'พฤศจิกายน', 'ธันวาคม']
    month_thai = list_month[date.month - 1]
    year_thai = date.year + 543
    return '%s %s %s' % (str(date.day), month_thai, str(year_thai))


def get_date_format_certificate_thai_number(date):
    list_month = [
        'มกราคม',
        'กุมภาพันธ์',
        'มีนาคม',
        'เมษายน',
        'พฤษภาคม',
        'มิถุนายน',
        'กรกฎาคม',
        'สิงหาคม',
        'กันยายน',
        'ตุลาคม',
        'พฤศจิกายน',
        'ธันวาคม',
    ]
    month_thai = list_month[date.month - 1]
    year_thai = date.year + 543
    return 'วันที่ %s เดือน %s พ.ศ. %s' % (
        convert_arabic_to_thai(str(date.day)),
        month_thai,
        convert_arabic_to_thai(str(year_thai))
    )


def get_date_format_certificate_english(date):
    return date.strftime('%B %d, %Y')


def format_seconds_to_hhmmss(seconds):
    hours = seconds // (60 * 60)
    seconds %= (60 * 60)
    minutes = seconds // 60
    seconds %= 60
    return "%02i:%02i:%02i" % (hours, minutes, seconds)

def convert_arabic_to_thai(arabic_num):
    thai_number_list = '๐๑๒๓๔๕๖๗๘๙'
    thai_number = ''
    for num in arabic_num:
        thai_number += thai_number_list[int(num)]
    return thai_number
