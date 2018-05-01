"""
# Fixture helpers

"""
# Stdlib
import os

# 3rd party
import pytool


# Constants
BASE_DIR = './fixtures'


# Classes
class FixtureLoader(object):
    def __init__(self, extension, mode='r', loader=lambda d: d):
        self.mode = mode
        self.extension = extension
        self.cache = {}
        self.loader = loader

    def __getattr__(self, attr):
        # Attempt to use the cache for speed
        if attr in self.cache:
            return self.cache[attr]

        # TODO: Better error handling
        with open(self.filename(attr), self.mode) as fixture:
            data = fixture.read()

        # Load the data and cache it for later
        data = self.loader(data)
        self.cache[attr] = data

        return data

    def filename(self, attr):
        # TODO: Make the directory configurable
        name = "{}.{}".format(attr, self.extension)
        return os.path.join(BASE_DIR, name)


# Module level loaders
json = FixtureLoader('json', loader=pytool.json.from_json)
raw_json = FixtureLoader('json', loader=lambda v: v)
