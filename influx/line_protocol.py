# -*- coding: utf-8 -*-
"""
# InfluxDB line protocol module

"""
# System imports
from datetime import datetime
from numbers import Integral

# 3rd party imports
import pytool


def _convert_timestamp(timestamp, precision=None):
    if precision is None or precision == 'n':
        factor = 1e9
    elif precision == 'u':
        factor = 1e6
    elif precision == 'ms':
        factor = 1e3
    elif precision == 's':
        factor = 1
    elif precision == 'm':
        factor = 1. / 60
    elif precision == 'h':
        factor = 1. / 3600

    if isinstance(timestamp, Integral):
        # Sanity checking that the precision isn't set wrong... this may bite
        # people who are using far future timestamps, which InfluxDB supports
        if precision == 'u':
            assert timestamp < 1e18
        elif precision == 'ms':
            assert timestamp < 1e15
        elif precision == 's':
            assert timestamp < 1e12

        return timestamp  # assume precision is correct if timestamp is int

    if isinstance(timestamp, float):
        return timestamp * factor

    if isinstance(timestamp, datetime):
        if not timestamp.tzinfo:
            timestamp = pytool.time.as_utc(timestamp)

        stamp = timestamp - pytool.time.fromutctimestamp(0)
        stamp = stamp.total_seconds()
        stamp *= factor
        return stamp

    raise ValueError(timestamp)


def _escape_tag(tag):
    tag = _get_unicode(tag, force=True)
    return tag.replace(
        "\\", "\\\\"
    ).replace(
        " ", "\\ "
    ).replace(
        ",", "\\,"
    ).replace(
        "=", "\\="
    )


def _escape_tag_value(value):
    ret = _escape_tag(value)
    if ret.endswith('\\'):
        ret += ' '
    return ret


def quote_ident(value):
    """Indent the quotes."""
    return "\"{}\"".format(value
                           .replace("\\", "\\\\")
                           .replace("\"", "\\\"")
                           .replace("\n", "\\n"))


def quote_literal(value):
    """Quote provided literal."""
    return "'{}'".format(value
                         .replace("\\", "\\\\")
                         .replace("'", "\\'"))


def _is_float(value):
    try:
        float(value)
    except (TypeError, ValueError):
        return False

    return True


def _escape_value(value):
    value = _get_unicode(value)

    if isinstance(value, str) and value != '':
        return quote_ident(value)
    elif isinstance(value, int) and not isinstance(value, bool):
        # Appending 'i' forces an integer, which causes a conflict when values
        # round to zero because it thinks its an int... we don't want that, so
        # we drop the 'i' and everything counts as a float, which is the most
        # compatible behavior. Uncommenting this will restore the original
        # behavior, but break things elsewhere.
        # return str(value) + 'i'
        return str(value)
    elif _is_float(value):
        return repr(value)

    return str(value)


def _get_unicode(data, force=False):
    """Try to return a text aka unicode object from the given data."""
    if isinstance(data, bytes):
        return data.decode('utf-8')
    elif data is None:
        return ''
    elif force:
        return str(data)
    else:
        return data


def make_lines(data, precision=None):
    """Extract points from given dict.
    Extracts the points from the given dict and returns a Unicode string
    matching the line protocol introduced in InfluxDB 0.9.0.
    """
    lines = []
    static_tags = data.get('tags')
    for point in data['points']:
        elements = []

        # add measurement name
        measurement = _escape_tag(_get_unicode(
            point.get('measurement', data.get('measurement'))))
        key_values = [measurement]

        # add tags
        if static_tags:
            tags = dict(static_tags)  # make a copy, since we'll modify
            tags.update(point.get('tags') or {})
        else:
            tags = point.get('tags') or {}

        # tags should be sorted client-side to take load off server
        for tag_key, tag_value in sorted(tags.items()):
            key = _escape_tag(tag_key)
            value = _escape_tag_value(tag_value)

            if key != '' and value != '':
                key_values.append(key + "=" + value)

        elements.append(','.join(key_values))

        # add fields
        field_values = []
        for field_key, field_value in sorted(point['fields'].items()):
            key = _escape_tag(field_key)
            value = _escape_value(field_value)

            if key != '' and value != '':
                field_values.append(key + "=" + value)

        elements.append(','.join(field_values))

        # add timestamp
        if 'time' in point:
            timestamp = _get_unicode(str(int(
                _convert_timestamp(point['time'], precision))))
            elements.append(timestamp)

        line = ' '.join(elements)
        lines.append(line)

    return '\n'.join(lines) + '\n'
