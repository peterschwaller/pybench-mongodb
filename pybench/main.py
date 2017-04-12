"""
Main for pybench-mongodb
"""
import argparse
from datetime import datetime
import logging
import sys
import time

import hjson

from pybench import __version__
from .mongod import Mongod
from .remerge import remerge
from .stats import Stats
from .testcase import Testcase


def load_config(config_files):
    """load config"""

    config_list = []
    for config_path in config_files:
        with open(config_path, "r") as cfg:
            config_list.append(hjson.load(cfg))

    return remerge(config_list)


def logging_numeric_level(level):
    """Return the numeric log level given a standard keyword"""
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise SystemExit("invalid log level: {}".format(level))
    return numeric_level


def parse_args():
    """parse the command line arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "configfiles",
        metavar='CONFIG_FILES',
        nargs='+',
        help="json configuration files")
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s {}".format(__version__))
    parser.add_argument(
        "--results-path",
        default="results/",
        help="folder in which to store results files")
    parser.add_argument(
        "--log-level",
        help="specify logging level")
    parser.add_argument(
        "--log-times",
        action="store_true",
        help="timestamp console logs")
    return parser.parse_args()


def setup_logging(root, log_level, log_times):
    """do the logging stuff"""
    logging.Formatter.converter = time.gmtime
    logformat = "%(levelname)s: [%(funcName)s] %(message)s"
    datelogformat = "%(asctime)s.%(msecs)03dZ pid=%(process)s t=%(threadName)s - " + logformat
    datefmt = "%Y-%m-%dT%H:%M:%S"
    logging.basicConfig(
        filename=root + ".log",
        format=datelogformat,
        level=logging_numeric_level(log_level),
        datefmt=datefmt)

    # set logging to occur to stdout as well as to the file
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        datelogformat if log_times else logformat,
        datefmt=datefmt))

    root = logging.getLogger()
    root.setLevel(logging_numeric_level(log_level))
    root.addHandler(handler)


def main():
    """main"""
    args = parse_args()

    root = "pybench"
    if args.log_level:
        setup_logging(root, args.log_level, args.log_times)
    else:
        setup_logging(root, "INFO", args.log_times)

    config = load_config(args.configfiles)

    mongods = []
    for database_config in config["databases"]:
        mongods.append(Mongod(database_config, config))

    for mongod in mongods:
        if mongod.is_enabled():
            mongod.start()

            try:
                testcase = Testcase(
                    config["testcase"],
                    config)

                stats = Stats(
                    testcase.config.get("max-iterations"),
                    testcase.config.get("max-time-seconds"))

                time_string = time.strftime(
                    "%Y-%m-%d %H:%M",
                    time.localtime())
                testcase.run(mongod.get_uri(), stats)


            finally:
                stats.end()
                filename = "{} - {} {}".format(mongod.get_name(), testcase.get_name(), time_string)
                with open(filename + ".csv", "w") as output:
                    stats.save(output)
                mongod.shutdown()


if __name__ == "__main__":
    main()
