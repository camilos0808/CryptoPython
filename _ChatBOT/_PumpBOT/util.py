import datetime as dt

def minute_boolean(date:dt):
    minutes = date.minute
    if minutes in [0,29,30,59]:
        return True
    else:
        return False