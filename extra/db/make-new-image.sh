#!/bin/bash -x

# extract just the table+columns we want from the upstream DB
docker run -d --publish=5433:5432 --name db minus34/gnafloader:latest
sleep 5
docker exec db psql -c "copy (SELECT gnaf_pid, address, locality_name, postcode, state, latitude, longitude FROM gnaf_202305.address_principals) to stdout with CSV HEADER;" | \
  gzip -9 > address_principals.csv.gz
docker rm -f db

# build a new docker image using the file above
docker build . -t mydb:latest

# test the new image (a bit slow to start)
# docker run -d --publish=5433:5432 --name mydb mydb:latest
# sleep 5
# docker exec -it mydb psql -c 'select * from gnaf_cutdown.address_principals limit 10'
