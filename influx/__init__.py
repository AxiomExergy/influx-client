"""
# InfluxDB client

This module contains an InfluxDB client.

"""
# System imports
from urllib import parse

# 3rd party imports
import pytool
import requests
import simplejson
from requests.exceptions import RequestException, HTTPError

# Project imports
from . import line_protocol


# Mappings for InfluxQL commands to HTTP requests
IQL_WRITE = 'POST', 'write?db={database}', '', '{lines}'
IQL_CREATE_DATABASE = ('POST', 'query', {'q':
                                         "CREATE DATABASE \"{database}\""}, '')
IQL_DROP_DATABASE = ('POST', 'query', {'q':
                                       "DROP DATABASE \"{database}\""}, '')
IQL_SELECT = ('GET', 'query', {'db': "{database}", 'epoch': 'u', 'q': "SELECT "
              "{fields} FROM {measurement} WHERE {where}"}, '')


@pytool.lang.hashed_singleton
class InfluxDB:
    """
    InfluxDB client class

    Provides lowish level access to write and read from InfluxDB with automatic
    connection pooling.

    TODO: Document this

    """
    __slots__ = [
            'url',
            'session',
            '__weakref__',
            ]

    def __init__(self, url):
        self.url = url
        self.session = requests.Session()

    def create_database(self, database):
        """
        Returns the the response JSON from making the create database request.

        If the creation is successful (or the database already exists, the
        response JSON will always be `{'results': [{'statement_id': 0}]}`.

        Issues the CREATE DATABASE InfluxQL query for *database*.

        If there is an error with the request, an exception will be raised from
        the *requests* library.

        :param str database: Database name to create
        :return dict: Response JSON

        """
        resp = self._make_request(IQL_CREATE_DATABASE, database=database)
        InfluxDB._check_and_raise(resp)
        return resp.json()

    def drop_database(self, database):
        """
        Returns the the response JSON from making the drop database request.

        Issues the DROP DATABASE InfluxQL query for *database*.

        If there is an error with the request, an exception will be raised from
        the *requests* library.

        :param str database: Database name to drop
        :return dict: Response JSON

        """
        resp = self._make_request(IQL_DROP_DATABASE, database=database)
        InfluxDB._check_and_raise(resp)
        return resp.json()

    def write(self, database, measurement, fields, tags={}, time=None):
        """
        Return response JSON from writing data points as a dict.

        If there is an error with the request, an exception will be raised from
        the *requests* library.

        :param str database: Database name to write to
        :param str measurement: Measurement name to write to
        :param dict fields: Dictionary of fields to write
        :param dict tags: Dictionary of tags to associate with these points
        :param datetime time: UTC timestamp to use (optional, defaults to using
                              the InfluxDB server time)
        :return dict: Response JSON

        """
        lines = InfluxDB._make_lines(measurement, fields, tags, time)
        resp = self._safe_request(IQL_WRITE, database=database, lines=lines)
        InfluxDB._check_and_raise(resp)
        if resp.status_code != 204:
            return resp.json()

    def select_recent(self, database, measurement, fields='*', tags=None,
                      relative_time="15m"):
        """
        Return response JSON from querying InfluxDB for all fields in the given
        database and measurement.

        If there is an error with the request, an exception will be raised from
        the *requests* library.

        :param str database: Database name to query
        :param str measurement: Measurement name to query
        :param str fields: Fields to select in query (optional, default `'*'`)
        :param str tags: Tags to restrict the select by (optional)
        :param str relative_time: Relative time to now() to query for
                                  (optional, default `'15m'`)

        .. note::

            The *relative_time* argument uses the `InfluxDB relative time
            <https://docs.influxdata.com
            /influxdb/v1.5/query_language/data_exploration/#relative-time>`_
            format.

        """
        relative_time = "time > now() - {}".format(relative_time)

        # Format the tags and combine them with the time slice for WHERE clause
        if tags:
            where = InfluxDB._format_tags(tags)
            where += " AND {}".format(relative_time)
        else:
            where = relative_time

        resp = self._safe_request(IQL_SELECT, database=database,
                                  measurement=measurement, fields=fields,
                                  where=where)
        InfluxDB._check_and_raise(resp)
        return resp.json()

    def _safe_request(self, *args, **kwargs):
        """
        Return a response object.

        This will attempt to retry the request if the database does not exist,
        after first creating the database.

        :param *args: Positional arguments that are passed to
                      :meth:`InfluxDB._make_request`
        :param *kwargs: Keyword arguments that are passed to
                      :meth:`InfluxDB._make_request`
        :return request.Response: Response object

        """
        # Initial request, this should hopefully be fine
        resp = self._make_request(*args, **kwargs)

        # If we don't have a database name to work with, we can't do anything
        database = kwargs.get('database', None)
        if not database:
            return resp

        # Database missing errors can be 200s or 404s
        if resp.status_code != 200 and resp.status_code != 404:
            return resp

        # The response should contain JSON data
        data = resp.json()

        if 'error' in data:
            error = data['error']
        elif 'results' in data:
            statements = data.get('results', [])

            # Check if there's an error in the first statement - if there's
            # multiple statements, we'll have to handle this differently
            if len(statements) != 1 or 'error' not in statements[0]:
                return resp

            # Check if the error is a database missing error
            error = statements[0]['error']
            if not error.startswith('database not found'):
                return resp
        else:
            # JSON returned is a weird ass format
            return resp

        # Create the database
        try:
            db_resp = self.create_database(database)
        except RequestException as err:
            # XXX: We probably should include this exception to be raised or
            # report it
            return resp

        # If we didn't succeed, return the original error
        # We expect the JSON to match {'results': [{'statement_id': 0}]}
        if db_resp != {'results': [{'statement_id': 0}]}:
            # XXX: Log/report the error trying to create the database?
            return resp

        # Retry the request
        return self._make_request(*args, **kwargs)

    def _make_request(self, influxql, **fields):
        """
        Return a response object from making a request to the InfluxDB API.

        :param tuple influxql: Tuple describing an InfluxQL API request
        :param dict **fields: Fields to include in the formatted and prepared
                              InfluxQL API request as keyword arguments
        :return requests.Response: A response object

        """
        # Get the query template
        method, path, params, data = influxql

        # Format the path with any path fields
        path = path.format(**fields)

        # Format the params
        params = InfluxDB._format_any(params, **fields)

        # Format the data body
        data = InfluxDB._format_any(data, **fields)

        # Create the new URL
        url = parse.urljoin(self.url, path)

        # Make the request using the session socket pool
        # XXX (Jake): May want to make the timeout here configurable...
        return self.session.request(method, url, params=params, data=data,
                                    timeout=2)

    @staticmethod
    def _check_and_raise(response):
        """
        Raises a smart exception if *response* is an error.

        :param request.Response response: A response object

        """
        assert isinstance(response, requests.Response), \
            "Bad response type {}".format(response)

        # Only pay attention to codes over 400
        if response.status_code < 400:
            return

        if isinstance(response.reason, bytes):
            # We attempt to decode utf-8 first because some servers
            # choose to localize their reason strings. If the string
            # isn't utf-8, we fall back to iso-8859-1 for all other
            # encodings. (See PR #3538)
            try:
                reason = response.reason.decode('utf-8')
            except UnicodeDecodeError:
                reason = response.reason.decode('iso-8859-1')
        else:
            reason = response.reason

        # Try to decode the JSON body from Influx
        try:
            msg = response.json()
            # Try to get the error from all possible places
            msg = msg.get('error', (msg.get('results', []) +
                                    [{}]).pop().get('error', None))
        except simplejson.JSONDecodeError:
            msg = None

        if msg:
            reason = msg

        # Format a sane error message
        http_error_msg = "{} {} for {}".format(response.status_code, reason,
                                               response.url)

        raise HTTPError(http_error_msg, response=response)

    @staticmethod
    def _make_lines(measurement, fields, tags={}, time=None):
        """
        Return InfluxDB line protocol lines as a string.

        :param str measurement: Measurement name
        :param dict fields: Fields dictionary
        :param dict tags: Tags to include (optional)
        :param datetime time: Time of the data points (optional, default now)

        """
        if time is None:
            time = pytool.time.utcnow()

        lines = line_protocol.make_lines({
                'tags': tags,
                'points': [{
                    'measurement': measurement,
                    'fields': fields,
                    'time': time,
                    }]
                })
        return lines

    @staticmethod
    def _format_any(obj, **fields):
        """
        Return `obj` having formatted its values using `fields` as a format
        dict.

        :param object obj: A tuple, list, dict, or str
        :return str: Formatted string

        """
        if not obj:
            return obj

        # Handle a list of lists or list of tuples
        if (isinstance(obj, (tuple, list)) and
                isinstance(obj[0], (tuple, list))):
            return {i[0]: i[1].format(**fields) for i in obj}
        # Handle a list of dicts
        elif isinstance(obj, (tuple, list)) and isinstance(obj[0], dict):
            return [InfluxDB._format_any(i, fields) for i in obj]
        # Handle a straight up dict
        elif isinstance(obj, (dict)):
            return {k: v.format(**fields) for k, v in obj.items()}
        # Handle a string
        else:
            return obj.format(**fields)

    @staticmethod
    def _format_tags(tags):
        """
        Return *tags* formatted as a WHERE clause in InfluxQL using AND.

        :param dict tags: Dictionary of tags to format
        :return str: WHERE clause string

        """
        where = []
        for tag, value in tags.items():
            tag = '"{}"'.format(tag)
            if isinstance(value, (list, tuple)):
                value = ["'{}'".format(i) for i in value]
                value = ','.join(value)
                value = "[{}]".format(value)
            else:
                value = "'{}'".format(value)
            where.append('{}={}'.format(tag, value))

        where = ' AND '.join(where)
        return where


def client(url):
    """
    Return an InfluxDB client.

    :param str url: InfluxDB API url

    """
    return InfluxDB(url)
