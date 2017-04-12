"""
Stats for pybench-mongodb
"""

import logging
import multiprocessing
import queue
import threading
import time


STATS_DUMP_DELAY = 2.0


class Timer:
    """Timer"""
    # pylint: disable=attribute-defined-outside-init,too-few-public-methods
    def __enter__(self):
        self.start = time.clock()
        return self

    def __exit__(self, *args):
        self.end = time.clock()
        self.interval = self.end - self.start


class Stats(object):
    """Stats class"""
    # pylint: disable=too-many-instance-attributes

    def __init__(self, max_iterations, max_time_seconds):
        self.max_iterations = max_iterations
        self.max_time_seconds = max_time_seconds
        self.interval = 5
        self.done = multiprocessing.Event()
        self.start_time = 0
        self.end_time = 0
        self.total_inserts = 0
        self.queue = multiprocessing.Queue(maxsize=500)
        self.data = {}
        self.lock = threading.Lock()

    def set_interval(self, interval):
        """set interval"""
        self.interval = interval

    def process_item(self, current_time, instance, counters):
        """process item"""
        time_index = int(int(current_time) / self.interval)
        if time_index not in self.data:
            self.data[time_index] = {}
        if instance not in self.data[time_index]:
            self.data[time_index][instance] = {"count": 0}
        for key in counters:
            self.data[time_index][instance][key] = \
                (self.data[time_index][instance].get(key, 0) +
                 counters[key])

        self.data[time_index][instance]["count"] += 1

        if instance == "insert" and "inserts" in counters:
            self.total_inserts += counters["inserts"]
            if self.total_inserts > self.max_iterations:
                self.done.set()

        if time.time() - self.start_time > self.max_time_seconds:
            self.done.set()

    def log(self, instance, counters):
        """log"""
        self.queue.put([time.time(), instance, counters])

    def start(self, interval=5):
        """start"""
        self.start_time = time.time()
        self.interval = interval
        self.lock.acquire()
        self.lock.release()
        thread = threading.Thread(target=self.stats_monitor)
        thread.start()

    def end(self):
        """end"""
        if self.end_time == 0:
            self.end_time = time.time()

    def stats_monitor(self):
        """monitor"""
        last_shown_index = 0

        logging.info("Starting stats monitor")

        while not self.done.is_set():
            time_index = (int(int(time.time() - self.interval - STATS_DUMP_DELAY) /
                              self.interval))

            self.lock.acquire()
            try:
                if time_index not in self.data:
                    self.data[time_index] = {}
            finally:
                self.lock.release()

            if time_index > last_shown_index:
                self.show_record(time_index)
                last_shown_index = time_index

            try:
                item = self.queue.get(True, 0.1)
            except queue.Empty:
                continue
            self.process_item(item[0], item[1], item[2])

        if last_shown_index + 1 in self.data:
            self.show_record(last_shown_index + 1)

        logging.info("Ending stats monitor")

    def show_record(self, time_index):
        """show record"""
        # pylint: disable=too-many-locals,too-many-branches

        if ((time_index+1) * self.interval) < self.start_time:
            return

        time_string = time.strftime(
            "%H:%M:%S",
            time.localtime(time_index * self.interval))

        if len(self.data[time_index]) == 0:
            print("{} {}s - no records".format(
                time_string,
                self.interval))
        else:
            inserts = 0
            for instance in sorted(self.data[time_index]):
                counters = self.data[time_index][instance]
                inserts += counters.get("inserts")

            # The first interval is truncated...
            interval = min(self.interval, ((time_index+1) * self.interval) - self.start_time)
            print("{} {}s - {}, {:0.1f}/s, cum: {}, {:0.1f}/s".format(
                time_string,
                self.interval,
                inserts,
                inserts / interval,
                self.total_inserts,
                self.total_inserts / (time.time() - self.start_time)
                ))
