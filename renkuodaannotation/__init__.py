# -*- coding: utf-8 -*-
#
# Copyright 2020 - 
# A partnership between École Polytechnique Fédérale de Lausanne (EPFL) and
# Eidgenössische Technische Hochschule Zürich (ETHZ).
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

from __future__ import absolute_import, print_function

import logging
from . import config
from pip._vendor import pkg_resources
from renku.version import __version__


logging.basicConfig(level="DEBUG")


def _check_renku_version():
    """Check renku version."""

    _package = pkg_resources.working_set.by_key["renku"]
    required_version = _package.parsed_version.public

    if required_version != __version__:
        logging.info(f"You are using renku version {__version__}, however version {required_version} "
                     f"is required for the renku-aqs plugin.\n"
                     "You should consider install the suggested version.",)


_check_renku_version()
