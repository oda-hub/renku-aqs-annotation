# renku-oda-annotation

This renku plugin provides the following functionalities:

* Generate astroquery specific annotations by intercepting the call to the following functions:
  * query_object
  * get_images
  * query_region
* CLI `inspect` to analyze input notebooks and extract a set of metadata to be visualized over the knowledge graph.
This is executed by using the [https://github.com/oda-hub/nb2workflow]() library
* CLI to start a renku session

    ```renku aqs start-session```