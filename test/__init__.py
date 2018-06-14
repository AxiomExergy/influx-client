"""
# Tests for InfluxDB client library

"""
# System imports
import os
import math
import time
import datetime

# 3rd party imports
import pytool
from nose.tools import eq_, ok_
from nose.plugins.attrib import attr

import mock

# Project imports
import influx
import fixtures


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


def test_make_many_lines():
    _make_many_lines = influx.InfluxDB._make_many_lines

    measurement = 'test_many'
    fields = ['alpha', 'beta', 'ts']
    values = [
            [1, 2, 1000],
            [2, 4, 2000],
            [3, 6, 3000],
            [4, 8, 4000],
            ]
    tags = {'tag_many': 'all'}

    lines = _make_many_lines(measurement, fields, values, tags)

    expected = (
            'test_many,tag_many=all alpha=1,beta=2,ts=1000\n'
            'test_many,tag_many=all alpha=2,beta=4,ts=2000\n'
            'test_many,tag_many=all alpha=3,beta=6,ts=3000\n'
            'test_many,tag_many=all alpha=4,beta=8,ts=4000\n'
            )

    eq_(lines, expected)


def test_make_many_lines_with_time_field():
    _make_many_lines = influx.InfluxDB._make_many_lines

    measurement = 'test_many'
    fields = ['alpha', 'beta', 'ts']
    values = [
            [1, 2, 1000],
            [2, 4, 2000],
            [3, 6, 3000],
            [4, 8, 4000],
            ]
    tags = {'tag_many': 'all'}

    lines = _make_many_lines(measurement, fields, values, tags,
                             time_field='ts')

    expected = (
            'test_many,tag_many=all alpha=1,beta=2 1000\n'
            'test_many,tag_many=all alpha=2,beta=4 2000\n'
            'test_many,tag_many=all alpha=3,beta=6 3000\n'
            'test_many,tag_many=all alpha=4,beta=8 4000\n'
            )

    eq_(lines, expected)


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
def test_write_many():
    client = influx.client(_get_url())

    db = 'test_write_many'
    measurement = _get_unique_measurement()
    fields = ['alpha', 'beta']
    values = [
            [1.1, 100],
            [1.2, 200],
            [2.1, 300],
            [3.0, 400],
            [5.0, 500],
            ]
    tags = {'tag_write_many': "unittest"}
    err = client.write_many(db, measurement, fields, values, tags)
    eq_(err, None)


@attr('services_required')
def test_write_many_with_ts():
    client = influx.client(_get_url())

    now = pytool.time.utcnow()
    now = pytool.time.toutctimestamp(now)
    now = math.floor(now) * 1.0  # Strip ms to prevent rounding differences

    db = 'test_write_many'
    measurement = _get_unique_measurement()
    fields = ['alpha', 'beta', 'ts']
    values = [
            [1.1, 100, now - 4],
            [1.2, 200, now - 3],
            [2.1, 300, now - 2],
            [3.0, 400, now - 1],
            [5.0, 500, now],
            ]
    tags = {'tag_write_many_ts': "unittest"}
    err = client.write_many(db, measurement, fields, values, tags, 'ts')
    eq_(err, None)

    resp = client.select_recent(db, measurement)

    # Precision multiplier (ms)
    exp = 1000000
    now = math.floor(now * exp)
    expected = {
            'results': [{
                'series': [{
                    'name': measurement,
                    'columns': ['time', 'alpha', 'beta', 'tag_write_many_ts'],
                    'values': [
                        [now - (4 * exp), 1.1, 100, 'unittest'],
                        [now - (3 * exp), 1.2, 200, 'unittest'],
                        [now - (2 * exp), 2.1, 300, 'unittest'],
                        [now - (1 * exp), 3, 400, 'unittest'],
                        [now, 5, 500, 'unittest']]}],
                'statement_id': 0}]}

    # resp = resp['results'][0]['series'][0]['values']
    # expected = expected['results'][0]['series'][0]['values']
    eq_(resp, expected)


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
def test_select_recent():
    client = influx.client(_get_url())

    # Replace microseconds race conditions at the nanosecond level
    test_time = pytool.time.utcnow().replace(microsecond=0)
    expected_time = pytool.time.toutctimestamp(test_time) * 1e6
    measurement = _get_unique_measurement()
    tags = {'my_tag': 'hello'}

    resp = client.write('test_select_all', measurement, {'value': 1}, tags,
                        time=test_time)

    # Sleep for 10ms to guarantee write persistence
    time.sleep(0.01)

    # Make our query
    # resp = client.select_recent('test_select_all', measurement,
    #                               where='"my_tag" = \'hello\'')
    resp = client.select_recent('test_select_all', measurement,
                                tags=tags)

    eq_(resp, {'results': [{'statement_id': 0, 'series': [{'name':
        measurement, 'columns': ['time', 'my_tag', 'value'], 'values':
        [[expected_time, 'hello', 1]]}]}]})


@attr('services_required')
def test_select_where():
    client = influx.client(_get_url())

    # Replace microseconds race conditions at the nanosecond level
    test_time = pytool.time.utcnow().replace(microsecond=0)
    expected_time = pytool.time.toutctimestamp(test_time) * 1e6
    measurement = _get_unique_measurement()
    db = 'test_select_where'
    tags = {'my_tag': 'workplz'}

    resp = client.write(db, measurement, {'value': 1}, tags, time=test_time)

    # Sleep for 10ms to guarantee write persistence
    time.sleep(0.01)

    # Make our query
    resp = client.select_where(db, measurement,
                               tags=tags, where='time > now() - 1s')

    eq_(resp, {'results': [{'statement_id': 0, 'series': [{'name':
        measurement, 'columns': ['time', 'my_tag', 'value'], 'values':
        [[expected_time, 'workplz', 1]]}]}]})


@attr('services_required')
def test_select_where_in_the_past():
    client = influx.client(_get_url())

    # Replace microseconds race conditions at the nanosecond level
    test_time = pytool.time.utcnow().replace(microsecond=0)
    test_time -= datetime.timedelta(hours=1)
    expected_time = pytool.time.toutctimestamp(test_time) * 1e6
    measurement = _get_unique_measurement()
    db = 'test_select_where'
    tags = {'my_tag': 'huzzah'}

    # Write one data point an hour ago
    resp = client.write(db, measurement, {'value': 1}, tags,
                        time=test_time)

    # Sleep for 10ms to guarantee write persistence
    time.sleep(0.01)

    # Make our query
    where = 'time > now() - 61m AND time < now() - 59m'
    resp = client.select_where(db, measurement, tags=tags, where=where)

    # We should find our hour old data point
    expected = {'results': [{'statement_id': 0, 'series': [{
        'name': measurement, 'columns': ['time', 'my_tag', 'value'], 'values':
        [[expected_time, 'huzzah', 1]]}]}]}

    eq_(resp, expected)

    # Query for 1h10m ago
    where = 'time > now() - 71m AND time < now() - 69m'
    resp = client.select_where(db, measurement, tags=tags, where=where)

    # We shouldn't find anything
    eq_(resp, {'results': [{'statement_id': 0}]})

    # Query an hour ago again, but with timestamps
    earlier = test_time - datetime.timedelta(minutes=1)
    later = test_time + datetime.timedelta(minutes=1)
    earlier = earlier.replace(tzinfo=None).isoformat('T') + 'Z'
    later = later.replace(tzinfo=None).isoformat('T') + 'Z'

    where = "time > '{}' AND time < '{}'".format(earlier, later)

    resp = client.select_where(db, measurement, tags=tags, where=where)

    # We should find our data point again
    eq_(resp, expected)


@attr('services_required')
def test_select_where_limits_and_order():
    client = influx.client(_get_url())

    # Replace microseconds race conditions at the nanosecond level
    test_time = pytool.time.utcnow().replace(microsecond=0)
    expected_time = pytool.time.toutctimestamp(test_time) * 1e6
    measurement = _get_unique_measurement()
    db = 'test_select_where'
    tags = {'my_tag': 'workplz'}

    resp = client.write(db, measurement, {'value': 1}, tags,
                        time=test_time - datetime.timedelta(seconds=2))
    eq_(resp, None)
    resp = client.write(db, measurement, {'value': 2}, tags,
                        time=test_time - datetime.timedelta(seconds=1))
    eq_(resp, None)
    resp = client.write(db, measurement, {'value': 3}, tags,
                        time=test_time)
    eq_(resp, None)

    # Sleep for 10ms to guarantee write persistence
    time.sleep(0.01)

    # Make our query
    fields = 'my_tag, last(value)'
    resp = client.select_where(db, measurement, fields=fields, tags=tags,
                               where='time > now() - 10s', limit=1)
    columns, values = client.unpack(resp)
    eq_(values, [[expected_time, 'workplz', 3]])

    # Test reverse ordering
    resp = client.select_where(db, measurement, tags=tags, desc=True, limit=3)
    columns, values = client.unpack(resp)
    eq_(len(values), 3)
    eq_(values[0], [expected_time, 'workplz', 3])

    # Test starting timestamp with reverse ordering
    fields = 'my_tag, first(value)'
    resp = client.select_where(db, measurement, tags=tags, desc=True, limit=1)
    columns, values = client.unpack(resp)
    eq_(values, [[expected_time, 'workplz', 3]])

    # Subtract two seconds from the expected time to match first result
    expected_time -= 2000000

    resp = client.select_where(db, measurement, tags=tags, desc=False, limit=3)
    columns, values = client.unpack(resp)
    eq_(len(values), 3)
    eq_(values[0], [expected_time, 'workplz', 1])

    # Test starting timestamp
    fields = 'my_tag, first(value)'
    resp = client.select_where(db, measurement, tags=tags, desc=False, limit=1)
    columns, values = client.unpack(resp)
    eq_(values, [[expected_time, 'workplz', 1]])

    # Test regular ordering
    resp = client.select_where(db, measurement, tags=tags, desc=False, limit=1)
    columns, values = client.unpack(resp)
    eq_(values, [[expected_time, 'workplz', 1]])

    # Generic ordering
    resp = client.select_where(db, measurement, tags=tags,
                               where='time > now() - 10s', limit=1)
    columns, values = client.unpack(resp)
    eq_(values, [[expected_time, 'workplz', 1]])


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


def test_importing_result_line_protocol():
    _make_many_lines = influx.InfluxDB._make_many_lines
    client = influx.client(_get_url())
    result = fixtures.json.result
    columns, values = client.unpack(result)

    # Sanity check
    eq_(columns[0], 'time')
    eq_(values[0][0], 1487275118000000)

    columns = columns[:3]
    values = [row[:3] for row in values[:3]]

    measurement = 'lines'
    fields = columns
    tags = {'mytag': 'mine'}

    lines = _make_many_lines(measurement, fields, values, tags)

    expected = (
            'lines,mytag=mine blding.cmpA=34.45272,blding.cmpB=48.43736,'
            'time=1487275118000000\n'
            'lines,mytag=mine blding.cmpA=34.223846,blding.cmpB=48.417927,'
            'time=1487275133000000\n'
            'lines,mytag=mine blding.cmpA=23.646818,blding.cmpB=48.378204,'
            'time=1487275148000000\n'
            )

    eq_(lines, expected)


@attr('services_required')
def test_importing_result_write_and_retrieve():
    client = influx.client(_get_url())
    result = fixtures.json.result
    columns, values = client.unpack(result)

    columns = columns[:3]
    values = [row[:3] for row in values[:3]]

    db = 'test_write_result'
    measurement = _get_unique_measurement()
    fields = columns

    tags = {'imported': 'yes'}
    err = client.write_many(db, measurement, fields, values, tags, 'time')

    eq_(err, None)

    resp = client.select_recent(db, measurement, relative_time='100000d')
    fields, vals = client.unpack(resp)

    eq_(fields, columns + ['imported'])
    eq_(vals, [v + ['yes'] for v in values])


# @mock.patch('influx.InfluxDB.create_database')
# @mock.patch('influx.InfluxDB._make_request')
# def test_safe_request(_make_request, create_database):
def test_safe_request():
    # _make_request.return_value.status_code = 200
    # _make_request.return_value.json = 'error'

    # create_database.return_value = {'results': [{'statement_id': 0}]}

    client = influx.client(_get_url())

    missing_db = mock.MagicMock()
    created_db = mock.MagicMock()
    select = mock.MagicMock()

    missing_db.status_code = 404
    missing_db.json.return_value = {
            'results': [
                {
                    'statement_id': 0,
                    'error': 'database not found'
                }
            ]
        }
    created_db.status_code = 200
    created_db.json.return_value = {'results': [{'statement_id': 0}]}

    select.status_code = 200
    select.json.return_value = '200 OK'

    with mock.patch.object(client.session, 'request') as request:
        request.side_effect = [
            missing_db, created_db, select
        ]

        resp = client._safe_request(
            influx.IQL_SELECT, database='database',
            measurement='measurement', fields='fields',
            where='where')

        eq_(len(request.call_args_list), 3)
        ok_(resp.json() is '200 OK')


@attr('services_required')
def test_write_float_returns_float():
    client = influx.client(_get_url())

    db = 'test_write_float'
    measurement = _get_unique_measurement()

    fields = {'float_value': 0.5}
    tags = {'tested': 1}
    err = client.write(db, measurement, fields, tags)

    eq_(err, None)

    resp = client.select_recent(db, measurement)
    fields, vals = client.unpack(resp)

    eq_(fields, ['time', 'float_value', 'tested'])
    eq_(vals[0][1:], [0.5, '1'])
    eq_(type(vals[0][1:][0]), float)
