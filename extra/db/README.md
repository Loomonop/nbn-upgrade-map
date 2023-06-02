The (excellent) upstream Docker image that contains all the GNAF data is huge (32GB).  In order to
consume less resources, we can create a cut-down version of this, with just the single table that
this tool actually uses, as well as a DB index already created.

In order to do this:

1. create a docker container using the upstream GNAF image
   1. select the table + columns into a CSV file (compressed)
   2. stop the container

2. build a new Docker image from basically the same Dockerfile as upstream, but with manual table and index creation, and data loaded from the CSV

This process is automated using [make-new-image.sh](make-new-image.sh)

The new Docker image is 3.73GB compared to the original 32GB.

```
❯ docker images
REPOSITORY           TAG       IMAGE ID       CREATED          SIZE
mydb                 latest    84af660a3493   39 seconds ago   3.73GB
minus34/gnafloader   latest    d2c552c72a0a   10 days ago      32GB
```

# References

- Hugh Saalmans Docker image containing all the GNAF data [gnaf-loader](https://github.com/minus34/gnaf-loader)

- [Dockerfile](https://github.com/minus34/gnaf-loader/blob/master/docker/Dockerfile) from that image