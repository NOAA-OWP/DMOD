import React from "react";
import {
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow
} from "@mui/material";

/**
 * Represents more detailed information than just the name of the column
 */
export interface HeaderCellDetails {
    columnName: string,
    styles?: Record<string, any>
}

/**
 * Defines a type of function that takes
 */
export type RowFunction<Type> = (
    id: string,
    entry: Type,
    index: string | number,
    data: Type[] | Record<string, Type>
) => JSX.Element;

export type IRFunction<Type, Collection> = (id: string, entry: Type, index: string | number, data: Collection) => JSX.Element;

export type IndexedRowFunction<Type> = (id: string, entry: Type, index: string | number, data: Record<string, Type>) => JSX.Element;
export type ArrayRowFunction<Type> = (id: string, entry: Type, index: number, data: Type[]) => JSX.Element;

export type RFunction<Type> =
    | IRFunction<Type, Record<string, Type>>
    | IRFunction<Type, Type[]>

/**
 * Defines the necessary values to consider an object a set of 'GenericTableProperties'
 */
export interface GenericTableProperties<Type, Collection> {
    id: string,
    columnNames: (string | HeaderCellDetails)[],
    data: Collection,
    rowFunction: RowFunction<Type>
}

export interface IGTableProperties<Type, Collection> {
    id: string,
    columnNames: (string | HeaderCellDetails)[],
    data: Collection,
    rowFunction: RFunction<Type>
}

export interface IndexedTableProperties<Type> {
    id: string,
    columnNames: (string | HeaderCellDetails)[],
    data: Record<string, Type>,
    rowFunction: IndexedRowFunction<Type>
}

export interface ArrayTableProperties<Type> {
    id: string,
    columnNames: (string | HeaderCellDetails)[],
    data: Type[],
    rowFunction: ArrayRowFunction<Type>
}

export type GTableProperties<Type> =
    | IndexedTableProperties<Type>
    | ArrayTableProperties<Type>

export type GDataTableType<Type> =
    | Type[]
    | Record<string, Type>;

export type OGTableProperties<Type> =
    | IGTableProperties<Type, Record<string, Type>>
    | IGTableProperties<Type, Type[]>

function interpretTextColumnName(id: string, column: string): JSX.Element {
    const cleanedColumnName = column.replace(" ", "-");
    return (
        <TableCell key={`${cleanedColumnName}-header`} id={`${id}-${cleanedColumnName}-header`}>
            {column}
        </TableCell>
    )
}

function interpretHeaderCellColumnName(id: string, column: HeaderCellDetails): JSX.Element {
    const styles = column.styles || {};
    let name = column.columnName || '';
    
    const cleanedColumnName = name.replace(" ", "-");
    
    return (
        <TableCell
            key={`${id}-${cleanedColumnName}-header`}
            id={`${id}-${cleanedColumnName}-header`}
            style={styles}
        >
            {name}
        </TableCell>
    );
}


function interpretColumnNames(id: string, columnNames: (string | HeaderCellDetails)[]): JSX.Element[] {
    return columnNames.map((column) => {
        if (typeof column === 'string') {
            return interpretTextColumnName(id, column);
        }
        else {
            return interpretHeaderCellColumnName(id, column);
        }
    });
}

function interpretArrayRow<Type>(
    id: string,
    entry: Type,
    rowNumber: number,
    data: Type[],
    rowFunction: RowFunction<Type>
): JSX.Element {
    return (
        <>
            {
                rowFunction(id, entry, rowNumber, data)
            }
        </>
    );
}

function interpretIndexedRow<Type>(
    id: string,
    entry: Type,
    rowNumber: number,
    key: string | number,
    data: Record<string, Type>,
    rowFunction: RowFunction<Type>
): JSX.Element {
    return (
        <>
            {
                rowFunction(id, entry, key, data)
            }
        </>
    );
}

function interpretIndexedRows<Type>(
    id: string,
    data: Record<string, Type>,
    rowFunction: IndexedRowFunction<Type>
): JSX.Element[] {
    return Object.entries(data).map(
        ([key, entry], rowNumber) => {
            return rowFunction(id, entry, key, data)
        }
    );
}

function interpretArrayRows<Type>(
    id: string,
    data: Type[],
    rowFunction: ArrayRowFunction<Type>
): JSX.Element[] {
    return data.map(
        (entry, rowNumber) => {
            return rowFunction(id, entry, rowNumber, data)
        }
    )
}

function interpretRows<Type>(
    id: string,
    data: Type[] | Record<string, Type>,
    rowFunction: RowFunction<Type>
): JSX.Element[] {
    if (Array.isArray(data)) {
        return data.map(
            (entry, rowNumber) => {
                return interpretArrayRow(id, entry, rowNumber, data, rowFunction)
            }
        )
    }
    else {
        return Object.entries(data).map(
            ([key, entry], rowNumber) => {
                return interpretIndexedRow(id, entry, rowNumber, key, data, rowFunction)
            }
        );
    }
}

function interpretGRows<Type, Collection> (
    id: string,
    data: Collection,
    rowFunction: IRFunction<Type, Collection>
): JSX.Element[] {
    if (Array.isArray(data)) {
        return data.map(
            (entry, rowNumber) => {
                return (
                    <React.Fragment key={`${id}-row-${rowNumber}`}>
                        {
                            rowFunction(id, entry, rowNumber, data)
                        }
                    </React.Fragment>
                )
            }
        )
    }
    else if (typeof data === 'object' && data) {
        return Object.entries(data).map(
            ([key, entry], rowNumber) => {
                return (
                    <React.Fragment key={`${id}-row-${rowNumber}`}>
                        {
                            rowFunction(id, entry, key, data)
                        }
                    </React.Fragment>
                )
            }
        );
    }
    return [];
}


export function GenericTable<Type, Collection extends Record<string, Type> | Type[]>(
    {
        id,
        columnNames,
        data,
        rowFunction
    }: GenericTableProperties<Type, Collection>
): JSX.Element {
    const columnCells: JSX.Element[] = interpretColumnNames(id, columnNames);
    const rows: JSX.Element[] = interpretRows(id, data, rowFunction);
    return makeTable(id, columnCells, rows);
}

function makeTable(id: string, columnCells: JSX.Element[], rows: JSX.Element[]): JSX.Element {
    return (
        <TableContainer>
            <Table id={id} className="generic-table">
                <TableHead className="generic-table-header">
                    <TableRow id={`${id}-header-row`} className="generic-table-header-row">
                        {columnCells}
                    </TableRow>
                </TableHead>
                <TableBody>
                    {rows}
                </TableBody>
            </Table>
        </TableContainer>
    );
}

export function GenericIndexedTable<Type>(
    {
        id,
        columnNames,
        data,
        rowFunction
    }: IndexedTableProperties<Type>
): JSX.Element {
    const columnCells: JSX.Element[] = interpretColumnNames(id, columnNames);
    const rows: JSX.Element[] = interpretIndexedRows(id, data, rowFunction);
    return makeTable(id, columnCells, rows)
}

export function GenericArrayTable<Type>(
    {
        id,
        columnNames,
        data,
        rowFunction
    }: ArrayTableProperties<Type>
): JSX.Element {
    const columnCells: JSX.Element[] = interpretColumnNames(id, columnNames);
    const rows: JSX.Element[] = interpretArrayRows(id, data, rowFunction);
    return makeTable(id, columnCells, rows)
}