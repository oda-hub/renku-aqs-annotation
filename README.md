# renku-aqs-annotation

This renku plugin provides the following functionalities:

* Generate annotations describing access to astronomical archives and services by intercepting any call to the following methods of `astroquery` classes:
  * query_object
  * get_images
  * query_region
* CLI `inspect` to analyze data analysis notebooks and extract a set of metadata and record it in the local knowledge graph.
This is executed by using the [https://github.com/oda-hub/nb2workflow]() library
* CLI to start a renku session

    ```renku aqs start-session```