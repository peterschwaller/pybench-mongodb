"""
Throttle
"""

import time
import threading


class Throttle:
    """Throttle"""
    def __init__(self):
        self.lock = threading.Lock()
        self.last_time = 0
        self.interval = 0

    def set_interval(self, interval):
        """set interval (seconds)"""
        self.interval = interval

    def set_rate(self, rate, batch=1, processes=1):
        """set rate"""
        if rate > 0:
            self.interval = 1 / (rate / (batch * processes))
        else:
            self.interval = 0

    def wait(self):
        """wait"""
        if self.interval == 0:
            return

        self.lock.acquire()
        try:
            sleep_time = self.interval - (time.time() - self.last_time)
            if sleep_time > 0:
                time.sleep(sleep_time)
            self.last_time = time.time()
        finally:
            self.lock.release()
