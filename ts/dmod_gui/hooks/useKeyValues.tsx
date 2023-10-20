import React, {ChangeEvent, MouseEventHandler, ReactElement, ReactNode, SyntheticEvent, useState} from "react";
import {
    Autocomplete,
    Button,
    IconButton,
    List,
    ListItem,
    MenuItem,
    Select,
    SelectChangeEvent,
    TextField
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import AddCircleIcon from "@mui/icons-material/AddCircle";
import {removeArrayIndex} from "../utils/arrays";
import {FieldSet, FieldSetOptions, LegendaryAction} from "../components/FieldSet";
import {BaseFieldHookProperties, FieldHook, HookInterface} from "../utils/types/Base";

type PossibleValue<Type> = Type|null;
type PossibleString = PossibleValue<string>;
type KeyValue = [string, PossibleValue<string>];
type KeyValueList = KeyValue[];
type KeyToPossibleOptions<Type> = Record<string, PossibleValue<Type>>
type KeyToOptions = KeyToPossibleOptions<string>;
type PossibleKeyToOptions = KeyToOptions|null;

export interface KeyValueProperties extends BaseFieldHookProperties<PossibleKeyToOptions> {
    keyNameAlias?: string;
    valueNameAlias?: string;
    keyTerms?: [];
    keyOptions?: [];
}

interface ExplicitKeyValueProperties extends BaseFieldHookProperties<PossibleKeyToOptions> {
    keyNameAlias: string;
    valueNameAlias: string;
    keyTerms?: [];
    keyOptions?: [];
}
function convertKeyValuePairs(initialValues?: PossibleKeyToOptions): KeyValueList {
    if (initialValues) {
        return Object.entries(initialValues).map(
            ([key, value]) => [key, value]
        );
    }
    else {
        return [];
    }
}

function fillKeyValuePropertiesDefaults(properties: KeyValueProperties): ExplicitKeyValueProperties {
    const defaultValueChangedFunction = () => {};
    
    return {
        id: properties.id,
        name: properties.name,
        applyChange: properties.applyChange ?? defaultValueChangedFunction,
        keyNameAlias: properties.keyNameAlias ?? "Key",
        valueNameAlias: properties.valueNameAlias ?? "Value",
        initialValue: properties.initialValue,
        keyTerms: properties.keyTerms,
        keyOptions: properties.keyOptions
    }
}


export const useKeyValues: FieldHook<PossibleKeyToOptions, KeyValueProperties> = (
    properties: KeyValueProperties
): HookInterface<PossibleKeyToOptions> => {
    const {
        id,
        name,
        initialValue,
        applyChange,
        keyNameAlias,
        valueNameAlias,
        keyTerms,
        keyOptions
    } = fillKeyValuePropertiesDefaults(properties);
    const cleanID = `${id.replace(" ", "-")}-${name.replace(" ", "_")}`;
    const [keyValues, setKeyValues] = useState<KeyValueList>(convertKeyValuePairs(initialValue));
    
    function hasBlank(): boolean {
        for (let [key, _] of keyValues) {
            if (key === null || key === undefined || key === '') {
                return true;
            }
        }
        return false;
    }
    
    function getDuplicateRows(): Record<string, number[]>|null {
        const encounteredValues: Record<string, number[]> = {};
        let duplicateRows: Record<string, number[]>|null = null;
        
        for (let keyValueIndex = 0; keyValueIndex < keyValues.length; keyValueIndex++) {
            const key = keyValues[keyValueIndex][0];
            
            if (Object.hasOwn(encounteredValues, key)) {
                encounteredValues[key].push(keyValueIndex);
            }
            else {
                encounteredValues[key] = [keyValueIndex];
            }
        }
        
        for (let [key, rows] of Object.entries(encounteredValues)) {
            if (rows.length > 1) {
                if (duplicateRows === null) {
                    duplicateRows = {};
                }
                
                duplicateRows[key] = rows;
            }
        }
        
        return duplicateRows;
    }
    
    function addRow() {
        let newKeyValues: KeyValueList = [...keyValues];
        newKeyValues.push(['', '']);
        setKeyValues(newKeyValues);
    }
    
    function removeItem(event: SyntheticEvent<HTMLButtonElement, MouseEvent>) {
        const rawRowIndex = event.currentTarget.dataset.entry;
        
        if (rawRowIndex) {
            const rowIndex = parseInt(rawRowIndex);
            const newKeyValues = removeArrayIndex(keyValues, rowIndex);
            setKeyValues(newKeyValues);
        }
    }
    
    function valueChanged(event: ChangeEvent<HTMLInputElement|HTMLTextAreaElement>) {
        const rawRowIndex = event.target.dataset.entry;
        const rawColumnIndex = event.target.dataset.index;
        if (rawRowIndex && rawColumnIndex) {
            const rowIndex = parseInt(rawRowIndex);
            const columnIndex = parseInt(rawColumnIndex);
            let newKeyValues: KeyValueList = {...keyValues};
            newKeyValues[rowIndex][columnIndex] = event.target.value;
            changeValues(newKeyValues);
        }
        else {
            console.log("Values changed but a row and column could not be found");
        }
    }
    
    function changeValues(newValues: KeyValueList) {
        setKeyValues(newValues);
        if (applyChange) {
            applyChange(getKeyValues())
        }
    }
    
    function updateValues(newValues: PossibleKeyToOptions) {
        setKeyValues(convertKeyValuePairs(newValues));
    }
    
    function keySelectChanged(event: SelectChangeEvent<HTMLInputElement>, child: ReactNode) {
        console.warn(
            "Trying to select a key - this is hard to navigate because we need to know what item that is " +
            "having a key changed on and that isn't immediately available on the element brought in on the " +
            "select changed event"
        )
    }
    
    function makeKeyField(cleanID: string, entryNumber: number, key: string): JSX.Element {
        let keyField: JSX.Element;
        
        if (keyTerms) {
            keyField = <Autocomplete
                renderInput={
                    (params) => {
                        return <TextField
                            {...params}
                            id={`${cleanID}-key-${entryNumber}`}
                            className={"KeyValueListItemTextKey"}
                            label={keyNameAlias}
                            inputProps={{
                                "data-key": key,
                                "data-index": 0,
                                "data-entry": entryNumber
                            }}
                            onChange={valueChanged}
                        >
                            {key}
                        </TextField>
                    }
                }
                options={keyTerms}/>
        } else if (keyOptions) {
            keyField = <Select
                id={`${cleanID}-key-${entryNumber}`}
                className={"KeyValueListItemSelectKey"}
                onChange={keySelectChanged}
                data-index={0}
                data-key={key}
            >
                {
                    keyOptions.map(
                        (option, optionNumber) => {
                            const optionID = `${cleanID}-key-${entryNumber}-option-${optionNumber}`;
                            return (
                                <React.Fragment key={optionID}>
                                    <MenuItem id={optionID} value={key}>{key}</MenuItem>
                                </React.Fragment>
                            );
                        }
                    )
                }
            </Select>
        }
        else {
            keyField = <TextField
                            id={`${cleanID}-key-${entryNumber}`}
                            className={"KeyValueListItemTextKey"}
                            label={keyNameAlias}
                            inputProps={{
                                "data-key": key,
                                "data-index": 0,
                                "data-entry": entryNumber
                            }}
                            onChange={(e) => valueChanged(e)}
                        >
                            {key}
                        </TextField>
        }
        
        return keyField;
    }
    
    function createKeyValueEntry(key: string, value: PossibleString, entryNumber: number): JSX.Element {
        console.log("Creating the markup for a value entry")
        const cleanKey = `${cleanID}-entry-${entryNumber}`;
        
        const deleteEntryMarkup = <IconButton edge={"end"} data-entry={entryNumber} onClick={removeItem}>
                                    <DeleteIcon data-entry={entryNumber} color={"error"}/>
                                </IconButton>
        return (
            <React.Fragment key={cleanKey}>
                <ListItem
                    className={"KeyValueListItem"}
                    secondaryAction={deleteEntryMarkup}
                    data-entry={entryNumber}
                >
                    {
                        makeKeyField(cleanKey, entryNumber, key)
                    }
                    <TextField
                        id={`${cleanKey}-value`}
                        className={"KeyValueListItemValue"}
                        label={valueNameAlias}
                        onChange={(e) => valueChanged(e)}
                        inputProps={{
                            "data-entry": entryNumber,
                            "data-index": 1
                        }}
                    >
                        {value ?? ''}
                    </TextField>
                </ListItem>
            </React.Fragment>
        );
    }
    
    function getMarkup(): JSX.Element {
        const legendaryActions: LegendaryAction[] = [
            {
                key: `${cleanID}-add-key-value`,
                action: addRow,
                buttonProperties: {},
                icon: <AddCircleIcon color={"primary"}/>,
                shouldShow: () => !hasBlank()
            }
        ]
        
        const fieldsetOptions: FieldSetOptions = {
            parentID: cleanID,
            name: name,
            actions: legendaryActions
        }
        
        return (
            <>
                <FieldSet {...fieldsetOptions}>
                    <List className={"KeyValueList"}>
                        {
                            keyValues.map(
                                ([key, value], entryNumber) => {
                                    return createKeyValueEntry(key, value, entryNumber)
                                }
                            )
                        }
                    </List>
                </FieldSet>
            </>
        );
    }
    
    function getKeyValues(): PossibleKeyToOptions {
        if (keyValues) {
            return Object.fromEntries(keyValues);
        }
        
        return null;
    }
    
    return {
        render: getMarkup,
        update: updateValues,
        get: getKeyValues,
        isPopulated: () => !hasBlank(),
        getKey: () => cleanID
    }
}

export default useKeyValues;