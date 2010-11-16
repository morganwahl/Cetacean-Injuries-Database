from math import modf

from cetacean_incidents.apps.incidents.models import Observation
from cetacean_incidents.apps.entanglements.models import GearOwner
from cetacean_incidents.apps.uncertain_datetimes import UncertainDateTime

def dt_to_udt(dt):
    udt = UncertainDateTime(
        dt.year,
        dt.month,
        dt.day,
        dt.hour,
        dt.minute,
    )
    if not dt.second is None:
        (usec, sec) = modf(dt.second)
        udt.second = int(sec)
        if usec:
            udt.microsecond = int(round(usec * (10 ** 6)))
    print "%s <- %s" % (udt.__unicode__(), dt)
    return udt


for o in Observation.objects.all():
    o.datetime_observed = dt_to_udt(o.observation_datetime)
    o.datetime_reported = dt_to_udt(o.report_datetime)
    o.save()

for go in GearOwner.objects.all():
    go.datetime_set = dt_to_udt(go.date_gear_set)
    go.datetime_missing = dt_to_udt(go.date_gear_missing)
    go.save()
    
