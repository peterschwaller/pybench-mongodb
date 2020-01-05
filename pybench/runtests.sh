#!/bin/sh
pybench-mongodb examples/database.hjson examples/iibench.hjson examples/array.hjson
pybench-mongodb examples/database.hjson examples/iibench.hjson examples/unordered.hjson
pybench-mongodb examples/database.hjson examples/iibench.hjson examples/single.hjson
pybench-mongodb examples/database.hjson examples/iibench.hjson examples/unordered-upsert.hjson
pybench-mongodb examples/database.hjson examples/iibench.hjson examples/single-upsert.hjson
