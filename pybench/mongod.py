"""
Mongod
"""
from copy import deepcopy
import logging
import os
import shutil

from .remerge import remerge


class Mongod(object):
    """Mongod class"""

    def __init__(self, database_config, config):
        self.database_config = deepcopy(database_config)
        self.defaults = deepcopy(config.get("database-defaults", {}))
        self.config = remerge([self.defaults, self.database_config])

    def is_enabled(self):
        """is enabled"""
        return not self.config.get("disabled", False)

    def get_name(self):
        """get name"""
        return self.config["name"]

    def start(self):
        """start"""
        if self.config.get("clear-paths"):
            logging.debug("Clearing DB paths.")
            for file in ["logpath", "pidfilepath"]:
                path = self.config["options"].get(file)
                if path:
                    try:
                        os.remove(path)
                    except FileNotFoundError:
                        pass
            if "dbpath" in self.config["options"]:
                try:
                    shutil.rmtree(self.config["options"]["dbpath"])
                except FileNotFoundError:
                    pass

        if "dbpath" in self.config["options"]:
            os.makedirs(self.config["options"]["dbpath"], exist_ok=True)

        cmd = "mongod"
        for key, value in self.config["options"].items():
            cmd += " --{} {}".format(key, value if value is not None else "")
        if "quiet" in self.config["options"]:
            cmd += " > /dev/null"

        logging.info("Starting database with command: %s", cmd)
        os.system(cmd)
        logging.info("Started %s", self.config.get("name"))

    def shutdown(self):
        """shutdown"""
        cmd = "mongod --shutdown"
        if "dbpath" in self.config["options"]:
            cmd += " --dbpath {}".format(self.config["options"]["dbpath"])
        if "quiet" in self.config["options"]:
            cmd += " --quiet"
            cmd += " > /dev/null"

        logging.debug("Shutting down database with command: %s", cmd)
        os.system(cmd)
        logging.info("Stopped %s", self.config.get("name"))

    def get_uri(self):
        """get uri"""
        return "mongodb://localhost:{}/".format(self.config["options"].get("port", 27017))
