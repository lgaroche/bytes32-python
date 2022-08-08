#!/bin/bash

core="bytes32_rinkeby"
docker run -d -v "$PWD/solrdata:/var/solr" -p 8983:8983 --name solr_${core} solr:8 solr-precreate $core