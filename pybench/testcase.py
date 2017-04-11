"""
Testcase class
"""
from copy import deepcopy
import logging
import random
import time

from bson.binary import Binary
import lorem
import pymongo

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
        print(uri)
        database = self.connect(uri)
        self.startup(database)

    def startup(self, database):
        """startup"""
        if self.config.get("startup"):
            logging.info("Processing %d startup commands.", len(self.config["startup"]))
        else:
            logging.info("No startup commands to process.")

        for key, value in self.config.get("startup", {}).items():
            logging.info("Processing %s", key)
            if value["operation"] == "insert":
                self.insert(database, value)
            elif value["operation"] == "index":
                self.create_indexes(database, value)
            else:
                assert False

    def insert(self, database, command):
        """insert"""
        print(command)

        iterations = 0
        start_time = time.time()
        while iterations < command["max-iterations"]:
            doc = self.build_doc(command["doc"])
            database[self.config["db-name"]][self.config["collection"]].insert(doc)
            iterations += 1

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
            else:
                assert False

    def create_indexes(self, database, command):

        for collection in command["indexes"]:
            logging.info("Creating indexes for %s.", collection)
            for item in command["indexes"][collection]:
                index = [(x[0], x[1]) for x in item["index"]]
                logging.info("Creating %s.", index)
                if "kwargs" in item:
                    database[collection].create_index(
                        index,
                        background=True,
                        **item["kwargs"])
                else:
                    database[self.config["db-name"]][collection].create_index(
                        index,
                        background=True)
