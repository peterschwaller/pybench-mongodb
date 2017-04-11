"""
Testcase class
"""
from collections import ChainMap
from copy import deepcopy
from datetime import datetime, timedelta
import logging
import random
import time
import uuid

from bson.binary import Binary
import lorem
import pymongo
from pytz import utc

from .remerge import remerge


class Testcase(object):
    """Testcase"""
    def __init__(self, testcase_config, config):
        self.config = remerge([
            deepcopy(config.get("testcase-defaults", {})),
            deepcopy(testcase_config)
        ])
        self.text = ""
        while len(self.text) < self.config["random-text-buffer-size"]:
            self.text += lorem.paragraph()

        self.bytes = bytes(
            [random.randrange(0, 256) for _ in range(self.config["random-bytes-buffer-size"])])

    def connect(self, uri):
        """connect"""
        return pymongo.MongoClient(uri, tz_aware=True)[self.config.get("db-name", "pybench")]

    def run(self, uri):
        """run"""
        database = self.connect(uri)
        self._process(database, "startup")
        self._process(database, "testing")
        self._process(database, "cleanup")

    def _process(self, database, section):
        """startup"""
        if self.config.get(section):
            logging.debug("Processing %d %s commands.", len(self.config[section]), section)
        else:
            logging.debug("No %s commands to process.", section)

        for key, value in self.config.get(section, {}).items():
            logging.debug("Processing %s", key)
            if value["operation"] == "insert":
                self.insert(database, ChainMap(value, self.config))
            elif value["operation"] == "index":
                self.create_indexes(database, value)
            else:
                assert False

    def _get_bulk(self, database, method, collection):
        """get bulk"""
        if method == "unordered-bulk":
            bulk = database[collection].initialize_unordered_bulk_op()
        elif method == "ordered-bulk":
            bulk = database[collection].initialize_ordered_bulk_op()
        else:
            bulk = None
        return bulk


    def insert(self, database, command):
        """insert"""
        iterations = 0
        start_time = time.time()

        insert_method = command.get("batch-method")
        batch_size = command.get("batch-size")

        bulk = self._get_bulk(database, insert_method, command.get("collection"))

        insert_array = []
        while iterations < command.get("max-iterations"):
            doc = self.build_doc(command.get("doc"))
            iterations += 1

            if bulk:
                bulk.insert(doc)
                if iterations % batch_size == 0:
                    bulk.execute()
                    bulk = self._get_bulk(database, insert_method, command.get("collection"))
            elif insert_method == "array":
                insert_array.append(doc)
                if iterations % batch_size == 0:
                    database[command.get("collection")].insert(insert_array)
                    insert_array = []
            elif insert_method == "single":
                database[command.get("collection")].insert(doc)
            else:
                assert False

        # Need to write out last records if max-iterations isn't a multiple of batch-size
        if bulk:
            if iterations % batch_size != 0:
                bulk.execute()
        elif insert_method == "array":
            if iterations % batch_size != 0:
                database[command.get("collection")].insert(insert_array)

        print("ELAPSED", time.time() - start_time)

    def build_doc(self, input_doc):
        """build doc"""
        doc = {}
        for key, value in input_doc.items():
            doc[key] = self.resolve_value(value)
        return doc

    def resolve_value(self, value):
        if isinstance(value, str):
            return value
        elif isinstance(value, int):
            return value
        elif isinstance(value, float):
            return value
        elif isinstance(value, dict):
            assert len(value) == 1
            key, value = list(value.items())[0]

            if key == "random-int":
                return random.randint(value[0], value[1])
            elif key == "random-list":
                return value[random.randrange(0, len(value))]
            elif key == "random-text":
                length = self.resolve_value(value)
                start = random.randrange(0, len(self.text)-length)
                end = start+length
                return self.text[start:end]
            elif key == "random-bytes":
                length = self.resolve_value(value)
                start = random.randrange(0, len(self.bytes)-length)
                end = start+length
                return Binary(self.bytes[start:end], 3)
            elif key == "date":
                offset = self.resolve_value(value)
                return datetime.now(tz=utc) + timedelta(seconds=offset)
            elif key == "uuid":
                assert value is None
                return uuid.uuid4()
            elif key == "uuid-string":
                assert value is None
                return str(uuid.uuid4())
            else:
                assert False

    def create_indexes(self, database, command):

        for collection in command["indexes"]:
            logging.debug("Creating indexes for %s.", collection)
            for item in command["indexes"][collection]:
                index = [(x[0], x[1]) for x in item["index"]]
                logging.debug("Creating %s.", index)
                if "kwargs" in item:
                    database[collection].create_index(
                        index,
                        background=True,
                        **item["kwargs"])
                else:
                    database[collection].create_index(
                        index,
                        background=True)
