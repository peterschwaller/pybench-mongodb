"""
Mongod
"""
from copy import deepcopy
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

    def start(self):
        """start"""
        if self.config["options"].get("clear-paths"):
            for file in ["logpath", "pidfilepath"]:
                path = self.config["options"].get(file)
                if path:
                    os.remove(path)
            if "dbpath" in self.config["options"]:
                shutil.rmtree(self.config["options"]["dbpath"])

        if "dbpath" in self.config["options"]:
            print("dbpath", self.config["options"]["dbpath"])
            os.makedirs(self.config["options"]["dbpath"], exist_ok=True)

        cmd = "mongod"
        for key, value in self.config["options"].items():
            cmd += " --{} {}".format(key, value if value is not None else "")

        print(cmd)
        os.system(cmd)
        print("cmd finished")

    def shutdown(self):
        """shutdown"""
        cmd = "mongod --shutdown"
        if "dbpath" in self.config["options"]:
            cmd += " --dbpath {}".format(self.config["options"]["dbpath"])
        if "quiet" in self.config["options"]:
            cmd += " --quiet"

        print(cmd)
        os.system(cmd)
        print("cmd finished")

    def get_uri(self):
        """get uri"""
        return "mongodb://localhost:{}/".format(self.config["options"].get("port", 27017))
