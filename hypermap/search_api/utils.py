import re

import datetime
import isodate
import math

from dateutil.parser import parse
from shapely.geometry import box


def parse_datetime(date_str):
    """
    Parses a date string to date object.
    """
    if date_str == '*':
        return None  # open ended.
    default = datetime.datetime.now().replace(
        hour=0, minute=0, second=0, microsecond=0,
        day=1, month=1
    )
    return parse(date_str, default=default)


def parse_solr_time_range_as_pair(time_filter):
    """
    :param time_filter: [2013-03-01 TO 2013-05-01T00:00:00]
    :return: (2013-03-01, 2013-05-01T00:00:00)
    """
    pattern = "\\[(.*) TO (.*)\\]"
    matcher = re.search(pattern, time_filter)
    if matcher:
        return matcher.group(1), matcher.group(2)
    else:
        raise Exception("Regex {0} couldn't parse {1}".format(pattern, time_filter))

def parse_datetime_range(time_filter):
    """
    Parse the url param to python objects.
    From what time range to divide by a.time.gap into intervals.
    Defaults to q.time and otherwise 90 days.
    Validate in API: re.search("\\[(.*) TO (.*)\\]", value)
    :param time_filter: [2013-03-01 TO 2013-05-01T00:00:00]
    :return: datetime.datetime(2013, 3, 1, 0, 0), datetime.datetime(2013, 5, 1, 0, 0)
    """

    if not time_filter:
        time_filter = "[* TO *]"

    start, end = parse_solr_time_range_as_pair(time_filter)
    start, end = parse_datetime(start), parse_datetime(end)
    if None not in [start, end] and start > end:
        raise Exception("Start must come before End: {0}".format(time_filter))

    return start, end


def parse_ISO8601(time_gap):
    """
    P1D to (1, ("DAYS", isodate.Duration(days=1)).
    P1Y to (1, ("YEARS", isodate.Duration(years=1)).
    :param time_gap: ISO8601 string.
    :return: tuple with quantity and unit of time.
    """
    matcher = None

    if time_gap.count("T"):
        units = {
            "H": ("HOURS", isodate.Duration(hours=1)),
            "M": ("MINUTES", isodate.Duration(minutes=1)),
            "S": ("SECONDS", isodate.Duration(seconds=1))
        }
        matcher = re.search("PT(\d+)([HMS])", time_gap)
        if matcher:
            quantity = int(matcher.group(1))
            unit = matcher.group(2)
            return quantity, units.get(unit)
        else:
            raise Exception("Does not match the pattern: {}".format(time_gap))
    else:
        units = {
            "Y": ("YEARS", isodate.Duration(years=1)),
            "M": ("MONTHS", isodate.Duration(months=1)),
            "W": ("WEEKS", isodate.Duration(weeks=1)),
            "D": ("DAYS", isodate.Duration(days=1))
        }
        matcher = re.search("P(\d+)([YMWD])", time_gap)
        if matcher:
            quantity = int(matcher.group(1))
            unit = matcher.group(2)
        else:
            raise Exception("Does not match the pattern: {}".format(time_gap))

    return quantity, units.get(unit)


def compute_gap(start, end, time_limit):
    """
    Compute a gap that seems reasonable, considering natural time units and limit.
    # TODO: make it to be reasonable.
    # TODO: make it to be small unit of time sensitive.
    :param start: datetime
    :param end: datetime
    :param time_limit: gaps count
    :return: solr's format duration.
    """
    duration = end - start
    unit = int(math.ceil(duration.days / float(time_limit)))
    return "+{0}DAYS".format(unit)


def gap_to_sorl(time_gap):
    """
    P1D to +1DAY
    :param time_gap:
    :return: solr's format duration.
    """
    quantity, unit = parse_ISO8601(time_gap)
    if unit[0] == "WEEKS":
        return "+{0}DAYS".format(quantity * 7)
    else:
        return "+{0}{1}".format(quantity, unit[0])


def request_time_facet(field, time_filter, time_gap, time_limit=100):
    """
    time facet query builder
    :param field: map the query to this field.
    :param time_limit: Non-0 triggers time/date range faceting. This value is the maximum number of time ranges to
    return when a.time.gap is unspecified. This is a soft maximum; less will usually be returned. A suggested value is 100.
    Note that a.time.gap effectively ignores this value. See Solr docs for more details on the query/response format.
    :param time_filter: From what time range to divide by a.time.gap into intervals. Defaults to q.time and otherwise 90 days.
    :param time_gap: The consecutive time interval/gap for each time range. Ignores a.time.limit.The format is based
    on a subset of the ISO-8601 duration format
    :return: facet.range=manufacturedate_dt&f.manufacturedate_dt.facet.range.start=2006-02-11T15:26:37Z&f.manufacturedate_dt.facet.range.end=2006-02-14T15:26:37Z&f.manufacturedate_dt.facet.range.gap=+1DAY
    """
    now = datetime.datetime.utcnow()
    start, end = parse_datetime_range(time_filter)
    if not start:
        start = now - datetime.timedelta(days=90)
    if not end:
        end = now

    key_range_start = "f.{0}.facet.range.start".format(field)
    key_range_end = "f.{0}.facet.range.end".format(field)
    key_range_gap = "f.{0}.facet.range.gap".format(field)

    if time_gap:
        gap = gap_to_sorl(time_gap)
    else:
        gap = compute_gap(start, end, time_limit)

    params = {
        'facet.range': field,
        key_range_start: start.isoformat().replace("+00:00", "Z"),
        key_range_end: end.isoformat().replace("+00:00", "Z"),
        key_range_gap: gap,
    }
    # get_params = urllib.urlencode(params)
    return params


def parse_solr_geo_range_as_pair(geo_box_str):
    """
    :param geo_box_str: [-90,-180 TO 90,180]
    :return: ("-90,-180", "90,180")
    """
    pattern = "\\[(.*) TO (.*)\\]"
    matcher = re.search(pattern, geo_box_str)
    if matcher:
        return matcher.group(1), matcher.group(2)
    else:
        raise Exception("Regex {0} could not parse {1}".format(pattern, geo_box_str))


def parse_lat_lon(point_str):
    lat, lon = map(float, point_str.split(','))
    return lat, lon

def parse_geo_box(geo_box_str):
    """
    parses [-90,-180 TO 90,180] to a shapely.geometry.box
    :param geo_box_str:
    :return:
    """

    from_point_str, to_point_str = parse_solr_geo_range_as_pair(geo_box_str)
    from_point = parse_lat_lon(from_point_str)
    to_point = parse_lat_lon(to_point_str)
    rectangle = box(from_point[0], from_point[1], to_point[0], to_point[1])
    return rectangle


def request_heatmap_facet(field, hm_filter, hm_grid_level, hm_limit):
    """
    heatmap facet query builder
    :param field: map the query to this field.
    :param hm_filter: From what region to plot the heatmap. Defaults to q.geo or otherwise the world.
    :param hm_grid_level: To explicitly specify the grid level, e.g. to let a user ask for greater or courser
    resolution than the most recent request. Ignores a.hm.limit.
    :param hm_limit: Non-0 triggers heatmap/grid faceting. This number is a soft maximum on thenumber of
    cells it should have. There may be as few as 1/4th this number in return. Note that a.hm.gridLevel can effectively
    ignore this value. The response heatmap contains a counts grid that can be null or contain null rows when all its
    values would be 0. See Solr docs for more details on the response format.
    :return:
    """

    if not hm_filter:
        hm_filter = '[-90,-180 TO 90,180]'

    params = {
        'facet': 'on',
        'facet.heatmap': field,
        'facet.heatmap.geom': hm_filter
    }

    if hm_grid_level:
        # note: aHmLimit is ignored in this case
        params['facet.heatmap.gridLevel'] = hm_grid_level
    else:
        # Calculate distErr that will approximate aHmLimit many cells as an upper bound
        rectangle = parse_geo_box(hm_filter)
        degrees_side_length = rectangle.length / 2
        cell_side_length = math.sqrt(float(hm_limit))
        cell_side_length_degrees = degrees_side_length / cell_side_length * 2
        params['facet.heatmap.distErr'] = str(float(cell_side_length_degrees))
        # TODO: not sure about if returning correct param values.

    #get_params = urllib.urlencode(params)
    return params


def request_field_facet(field, limit, ex_filter=True):
    pass