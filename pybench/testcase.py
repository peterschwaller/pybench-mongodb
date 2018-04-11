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
from .throttle import Throttle


class Testcase(object):
    """Testcase"""
    def __init__(self, testcase_config, config):
        self.config = remerge([
            deepcopy(config.get("testcase-defaults", {})),
            deepcopy(testcase_config["steps"])
        ])
        self.name = testcase_config["name"]
        self.uri = ""

        self.compressible = "".join("a" for _ in range(10000))

        self.text = ""
        while len(self.text) < self.config["random-text-buffer-size"]:
            self.text += lorem.paragraph()

        self.bytes = bytes(
            [random.randrange(0, 256) for _ in range(self.config["random-bytes-buffer-size"])])

        self.throttles = {
            "insert": Throttle()
        }

        # self.throttles["insert"].set_rate(18000, batch=1000, processes=self.config["process-count"])

    def get_name(self):
        """get name"""
        return self.name

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

        while not stats.done.is_set():
            time.sleep(2)

        stats.end()

        logging.debug("Waiting on processes to finish.")
        for process in process_list:
            process.join(30)
            if process.is_alive():
                process.terminate()
                logging.info(
                    "One or more processes hasn't finished.  Manual cleanup may be required.")

        self._worker("cleanup")

    def _process(self, section, stats):
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

        for _, value in self.config.get(section, {}).items():
            if value["operation"] in ["insert", "upsert"]:
                max_iterations = value.get("count", None)
                self.insert(
                    value["operation"],
                    database,
                    ChainMap(value, self.config),
                    stats,
                    max_iterations=max_iterations)
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

    def insert(self, operation, database, command, stats, max_iterations=None):
        """insert"""
        # pylint: disable=too-many-branches
        iterations = 0

        batch_method = command.get("batch-method")
        batch_size = command.get("batch-size")

        bulk = self._get_bulk(database, batch_method, command.get("collection"))

        insert_array = []
        last_check = 0
        last_log = 0
        logged_inserts = 0

        while True:
            doc = self.build_doc(command.get("doc"), operation)
            iterations += 1

            # Only check every 5 seconds
            if time.time() - last_check > 5:
                last_check = time.time()
                if stats and stats.done.is_set():
                    break

            if bulk:
                if operation == "insert":
                    bulk.insert(doc)
                elif operation == "upsert":
                    bulk.find({"_id": doc["_id"]}).upsert().update_one({"$set": doc})
                else:
                    assert False
                if iterations % batch_size == 0:
                    self.throttles["insert"].wait()
                    bulk.execute()
                    if stats:
                        stats.log("insert", {"inserts": batch_size})
                    bulk = self._get_bulk(database, batch_method, command.get("collection"))
            elif batch_method == "array":
                assert operation == "insert"
                insert_array.append(doc)
                if iterations % batch_size == 0:
                    self.throttles["insert"].wait()
                    database[command.get("collection")].insert(insert_array)
                    if stats:
                        stats.log("insert", {"inserts": batch_size})
                    insert_array = []
            elif batch_method == "single":
                self.throttles["insert"].wait()
                if operation == "insert":
                    database[command.get("collection")].insert(doc)
                elif operation == "upsert":
                    database[command.get("collection")].update_one(
                        {"_id": doc["_id"]},
                        {"$set": doc},
                        upsert=True)
                else:
                    assert False
                logged_inserts += 1
                current_time = time.time()
                if stats and current_time - last_log > 0.2:
                    stats.log("insert", {"inserts": logged_inserts})
                    logged_inserts = 0
                    last_log = current_time
            else:
                assert False

            if max_iterations and iterations > max_iterations:
                break

    def build_doc(self, input_doc, operation):
        """build doc"""
        doc = {}
        for key, value in input_doc.items():
            doc[key] = self.resolve_value(value)
        if operation == "upsert":
            doc["_id"] = uuid.uuid4()
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
