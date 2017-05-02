#!/bin/sh
pybench-mongodb examples/database.hjson examples/iibench.hjson examples/array.hjson
pybench-mongodb examples/database.hjson examples/iibench.hjson examples/unordered.hjson
pybench-mongodb examples/database.hjson examples/iibench.hjson examples/ordered.hjson
pybench-mongodb examples/database.hjson examples/iibench.hjson examples/single.hjson
