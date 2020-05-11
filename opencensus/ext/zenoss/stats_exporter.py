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

import datetime
import json
import logging
import requests
import time
import urllib3

from opencensus.metrics import transport
from opencensus.metrics.export import metric as metric_module
from opencensus.metrics.export import metric_descriptor
from opencensus.stats import stats

DEFAULT_ADDRESS = "https://api.zenoss.io"
DEFAULT_INTERVAL = 60
DEFAULT_SOURCE_TYPE = "zenoss/opencensus-python-exporter"
API_KEY_FIELD = "zenoss-api-key"
SOURCE_FIELD = "source"
SOURCE_TYPE_FIELD = "source-type"
DESCRIPTION_FIELD = "description"
UNITS_FIELD = "units"

EPOCH = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)


class Options(object):
    """Exporter configuration options."""

    def __init__(
            self,
            address=DEFAULT_ADDRESS,
            api_key=None,
            source=None,
            extra_tags=None,
            insecure_tls=False,
    ):
        self.address = address
        self.api_key = api_key
        self.source = source
        self.extra_tags = extra_tags or {}
        self.insecure_tls = insecure_tls

        if SOURCE_TYPE_FIELD not in self.extra_tags:
            self.extra_tags[SOURCE_TYPE_FIELD] = DEFAULT_SOURCE_TYPE

        if source and SOURCE_FIELD not in self.extra_tags:
            self.extra_tags[SOURCE_FIELD] = source

        if self.insecure_tls:
            urllib3.disable_warnings()


class ZenossStatsExporter(object):
    """Stats exporter for Zenoss."""

    def __init__(self, options=None):
        self.options = options or Options
        self.logger = logging.getLogger(__name__)

    def export_metrics(self, metrics):
        now = datetime.datetime.utcnow()
        tagged_metrics = []

        def add_metric(name, timestamp, value, tags):
            tagged_metrics.append({
                "metric": name,
                "timestamp": int(datetime_timestamp(timestamp or now) * 1000),
                "value": value,
                "tags": tags,
            })

        for metric in metrics:
            if not isinstance(metric, metric_module.Metric):
                continue

            descriptor = metric.descriptor

            for ts in metric.time_series:
                tags = {}
                for k, v in zip(descriptor.label_keys, ts.label_values):
                    tags[k.key] = v.value

                if descriptor.description:
                    tags[DESCRIPTION_FIELD] = descriptor.description

                if descriptor.unit:
                    tags[UNITS_FIELD] = descriptor.unit

                # extra_tags override metric tags.
                for k, v in self.options.extra_tags.items():
                    tags[k] = v

                for point in ts.points:
                    value = point.value

                    # "Regular" metric types.
                    if descriptor.type in (
                            metric_descriptor.MetricDescriptorType.CUMULATIVE_DOUBLE,
                            metric_descriptor.MetricDescriptorType.GAUGE_DOUBLE,
                            metric_descriptor.MetricDescriptorType.CUMULATIVE_INT64,
                            metric_descriptor.MetricDescriptorType.GAUGE_INT64):
                        add_metric(descriptor.name, point.timestamp, value.value, tags)

                    # Distribution metric types.
                    elif descriptor.type in (
                            metric_descriptor.MetricDescriptorType.CUMULATIVE_DISTRIBUTION,
                            metric_descriptor.MetricDescriptorType.GAUGE_DISTRIBUTION):
                        for s, v in {
                            "count": value.count,
                            "sum": value.sum,
                            "ss": value.sum_of_squared_deviation,
                            "mean": 0 if not value.count else value.sum / value.count,
                        }.items():
                            add_metric(
                                "{}/{}".format(descriptor.name, s),
                                point.timestamp, v, tags)

                    # Summary metric type.
                    elif descriptor.type == metric_descriptor.MetricDescriptorType.SUMMARY:
                        for s, v in {
                            "count": point.count,
                            "sum": point.sum,
                        }.items():
                            add_metric(
                                "{}/{}".format(descriptor.name, s),
                                point.timestamp, v, tags)

                    # Currently no other types, but log to be safe.
                    else:
                        self.logger.warning("unknown metric type: %s", metric.descriptor.type)

        if len(tagged_metrics) > 0:
            self.send_tagged_metrics(tagged_metrics)

    def send_tagged_metrics(self, tagged_metrics):
        metrics_url = "{}/v1/data-receiver/metrics".format(self.options.address)
        headers = {}
        if self.options.api_key:
            headers[API_KEY_FIELD] = self.options.api_key

        try:
            r = requests.post(
                metrics_url,
                verify=not self.options.insecure_tls,
                data=json.dumps({"taggedMetrics": tagged_metrics}))

            if not r.ok:
                r.raise_for_status()

            self.logger.debug("sent metrics: %s", r.json())
        except Exception as e:
            self.logger.error("failed to send metrics: %s", e)


def new_stats_exporter(options=None, interval=DEFAULT_INTERVAL):
    """Return a stats exporter and running transport thread."""
    exporter = ZenossStatsExporter(options=options)
    transport.get_exporter_thread([stats.stats], exporter, interval=interval)
    return exporter


def datetime_timestamp(dt):
    """Return POSIX timestamp as float.

    This is essentially Python 3.3's datetime.timestamp() function. I've
    moved it here for Python 2 compatibility.

    """
    if dt.tzinfo is None:
        return time.mktime(
            (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, -1, -1, -1)
        ) + dt.microsecond / 1e6
    else:
        return (dt - EPOCH).total_seconds()
