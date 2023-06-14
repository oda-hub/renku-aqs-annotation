# -*- coding: utf-8 -*-
#
# Copyright 2020 - Viktor Gal
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

import os
import json
import re
import subprocess
import webbrowser
import click
import rdflib
import rdflib.tools.rdf2dot

from pathlib import Path
from renku.domain_model.provenance.annotation import Annotation
from renku.domain_model.project_context import project_context
from renku.core.plugin import hookimpl
from aqsconverters.io import ODA_ANNOTATION_DIR, COMMON_DIR
from renkuodaannotation.config import ENTITY_METADATA_AQS_DIR
from nb2workflow import ontology

import renkuodaannotation.graph_utils as graph_utils


class OdaAnnotation(object):
    def __init__(self, run):
        self.run = run

    @property
    def renku_oda_annotation_path(self):
        """Return a ``Path`` instance of Renku oda annotation folder."""
        return Path(project_context.metadata_path).joinpath(ODA_ANNOTATION_DIR).joinpath(COMMON_DIR)

    @property
    def oda_metadata_path(self):
        """Return a ``Path`` instance of Renku oda metadata folder."""
        return Path(project_context.metadata_path).joinpath(ENTITY_METADATA_AQS_DIR)

    def load_model(self, path):
        """Load AQS reference file."""
        if path and path.exists():
            return json.load(path.open())
        return {}


@hookimpl
def activity_annotations(activity):
    """``process_run_annotations`` hook implementation."""
    oda_annotation = OdaAnnotation(activity)

    sitecustomize_path = Path(project_context.metadata_path, ODA_ANNOTATION_DIR, "sitecustomize.py")
    if sitecustomize_path.exists():
        sitecustomize_path.unlink()

    annotations = []

    print("process_run_annotations")
    print(oda_annotation.renku_oda_annotation_path)
    # apply nb2rdf also to input nb and also add the name of the notebook
    # should be related to the input/output notebook
    # add the annotations to the plan

    if activity.generations is not None and len(activity.generations) >= 1:
        for generation in activity.generations:
            entity = generation.entity
            if isinstance(entity, list):
                entity = generation.entity[0]
            entity_file_name, entity_file_extension = os.path.splitext(entity.path)
            if entity_file_extension == '.ipynb':
                print(f"\033[31mExtracting metadata from the output notebook: {entity.path}, id: {entity.id}\033[0m")
                rdf_nb = ontology.nb2rdf(entity.path)
                print(f"\033[32m{rdf_nb}\033[0m")
                G = rdflib.Graph()
                G.parse(data=rdf_nb)
                rdf_jsonld_str = G.serialize(format="json-ld")
                rdf_jsonld = json.loads(rdf_jsonld_str)
                for nb2annotation in rdf_jsonld:
                    # to comply with the terminology
                    nb2annotation["http://odahub.io/ontology#entity_checksum"] = entity.checksum
                    print(f"found jsonLD annotation:\n", json.dumps(nb2annotation, sort_keys=True, indent=4))
                    model_id = nb2annotation["@id"]
                    annotation_id = "{activity}/annotations/aqs/{id}".format(
                        activity=activity.id, id=model_id
                    )
                    annotations.append(
                        Annotation(id=annotation_id, source="AQS plugin", body=nb2annotation)
                    )

    if os.path.exists(oda_annotation.renku_oda_annotation_path):
        for p in oda_annotation.renku_oda_annotation_path.iterdir():
            if p.match("*json"):
                print(f"found json annotation: {p}")
                print(open(p).read())

            elif p.match("*jsonld"):
                aqs_annotation = oda_annotation.load_model(p)
                print(f"found jsonLD annotation: {p}\n", json.dumps(aqs_annotation, sort_keys=True, indent=4))

                # this will make annotations according to https://odahub.io/ontology/
                model_id = aqs_annotation["@id"]
                annotation_id = "{activity}/annotations/aqs/{id}".format(
                    activity=activity.id, id=model_id
                )
                p.unlink()
                annotations.append(
                    Annotation(id=annotation_id, source="AQS plugin", body=aqs_annotation)
                )
    else:
        print("nothing to process in process_run_annotations")

    return annotations


@hookimpl
def pre_run(tool):
    print(f"\033[31mhere we will prepare hooks for astroquery, tool given is {tool}\033[0m")

    sitecustomize_dir = Path(project_context.metadata_path).joinpath(ODA_ANNOTATION_DIR)

    if not sitecustomize_dir.exists():
        sitecustomize_dir.mkdir(parents=True)

    os.environ["PYTHONPATH"] = f"{sitecustomize_dir}:" + os.environ.get('PYTHONPATH', "")

    sitecustomize_path = os.path.join(sitecustomize_dir, "sitecustomize.py")

    print(f"\033[34msitecustomize.py as {sitecustomize_path}\033[0m")

    open(sitecustomize_path, "w").write("""
print(f"\033[31menabling hooks for astroquery\033[0m")  

import aqsconverters.aq

aqsconverters.aq.autolog()
""")


@click.group()
def oda():
    pass


@oda.command()
@click.option(
    "--revision",
    default="HEAD",
    help="The git revision to generate the log for, default: HEAD",
)
@click.option("--input-notebook", default=None, help="Input notebook to process")
@click.argument("paths", type=click.Path(exists=False), nargs=-1)
def inspect(revision, paths, input_notebook):
    """Inspect the input entities within the graph"""

    path = paths
    if paths is not None and isinstance(paths, click.Path):
        path = str(path)

    graph_utils.inspect_oda_graph_inputs(revision, path, input_notebook)

    return ""


@oda.command()
def start_session():
    gitlab_url = subprocess.check_output(["git", "remote", "get-url", "origin"]).decode().strip()

    new_session_urls = []

    for pattern in [
        'https://renkulab.io/gitlab/(.*)\.git',
        'git@renkulab.io:(.*)\.git'
    ]:
        if (r := re.match(pattern, gitlab_url)) is not None:
            new_session_urls.append(f"https://renkulab.io/projects/{r.group(1)}/sessions/new?autostart=1&branch=master")

    if (n := len(new_session_urls)) > 1:
        click.echo(f"using first of many session URLs: {new_session_urls}")
    elif n == 0:
        raise RuntimeError("unable to find any session URLs")

    click.echo(f"will open new session: {new_session_urls[0]}")

    webbrowser.open(new_session_urls[0])
