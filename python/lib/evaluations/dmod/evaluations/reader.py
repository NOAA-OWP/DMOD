#!/usr/bin/env python3
import typing

import pandas
import jsonpath_ng as jsonpath


from . import specification


def select_values(document: dict, selector: specification.ValueSelector):
    origin_expression: jsonpath.This = jsonpath.parse(".".join(selector.origin))
    tables: typing.List[pandas.DataFrame] = []

    for element in origin_expression.find(document):
        full_path = str(element.full_path)

        main_path = full_path + "." + ".".join(selector.path)
        value_expression: jsonpath.This = jsonpath.parse(main_path)

        value_results = value_expression.find(document)

        if not value_results:
            continue

        columns = {}

        if len(value_results) == 1:
            if selector.where == "key":
                columns[selector.name] = selector.to_datatype(value_results[0].path)
            else:
                columns[selector.name] = selector.to_datatype(value_results[0].value)
        else:
            if selector.where == "key":
                columns[selector.name] = [
                    selector.to_datatype(result.path)
                    for result in value_results
                ]
            else:
                columns[selector.name] = [
                    selector.to_datatype(result.value)
                    for result in value_results
                ]

        for index in selector.associated_fields:
            if selector.where.lower() == "key":
                column_data = list()
                missing_entries = 0

                for result in value_results:
                    index_path = f"{str(result.full_path)}.{'.'.join(index.path)}"
                    index_expression = jsonpath.parse(index_path)
                    index_results = index_expression.find(document)

                    if not index_results:
                        missing_entries += 1
                        column_data.append(None)
                    else:
                        column_data.append(index.to_datatype(index_results[0].value))

                if len(column_data) == 0 or len(column_data) == missing_entries:
                    raise KeyError(
                            f"There are no values for the index named '{index.name}' at "
                            f"'{full_path + '.*.' + '.'.join(index.path)}'"
                    )

                if len(column_data) == 1:
                    columns[index.name] = column_data[0]
                else:
                    columns[index.name] = column_data
            else:
                index_path = full_path + "." + ".".join(index.path)

                index_expression: jsonpath.This = jsonpath.parse(index_path)
                index_results = index_expression.find(document)

                if not index_results:
                    raise KeyError(f"There are no values for the index named '{index.name}' at '{index_path}'")

                if len(index_results) == 1:
                    # We're dealing with a scalar
                    columns[index.name] = index.to_datatype(index_results[0].value)
                else:
                    # we're dealing with a vector
                    columns[index.name] = [
                        index.to_datatype(result.value)
                        for result in index_results
                    ]

        tables.append(pandas.DataFrame(data=columns))

    if len(tables) == 1:
        return tables[0]
    elif tables:
        table = pandas.concat(tables, ignore_index=True)
        return table

    return None
