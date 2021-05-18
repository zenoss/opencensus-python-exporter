# OpenCensus Zenoss Exporter for Python

A Python library intended to be used in Python applications instrumented with
OpenCensus to export stats to Zenoss.

## Status

This library is in an alpha stage, and the API is subject to change.

## Installation

The package can be installed with the following command.

```shell script
pip install opencensus-ext-zenoss
```

## Usage

The following example shows how to configure the exporter.

```python
from opencensus.ext.zenoss import stats_exporter as zenoss
from opencensus.stats import stats as stats_module

stats = stats_module.stats
view_manager = stats.view_manager

exporter = zenoss.new_stats_exporter(
    zenoss.Options(api_key="YOUR-ZENOSS-API-KEY"))

view_manager.register_exporter(exporter)
```

### Options

The following options are available when creating a stats exporter.

* `address`: Zenoss API address. Default is https://api.zenoss.io.
* `api_key`: Zenoss API key.
* `source`: Added as a tag to all sent metrics. Recommended.
* `extra_tags`: Map of additional tags to add to all sent metrics. Default is {}.
* `insecure_tls`: Set to True to disable server certification verification. Default is False.

### Tags

The tags associated with exported metrics are very important in determining how
the metrics will be handled by Zenoss. Without adding appropriate tags to the
metrics, and creating corresponding Zenoss policy, you will not be able to see
the metrics in Zenoss.

The metrics sent via the Zenoss exporter by default will have only the explicit
tags added via the OpenCensus view and record APIs, and a _source-type_ tag
equal to "zenoss/opencensus-python-exporter". You should also typically specify
the _source_ argument when creating the Zenoss exporter to also add a _source_
tag to all exported metrics. This enables you to add your source to Zenoss
dashboard scopes.

For the simplest case where you want all the metrics sent by your app to be
associated with a single entity in Zenoss, you don't need to specify any
additional tags in _extra_tags_. You must just choose a value for the _source_
tag that uniquely identifies the Zenoss entity you want the metrics to be
associated with. For example, "app.example.com".

### Zenoss Policy

Assuming your metrics are being sent to Zenoss with the _source_ and
_source-type_ tags setup as described above, you will need to create Zenoss
policy to control which tags become metric dimensions, and the dimensions for
the entity that will be created for the metrics.

First you need to create a metric ingest policy that controls which tags will
be dimensions, and which will be metadata. This metric ingest policy will also
be used to automatically create entities (via models) with which the metrics
will be associated.

```shell script
cat << EOF | curl https://api.zenoss.io/v1/policy/custom/ingests \
    -H "zenoss-api-key: YOUR-API-KEY" -X POST -s -d @-
{
    "name": "metricIngest_opencensus",
    "requiredKeys": ["source", "source-type"],
    "dimensionKeys": ["source"],
    "metadataKeys": ["source-type"],
    "useAllKeysAsDims": false,
    "excludeInternalFromAllKeysAsDims": true,
    "generateEntityId": true,
    "entityDimensionKeys": ["source"],
    "contributeModelInfo": true
}
EOF
```

You will next need a model ingest policy to handle the generated model generated
by the metric ingest policy. Note that we're copying the value of the _source_
tag into the _name_ metadata field. This _name_ field gives our entity its name.

```shell script
cat << EOF | curl https://api.zenoss.io/v1/policy/custom/ingests \
    -H "zenoss-api-key: YOUR-API-KEY" -X POST -s -d @-
{
    "name": "modelIngest_opencensus",
    "requiredKeys": ["source", "source-type"],
    "fieldTransforms": [
        {
            "operation": "COPY",
            "sourceKey": "source",
            "targetKey": "name"
        }
    ],
    "dimensionKeys": ["source"],
    "metadataKeys": ["source-type", "name"],
    "useAllKeysAsDims": false,
    "excludeInternalFromAllKeysAsDims": true,
    "generateEntityId": true,
    "entityDimensionKeys": ["source"]
}
EOF
```

Lastly we must create a datasource that applies the previous two policies to
all data with a _source-type_ of "zenoss/opencensus-python-exporter".

```shell script
cat << EOF | curl https://api.zenoss.io/v1/policy/custom/datasources \
    -H "zenoss-api-key: YOUR-API-KEY" -X POST -s -d @-
{
    "sourceType": "zenoss/opencensus-python-exporter",
    "policyReferences": [
        {
            "dataType": "METRIC",
            "policyType": "INGEST",
            "policyName": "metricIngest_opencensus"
        },
        {
            "dataType": "DATAMAP",
            "policyType": "INGEST",
            "policyName": "modelIngest_opencensus"
        }
    ]
}
EOF
```

Note that you can override the value of the _source-type_ tag by supplying it
in the _extra_tags_ argument when creating the Zenoss exporter. This would allow
you to define a separate datasource with different policies.

### Example Application

The following is a complete example of an application that will write to a
measure once per second for 100 seconds. A distribution view is created for
measure that will be exported to Zenoss once every 10 seconds.

```python
import os
import random
import sys
import time

from opencensus.ext.zenoss import stats_exporter as zenoss
from opencensus.stats import aggregation as aggregation_module
from opencensus.stats import measure as measure_module
from opencensus.stats import stats as stats_module
from opencensus.stats import view as view_module
from opencensus.tags import tag_map as tag_map_module

# Setup aliases to make working with OpenCensus easier.
stats = stats_module.stats
view_manager = stats.view_manager
stats_recorder = stats.stats_recorder

# Create a measure.
m_latency_ms = measure_module.MeasureFloat(
    "task_latency", "The task latency in milliseconds", "ms")

# Create a view using the measure.
latency_view = view_module.View(
    "task_latency_distribution",
    "The distribution of the task latencies",
    [],
    m_latency_ms,
    # Latency in buckets: [>=0ms, >=100ms, >=200ms, >=400ms, >=1s, >=2s, >=4s]
    aggregation_module.DistributionAggregation(
        [100.0, 200.0, 400.0, 1000.0, 2000.0, 4000.0]))


def main():
    address = os.environ.get("ZENOSS_ADDRESS", zenoss.DEFAULT_ADDRESS)
    api_key = os.environ.get("ZENOSS_API_KEY")
    if not api_key:
        sys.exit("ZENOSS_API_KEY must be set")

    # Create Zenoss exporter.
    exporter = zenoss.new_stats_exporter(
        options=zenoss.Options(
            address=address,
            api_key=api_key,
            source="app.example.com"),
        interval=10)

    # Register Zenoss exporter.
    view_manager.register_exporter(exporter)

    # Register our example view.
    view_manager.register_view(latency_view)

    # Prepare measurement map, and tag map we can reuse for each sample.
    measurement_map = stats_recorder.new_measurement_map()
    tag_map = tag_map_module.TagMap()

    # Record one random measurement each second for 100 seconds.
    print("Recording measurements:")
    for i in range(100):
        ms = random.random() * 5 * 1000
        print("  - latency {}:{}".format(i, ms))
        measurement_map.measure_float_put(m_latency_ms, ms)
        measurement_map.record(tag_map)
        time.sleep(1)


if __name__ == "__main__":
    import logging

    # Setup default logging configuration.
    logging.basicConfig()

    # Change level of Zenoss exporter's logging to debug.
    logging.getLogger("opencensus.ext.zenoss").setLevel(logging.DEBUG)

    main()
```

## Useful Links

* For more information about Zenoss, visit: <https://zenoss.com>.
* For more information about OpenCensus, visit: <https://opencensus.io>.
