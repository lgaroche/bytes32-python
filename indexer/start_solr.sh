#!/bin/bash

core="bytes32_local"

mkdir -p $PWD/solrdata
chown -R 8983:8983 $PWD/solrdata
docker run -d -v "$PWD/solrdata:/var/solr" -p 8983:8983 --name solr_${core} solr:9 solr-precreate $core