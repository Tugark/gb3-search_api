from dtos.search_result import SearchResult
from dtos.match import Match
from dtos.meta_match import MetaMatch
from geojson import GeoJSON
from fastapi.types import Callable
from elastic_transport import ObjectApiResponse


def prepare_search_result_for_gb3(index: str, search_result: ObjectApiResponse) -> SearchResult:
    if index == "fme-addresses":
        return get_results(index, search_result, lambda hit_source: f"{hit_source['street']} {hit_source['no']}, "
                                                                    f"{hit_source['plz']} {hit_source['town']}")
    if index == "fme-places":
        return get_results(index, search_result, lambda hit_source: f"{hit_source['type']} {hit_source['name']}")

    if "meta" in index:
        return get_meta_results(index, search_result)

    return get_results(index, search_result, lambda hit_source: get_special_search_display(hit_source))


def get_results(index: str, search_result: ObjectApiResponse,
                display_string_factory: Callable[dict, str]) -> SearchResult:
    matches = []
    hits = search_result["hits"]["hits"]
    for hit in hits:
        hit_source = hit["_source"]
        print(hit_source)
        matches.append(
            Match(
                displayString=display_string_factory(hit_source),
                score=hit["_score"],
                geometry=get_geometry(hit_source)
            )
        )

    return SearchResult(
        index=index,
        matches=matches
    )

def get_meta_results(index: str, search_result: ObjectApiResponse) -> SearchResult:
    matches = []
    hits = search_result["hits"]["hits"]
    for hit in hits:
        hit_source = hit["_source"]
        if "geodatensatz" in index:
            id = hit_source["giszhnr"]
        elif "gb2karten" in index:
            id = hit_source["gb2_id"]
        elif "product" in index:
            id = hit_source["gdpnummer"]
        elif "service" in index:
            id = hit_source["gdsernummer"]
        else:
            id = None

        matches.append(
            MetaMatch(
                id=str(id),
                score=hit["_score"]
            )
        )

    return SearchResult(
        index=index,
        matches=matches
    )


def get_geometry(hit_source: dict) -> GeoJSON | None:
    if hit_source.get("geometry"):
        return modify_geojson_geometry(hit_source.get("geometry"))

    return None

def modify_geojson_geometry(input_geometry: GeoJSON) -> GeoJSON:
    print(input_geometry)
    if input_geometry['type'] == 'MultiPoint' and len(input_geometry['coordinates']) == 1:
        return GeoJSON({
            "type": 'Point',
            "coordinates": input_geometry['coordinates'][0]
        })
    if input_geometry['type'] == 'MultiLineString' and len(input_geometry['coordinates']) == 1:
        return GeoJSON({
            "type": 'LineString',
            "coordinates": input_geometry['coordinates'][0]
        })
    if input_geometry['type'] == 'MultiPolygon' and len(input_geometry['coordinates']) == 1:
        return GeoJSON({
            "type": 'Polygon',
            "coordinates": input_geometry['coordinates'][0]
        })

    return input_geometry

def get_special_search_display(hit_source: dict) -> str:
    values = []
    fields = [e for e in hit_source.keys() if e != 'geometry']
    for field in fields:
        value = hit_source[field]
        if value is not None:
            values.append(get_display_string(value))

    return " ".join(values)


def get_display_string(value) -> str:
    if isinstance(value, float):
        return f'{value:g}'

    return str(value)
