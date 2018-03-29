# influx-client

InfluxDB client compatible with 1.5. This client uses the awesome
[requests](http://docs.python-requests.org/en/master/) library to provide
connection pooling for each unique InfluxDB URL given.

This InfluxDB client is created, maintained, and supported by [Axiom
Exergy](http://www.axiomexergy.com).

## Prerequisites

This client has only been tested and used against InfluxDB 1.5 and Python 3.5.
If you want to support any other environments, please submit a pull request.

## Installation

You can install this client via PyPI:

```bash
$ pip install influx-client
```

Or by cloning this repository:

```bash
$ git clone https://github.com/AxiomExergy/influx-client.git
$ cd influx-client
$ pip install .  # For a regular install
$ python setup.py develop  # OR for a development install
```

## Usage

This section describes basic usage.

#### Quickstart Example

This InfluxDB client is designed to be very simple. It takes a URL to the
InfluxDB API on creation, and otherwise supplies all parameters per `write()`
call.

If the InfluxDB API returns an error that the chosen database does not exist,
the client will issue a `CREATE DATABASE ...` query, followed by retrying the
write request.

```python
from influx import InfluxDB

# This creates the client instance... subsequent calls with the same URL will
# return the exact same instance, allowing you to use socket pooling for faster
# requests with less resources.
client = InfluxDB('http://127.0.0.1:8086')

# Creating the database is optional - calls to write() will try to create the
# database if it does not exist.
client.create_database('mydatabase')

# You can write as many fields and tags as you like, or override the *time* for
# the data points
client.write('mydatabase', 'mymeasurement', fields={'value': 1.0},
             tags={'env': 'example'})

# You can clean up after yourself, for example in testing environments
client.drop_database('mydatabase')

# Subsequent client creation will give the same instance
client2 = InfluxDB('http://127.0.0.1:8086')
client is client2  # This is True
```

## Development

This section describes development and contribution for *influx-client*.

*TODO: Document this*

## API

This section describes the public API for *influx-client*.

### `InfluxDB(`*`url`*`)`

This is the main InfluxDB client. It works as a singleton instance per *url*.
In threaded or event loop based environments it relies on the *requests*
library connection pooling (which in turn relies on *urllib3*) for thread
safety.

- **url** (*str*) - URL to InfluxDB API (such as `'http://127.0.0.1:8086'`)

#### `.create_database(`*`database`*`)`

Issues a `CREATE DATABASE ...` request to the InfluxDB API. This is an
idempotent operation.

- **database** (*str*) - Database name

#### `.drop_database(`*`database`*`)`

Issues a `DROP DATABASE ...` request to the InfluxDB API. This will raise a 404
HTTPError if the database does not exist.

- **database** (*str*) - Database name

#### `.write(`*`database, measurement, fields, tags={}, time=None`*`)`

Write data points to the specified *database* and *measurement*.

- **database** (*str*) - Database name
- **measurement** (*str*) - Measurement name
- **fields** (*dict*) - Dictionary of *field_name: value* data points
- **tags** (*dict*, optional) - Dictionary of *tag_name: value* tags to
  associate with the data points
- **time** (*datetime*, optional) - Datetime to use instead of InfluxDB's
  server-side "now"

## License

This repository and its codebase are made public under the [Apache License
v2.0](./LICENSE). We ask that if you do use this work please attribute [Axiom
Exergy](http://www.axiomexergy.com) and link to the original repository.

## Changelog

See [Releases](https://github.com/AxiomExergy/influx-client/releases) for
detailed release notes.
