"""
Main for pybench-mongodb
"""
import hjson
import time

from .database import Database


def load_config(config_path):
    """load config"""
    with open(config_path, "r") as cfg:
        return hjson.load(cfg)


def main():
    """main"""
    config = load_config("examples/database.json")

    databases = []
    for database_config in config["databases"]:
        databases.append(Database(database_config, config.get("database-defaults", {})))

    for database in databases:
        if database.is_enabled():
            database.start()
            time.sleep(5)
            database.shutdown()


if __name__ == "__main__":
    main()
