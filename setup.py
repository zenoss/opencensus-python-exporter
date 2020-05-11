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

from setuptools import find_packages, setup

setup(
    name="opencensus-ext-zenoss",
    version="0.0.2",
    author="Zenoss, Inc.",
    author_email="dev@zenoss.com",
    classifiers=[
        "Intended Audience :: Developers",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
    ],
    description="OpenCensus Zenoss Exporter",
    include_package_data=True,
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    python_requires=">=2.7",
    install_requires=[
        "google-cloud-monitoring >= 0.30.0, < 1.0.0",
        "opencensus >= 0.7, < 1.0.0",
        "requests",
        "urllib3",
    ],
    extras_require={},
    license="Apache-2.0",
    packages=find_packages(exclude=("examples", "tests",)),
    namespace_packages=[],
    url='https://github.com/zenoss/opencensus-python-exporter',
    zip_safe=False,
)
