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

## Options

The following options are available when creating a stats exporter.

* `address`: Zenoss API address. Default is https://api.zenoss.io.
* `api_key`: Zenoss API key.
* `source`: Added as a tag to all sent metrics. Recommended.
* `extra_tags`: Map of additional tags to add to all sent metrics. Default is {}.
* `insecure_tls`: Set to True to disable server certification verification. Default is False.

Example Application
-------------------

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
        period=10)

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
    main()
```

## Useful Links

* For more information about Zenoss, visit: <https://zenoss.com>.
* For more information about OpenCensus, visit: <https://opencensus.io>.
