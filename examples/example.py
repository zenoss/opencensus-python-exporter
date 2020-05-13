# Copyright 2020, Zenoss, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
    main()
