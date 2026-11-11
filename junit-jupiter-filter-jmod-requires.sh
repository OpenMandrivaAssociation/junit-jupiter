#!/bin/sh
# jar --describe-module records jmod(name@version). junit6 and opentest4j
# publish only that versioned provide, so the unversioned require cannot
# be installed. The explicit versioned Requires in the spec cover them.
/usr/lib/rpm/jmod.deps "$@" | grep -v -E '^jmod\(org\.junit\.platform\.(commons|engine)\)$|^jmod\(org\.opentest4j\)$' || [ $? -eq 1 ]
