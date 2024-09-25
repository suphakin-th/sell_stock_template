import random

TIME_RANGE_SHORT = range(60 * 1, 60 * 5, 60 * 1)  # 5 m.

TIME_RANGE_MINUTE = range(60 * 30, 60 * 60, 60 * 5)  # 5 m.

TIME_RANGE = range(60 * 60, 60 * 60 * 6, 60 * 5)  # 5 m.

TIME_RANGE_DAY = range(60 * 60 * 24, 60 * 60 * 24 * 5, 60 * 30)  # 1 hr.

TIME_RANGE_WEEK = range(60 * 60 * 24 * 7, 60 * 60 * 24 * 7 * 4, 60 * 60 * 4)  # 4hr.


def get_time_out_short():  # 1 - 5 minute.
    return random.choice(TIME_RANGE_SHORT)


def get_time_out_minute():  # 30 - 60 minute.
    return random.choice(TIME_RANGE_MINUTE)


def get_time_out():  # 1 - 6 hr.
    return random.choice(TIME_RANGE)


def get_time_out_day():  # 1 - 5 day.
    return random.choice(TIME_RANGE_DAY)


def get_time_out_week():  # 1 - 4 week.
    return random.choice(TIME_RANGE_WEEK)
