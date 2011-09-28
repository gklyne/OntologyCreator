#!/bin/bash
#
# make owl files
#

if [[ "$1" == "" ]]; then
    echo "Usage: $0 <filename>"
    echo "  reads from <filename>.csv, writes to <filename>.owl"
    exit 1
fi

python ConvertOntology.py -r $1.csv >$1.owl

# End.
