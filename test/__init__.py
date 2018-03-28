"""
# Tests for InfluxDB client library

"""
# System imports
import os
import time

# 3rd party imports
import pytool
from nose.tools import eq_
from nose.plugins.attrib import attr

# Project imports
import influx


def _get_url():
    """
    Return an InfluxDB client instance.

    """
    url = os.environ.get('INFLUX_URL', 'http://127.0.0.1:8086')
    return url


@attr('services_required')
def test_create_database():
    client = influx.client(_get_url())

    resp = client.create_database('test')

    eq_(resp, {'results': [{'statement_id': 0}]})


def test_make_lines():
    _make_lines = influx.InfluxDB._make_lines
    lines = _make_lines('test_measurement', {'field1': 1.0, 'field2': 2},
                        {'tag1': 'test_tag'}, 1521241703.097608192)

    eq_(lines, 'test_measurement,tag1=test_tag field1=1.0,field2=2 '
        '1521241703097608192\n')


def _get_unique_measurement():
    """ Helper to consistently return a unique measurement name as needed. """
    return 'test_measurement_{}'.format(int(time.monotonic() * 1e3))


@attr('services_required')
def test_write():
    client = influx.client(_get_url())

    measurement = _get_unique_measurement()
    err = client.write('test', measurement, {'field1': 1.0, 'field2':
                       2}, {'tag1': 'test_tag'}, 1521241703.097608192)

    # If there is no error, there will be no response JSON, and we're good
    eq_(err, None)


@attr('services_required')
def test_write_without_time():
    client = influx.client(_get_url())

    measurement = _get_unique_measurement()
    err = client.write('test', measurement, {'field1': 1.0, 'field2':
                       2}, {'tag1': 'test_tag'})

    # If there is no error, there will be no response JSON, and we're good
    eq_(err, None)


@attr('services_required')
def test_select_all():
    client = influx.client(_get_url())

    # Replace microseconds race conditions at the nanosecond level
    test_time = pytool.time.utcnow().replace(microsecond=0)
    expected_time = pytool.time.toutctimestamp(test_time) * 1e6
    measurement = _get_unique_measurement()

    resp = client.write('test_select_all', measurement, {'value': 1},
                        time=test_time)
    # Sleep for 50ms to guarantee write persistence
    time.sleep(0.05)
    resp = client.select_recent('test_select_all', measurement)

    eq_(resp, {'results': [{'statement_id': 0, 'series': [{'name':
        measurement, 'columns': ['time', 'value'], 'values':
        [[expected_time, 1]]}]}]})


@attr('services_required')
def test_select_where():
    client = influx.client(_get_url())

    # Replace microseconds race conditions at the nanosecond level
    test_time = pytool.time.utcnow().replace(microsecond=0)
    expected_time = pytool.time.toutctimestamp(test_time) * 1e6
    measurement = _get_unique_measurement()
    tags = {'my_tag': 'hello'}

    resp = client.write('test_select_all', measurement, {'value': 1}, tags,
                        time=test_time)

    # Sleep for 50ms to guarantee write persistence
    time.sleep(0.05)

    # Make our query
    # resp = client.select_recent('test_select_all', measurement,
    #                               where='"my_tag" = \'hello\'')
    resp = client.select_recent('test_select_all', measurement,
                                tags=tags)

    eq_(resp, {'results': [{'statement_id': 0, 'series': [{'name':
        measurement, 'columns': ['time', 'my_tag', 'value'], 'values':
        [[expected_time, 'hello', 1]]}]}]})


def test_format_tags_simple():
    _format_tags = influx.InfluxDB._format_tags
    where = _format_tags({'tag1': 'value1'})

    eq_(where, '"tag1"=\'value1\'')


def test_format_tags_list():
    _format_tags = influx.InfluxDB._format_tags
    where = _format_tags({'tag1': ['value1', 'value2']})

    eq_(where, '"tag1"=[\'value1\',\'value2\']')


def test_format_tags_complex():
    _format_tags = influx.InfluxDB._format_tags
    where = _format_tags({'tag1': ['value1', 'value2'], 'tag2': 'value3'})

    eq_(where, '"tag1"=[\'value1\',\'value2\'] AND "tag2"=\'value3\'')


def test_format_tags_empty():
    _format_tags = influx.InfluxDB._format_tags
    where = _format_tags({})

    eq_(where, '')
