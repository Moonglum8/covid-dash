from typing import Iterable, Dict, Union, List
from json import dumps
from requests import get
from http import HTTPStatus
import pandas as pd
import io

StructureType = Dict[str, Union[dict, str]]
FiltersType = Iterable[str]
APIResponseType = Union[List[StructureType], str]


def get_paginated_dataset(filters: FiltersType, structure: StructureType,
                          as_csv: bool = False) -> APIResponseType:
    """
    Extracts paginated data by requesting all of the pages
    and combining the results.

    Parameters
    ----------
    filters: Iterable[str]
        API filters. See the API documentations for additional
        information.

    structure: Dict[str, Union[dict, str]]
        Structure parameter. See the API documentations for
        additional information.

    as_csv: bool
        Return the data as CSV. [default: ``False``]

    Returns
    -------
    Union[List[StructureType], str]
        Comprehensive list of dictionaries containing all the data for
        the given ``filters`` and ``structure``.
    """
    endpoint = "https://api.coronavirus.data.gov.uk/v1/data"

    api_params = {
        "filters": str.join(";", filters),
        "structure": dumps(structure, separators=(",", ":")),
        "format": "json" if not as_csv else "csv"
    }

    data = list()

    page_number = 1

    while True:
        # Adding page number to query params
        api_params["page"] = page_number

        response = get(endpoint, params=api_params, timeout=10)

        if response.status_code >= HTTPStatus.BAD_REQUEST:
            raise RuntimeError(f'Request failed: {response.text}')
        elif response.status_code == HTTPStatus.NO_CONTENT:
            break

        if as_csv:
            csv_content = response.content.decode()

            # Removing CSV header (column names) where page
            # number is greater than 1.
            if page_number > 1:
                data_lines = csv_content.split("\n")[1:]
                csv_content = str.join("\n", data_lines)

            data.append(csv_content.strip())
            page_number += 1
            continue

        current_data = response.json()
        page_data: List[StructureType] = current_data['data']

        data.extend(page_data)

        # The "next" attribute in "pagination" will be `None`
        # when we reach the end.
        if current_data["pagination"]["next"] is None:
            break

        page_number += 1

    if not as_csv:
        return data

    # Concatenating CSV pages
    return str.join("\n", data)


if __name__ == "__main__":
    query_filters = [
        f"areaType=region"
    ]

    query_structure_cases = {
        "date": "date",
        "name": "areaName",
        "code": "areaCode",
        "daily": "newCasesBySpecimenDate",
        "cumulative": "cumCasesBySpecimenDate"
    }

    query_structure_deaths = {
        "date": "date",
        "name": "areaName",
        "code": "areaCode",
        "daily": "newDeaths28DaysByDeathDate",
        "cumulative": "cumDeaths28DaysByDeathDate"
    }


    csv_data = get_paginated_dataset(query_filters, query_structure_cases, as_csv=True)
    csv_lines = csv_data.split("\n")
    df_cases = pd.read_csv(io.StringIO(csv_data), index_col='date', parse_dates=True)

    print(df_cases)

    csv_data = get_paginated_dataset(query_filters, query_structure_deaths, as_csv=True)
    csv_lines = csv_data.split("\n")
    df_deaths = pd.read_csv(io.StringIO(csv_data), index_col='date', parse_dates=True)

    print(df_deaths)
