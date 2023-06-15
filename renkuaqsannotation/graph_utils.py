import os
import rdflib
import json
import hashlib
import glob

from prettytable import PrettyTable
from nb2workflow import ontology

from renku.domain_model.project_context import project_context
from renku.command.graph import export_graph_command
from renku.core.errors import RenkuException
from renku.core.util.git import get_entity_from_revision

from renkuaqsannotation.oda_annotation import OdaAnnotation

# TODO improve this
__this_dir__ = os.path.join(os.path.abspath(os.path.dirname(__file__)))


def _renku_graph(revision=None, paths=None):
    # FIXME: use (revision) filter

    cmd_result = export_graph_command().working_directory(paths).build().execute()

    if cmd_result.status == cmd_result.FAILURE:
        raise RenkuException("fail to export the renku graph")
    graph = cmd_result.output.as_rdflib_graph()

    return graph


def inspect_oda_graph_inputs(revision, paths, input_notebook: str = None):
    if paths is None:
        paths = project_context.path

    graph = _renku_graph(revision, paths)

    query_select = "SELECT DISTINCT ?entityInput ?entityInputLocation ?entityInputChecksum"

    query_where = """WHERE {
                    ?entityInput a <http://www.w3.org/ns/prov#Entity> ;
                        <http://www.w3.org/ns/prov#atLocation> ?entityInputLocation ;
                        <https://swissdatasciencecenter.github.io/renku-ontology#checksum> ?entityInputChecksum .
            """

    if input_notebook is not None:
        query_where += f"""
        
                FILTER ( ?entityInputLocation = '{input_notebook}' ) .
        """

    query_where += """
            ?activity a ?activityType ;
                <http://www.w3.org/ns/prov#qualifiedUsage>/<http://www.w3.org/ns/prov#entity> ?entityInput .        
    }
    """

    query = f"""{query_select}
               {query_where}
            """

    r = graph.query(query)

    G = rdflib.Graph()

    output = PrettyTable()
    output.field_names = ["Entity ID", "Entity checksum", "Entity input location"]
    output.align["Entity ID"] = "l"
    output.align["Entity checksum"] = "l"
    output.align["Entity input location"] = "l"
    for row in r:
        entity_path = row.entityInputLocation
        entity_checksum = row.entityInputChecksum
        entity_id = row.entityInput
        output.add_row([
            entity_id,
            entity_checksum,
            entity_path
        ])
        entity_file_name, entity_file_extension = os.path.splitext(entity_path)
        if entity_file_extension == '.ipynb':
            print(f"\033[31mExtracting metadata from the input notebook: {entity_path}, id: {entity_id}\033[0m")
            # get checksum from the path
            repository = project_context.repository
            revision = repository.head.commit.hexsha
            entity_obj = get_entity_from_revision(repository=repository, path=entity_path, revision=revision, bypass_cache=True)
            print(f"\033[31mEntity object extracted from entity_path: {entity_obj.path}, checksum: {entity_obj.checksum}\033[0m")
            print(f"\033[31mEntity checksum from the graph: {entity_checksum}\033[0m")
            if str(entity_obj.checksum) == str(entity_checksum):
                # file present on disk based on the checksum equality
                rdf_nb = ontology.nb2rdf(entity_path)
                oda_annotation_obj = OdaAnnotation(entity_obj)
                G.parse(data=rdf_nb)
                rdf_jsonld_str = G.serialize(format="json-ld")
                rdf_jsonld = json.loads(rdf_jsonld_str)

                print(f"\033[32mlog_aqs_annotation\033[0m")

                annotation_folder_path = oda_annotation_obj.graphvis_metadata_path.joinpath(entity_file_name).joinpath(entity_checksum)
                if annotation_folder_path.exists():
                    # directory gets cleaned-up in order to avoid to generate duplicate jsonld files
                    # that can occur in case of new commits where input notebook is not affected
                    jsonld_files = glob.glob(str(annotation_folder_path.joinpath("*.jsonld")))
                    for j_f in jsonld_files:
                        os.remove(j_f)
                else:
                    annotation_folder_path.mkdir(parents=True)

                for nb2annotation in rdf_jsonld:
                    nb2annotation["http://odahub.io/ontology#entity_checksum"] = entity_checksum
                    print(f"found jsonLD annotation:\n", json.dumps(nb2annotation, sort_keys=True, indent=4))
                    nb2annotation_id_hash = hashlib.sha256(nb2annotation["@id"].encode()).hexdigest()[:8]

                    jsonld_path = os.path.join(annotation_folder_path, nb2annotation_id_hash + ".jsonld")
                    with open(jsonld_path, mode="w") as f:
                        print("writing", jsonld_path)
                        f.write(json.dumps(nb2annotation, sort_keys=True, indent=4))

    print(output, "\n")

