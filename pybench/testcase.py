"""
Testcase class
"""
from collections import ChainMap
from copy import deepcopy
from datetime import datetime, timedelta
import logging
from multiprocessing import Process
import random
import threading
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
        self.uri = ""

        self.compressible = "".join("a" for _ in range(10000))

        self.text = ""
        while len(self.text) < self.config["random-text-buffer-size"]:
            self.text += lorem.paragraph()

        self.bytes = bytes(
            [random.randrange(0, 256) for _ in range(self.config["random-bytes-buffer-size"])])

    def connect(self):
        """connect"""
        return pymongo.MongoClient(self.uri, tz_aware=True)[self.config.get("db-name", "pybench")]

    def run(self, uri, stats):
        """run"""
        self.uri = uri

        self._worker("startup")
        stats.start()

        process_list = []
        for _ in range(self.config.get("process-count")):
            process = Process(
                target=self._process,
                args=("testing", stats, ))
            process_list.append(process)
            process.start()
        for process in process_list:
            process.join()

        stats.end()
        self._worker("cleanup")

    def _process(self, section, stats):
        print("stats", stats.start_time)
        threads = []
        for _ in range(self.config.get("threads-per-process")):
            thread = threading.Thread(
                target=self._worker, args=(section, stats, ))
            thread.start()
            threads.append(thread)
        for thread in threads:
            thread.join()

    def _worker(self, section, stats=None):
        """startup"""
        database = self.connect()

        if self.config.get(section):
            logging.debug("Processing %d %s commands.", len(self.config[section]), section)
        else:
            logging.debug("No %s commands to process.", section)

        for key, value in self.config.get(section, {}).items():
            logging.debug("Processing %s", key)
            if value["operation"] == "insert":
                self.insert(database, ChainMap(value, self.config), stats)
            elif value["operation"] == "index":
                self.create_indexes(database, value)
            else:
                assert False

    def _get_bulk(self, database, method, collection):
        """get bulk"""
        # pylint: disable=no-self-use
        if method == "unordered-bulk":
            bulk = database[collection].initialize_unordered_bulk_op()
        elif method == "ordered-bulk":
            bulk = database[collection].initialize_ordered_bulk_op()
        else:
            bulk = None
        return bulk

    def insert(self, database, command, stats):
        """insert"""
        # pylint: disable=too-many-branches
        iterations = 0

        insert_method = command.get("batch-method")
        batch_size = command.get("batch-size")

        bulk = self._get_bulk(database, insert_method, command.get("collection"))

        insert_array = []
        last_check = 0
        while True:
            doc = self.build_doc(command.get("doc"))
            iterations += 1

            # Only check every 5 seconds
            if time.time() - last_check > 5:
                last_check = time.time()
                if stats.done.is_set():
                    break

            if bulk:
                bulk.insert(doc)
                if iterations % batch_size == 0:
                    bulk.execute()
                    if stats:
                        stats.log("insert", {"inserts": batch_size})
                    bulk = self._get_bulk(database, insert_method, command.get("collection"))
            elif insert_method == "array":
                insert_array.append(doc)
                if iterations % batch_size == 0:
                    database[command.get("collection")].insert(insert_array)
                    if stats:
                        stats.log("insert", {"inserts": batch_size})
                    insert_array = []
            elif insert_method == "single":
                database[command.get("collection")].insert(doc)
                if stats:
                    stats.log("insert", {"inserts": 1})
            else:
                assert False

    def build_doc(self, input_doc):
        """build doc"""
        doc = {}
        for key, value in input_doc.items():
            doc[key] = self.resolve_value(value)
        return doc

    def resolve_value(self, value):
        """resolve value"""
        # pylint: disable=too-many-return-statements,too-many-branches

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
            elif key == "random-float":
                return random.random() * value
            elif key == "random-list":
                return value[random.randrange(0, len(value))]
            elif key == "iibench-string":
                compress_count = int((value["percent-compressible"] / 100) * value["length"])
                noncompress_count = value["length"] - compress_count
                start = random.randrange(0, len(self.text)-noncompress_count)
                end = start+noncompress_count
                return self.text[start:end] + self.compressible[0:compress_count]
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
        """create indexes"""
        # pylint: disable=no-self-use

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
