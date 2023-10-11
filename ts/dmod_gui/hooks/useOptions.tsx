import React, {ChangeEvent, ReactNode, ReactPortal, useState} from "react";
import {
    Autocomplete,
    AutocompleteRenderInputParams, FormControl, InputLabel,
    MenuItem, OutlinedInput,
    SelectChangeEvent,
    TextField
} from "@mui/material";
import Select from "@mui/material/Select"
import {BaseFieldHookProperties, FieldHook, HookInterface, StringHook, StringInterface} from "../utils/types/Base";
import {insertIntoArray} from "../utils/arrays";

export interface CanBeString {
    toString: () => string;
}

export type StringCapable = CanBeString | string;

export type Option<ValueType extends StringCapable> = [string, ValueType];

export interface OptionHookProperties<ValueType extends StringCapable> extends BaseFieldHookProperties<ValueType> {
    options: Option<ValueType>[];
    defaultValue?: ValueType;
    allowCustomInput?: boolean;
}

export interface OptionHookInterface<ValueType extends StringCapable> extends HookInterface<ValueType> {
    getText: () => string|null;
}

export interface ComboSuggestion<ValueType> {
    label: string;
    value: ValueType;
}

export interface SelectRenderOptions<ValueType extends StringCapable> {
    id: string;
    key: string;
    name: string;
    index: number;
    options: Option<ValueType>[];
    selectValueChanged: (event: SelectChangeEvent, child: ReactNode) => any;
    currentValue?: ValueType;
    isRequired?: boolean;
    defaultValue?: ValueType;
    style?: Record<string, any>;
    className?: string;
}

export function renderSelect<ValueType extends StringCapable = string>(
    properties: SelectRenderOptions<ValueType>
): JSX.Element {
    const inputID = properties.id.replace(" ", "-");
    
    function makeValueAssignable(candidate: ValueType|null): string|undefined {
        let valueToAssign: string|undefined;
        if (typeof candidate === 'string') {
            valueToAssign = candidate;
        }
        else if (candidate === null) {
            valueToAssign = undefined;
        }
        else {
            valueToAssign = candidate.toString();
        }
        return valueToAssign;
    }
    
    let options: JSX.Element[] = properties.options.map(
            ([optionText, optionValue], optionNumber) => {
                const optionID = `${inputID}-option-${optionNumber}`;
                return (
                    <MenuItem id={optionID} value={makeValueAssignable(optionValue)} key={optionID}>
                        {optionText}
                    </MenuItem>
                );
            }
        );
        
        const labelId = `${inputID}-label`
        
        if (!properties.defaultValue) {
            options = insertIntoArray(
                options,
                <MenuItem value=''><em>None</em></MenuItem>
            )
        }
        
        return (
            <FormControl
                style={properties.style ?? {}}
                className={properties.className ?? "DMODSelectHook"}
                required
                sx={{ verticalAlign: "middle", minWidth: 120 }}
            >
                <InputLabel shrink={true} id={labelId}>{properties.name}</InputLabel>
                <Select
                    id={inputID}
                    labelId={labelId}
                    label={properties.name}
                    onChange={properties.selectValueChanged}
                    value={makeValueAssignable(properties.currentValue || properties.defaultValue || null)}
                    displayEmpty={true}
                    autoWidth={true}
                    required={true}
                    placeholder={properties.name}
                    data-index={properties.index}
                    inputProps={{"data-index": properties.index, "data-id": properties.id}}
                >
                    {options}
                </Select>
            </FormControl>
        );
}

export function useOptions<ValueType extends StringCapable>(
    properties: OptionHookProperties<ValueType>
): OptionHookInterface<ValueType> {
    const [value, setValue] = useState<ValueType|null>(() => {
        if (properties.initialValue) {
            return properties.initialValue;
        }
        else if (properties.defaultValue) {
            return properties.defaultValue;
        }
        return null;
    });
    
    const cleanName = properties.name.replace(" ", "-");
    const inputID = `${properties.id}-${cleanName}`;
    
    function findValue(selectedValue: string): ValueType|null {
        for (const [_, optionValue] of properties.options) {
            if(typeof optionValue === 'string') {
                if (optionValue === selectedValue) {
                    return optionValue;
                }
            }
            else {
                if (optionValue.toString() === selectedValue) {
                    return optionValue;
                }
            }
        }
        return null;
    }
    
    function comboValueChanged(event: ChangeEvent<HTMLInputElement|HTMLTextAreaElement>) {
        const selectedValue: string = event.target.value;
        const foundValue: ValueType|null = findValue(selectedValue);
        
        if (foundValue !== null && foundValue !== value) {
            updateValue(foundValue);
        }
    }
    
    function selectValueChanged(event: SelectChangeEvent, child: ReactNode) {
        const selectedValue: string = event.target.value;
        const foundValue: ValueType|null = findValue(selectedValue);
        
        if (foundValue !== null && foundValue !== value) {
            updateValue(foundValue);
        }
    }
    
    function updateValue(newValue: ValueType) {
        setValue(newValue);
        if (properties.applyChange) {
            properties.applyChange(value);
        }
    }
    
    function getComboBoxMarkup(): JSX.Element {
        const suggestions: ComboSuggestion<ValueType>[] = properties.options.map(
            ([key, value]): ComboSuggestion<ValueType> => {
                return {"label": key, "value": value}
            }
        );
        
        const comboFactory: (params: AutocompleteRenderInputParams) => JSX.Element = (params) => {
            return <TextField
                {...params}
                className={properties.className ?? 'DMODComboHook'}
                label={properties.name}
                style={properties.style ?? {}}
                id={inputID}
                onChange={comboValueChanged}
                value={value}
            >
                {makeValueAssignable(value)}
            </TextField>
        }
        
        return (
            <Autocomplete renderInput={comboFactory} options={suggestions}/>
        );
    }
    
    function makeValueAssignable(candidate: ValueType|null): string|undefined {
        let valueToAssign: string|undefined;
        if (typeof candidate === 'string') {
            valueToAssign = candidate;
        }
        else if (candidate === null) {
            valueToAssign = undefined;
        }
        else {
            valueToAssign = candidate.toString();
        }
        return valueToAssign;
    }
    
    function getSelectMarkup(): JSX.Element {
        let options: JSX.Element[] = properties.options.map(
            ([optionText, optionValue], optionNumber) => {
                const optionID = `${inputID}-option-${optionNumber}`;
                return (
                    <MenuItem id={optionID} value={makeValueAssignable(optionValue)} key={optionID}>
                        {optionText}
                    </MenuItem>
                );
            }
        );
        
        const labelId = `${inputID}-label`
        
        if (!properties.defaultValue) {
            options = insertIntoArray(
                options,
                <MenuItem value=''><em>None</em></MenuItem>
            )
        }
        
        return (
            <FormControl
                style={properties.style ?? {}}
                className={properties.className ?? "DMODSelectHook"}
                required
                sx={{ verticalAlign: "middle", minWidth: 120 }}
            >
                <InputLabel shrink={true} id={labelId}>{properties.name}</InputLabel>
                <Select
                    id={inputID}
                    labelId={labelId}
                    label={properties.name}
                    onChange={selectValueChanged}
                    value={makeValueAssignable(value)}
                    displayEmpty={true}
                    autoWidth={true}
                    required={true}
                    placeholder={properties.name}
                >
                    {options}
                </Select>
            </FormControl>
        );
    }
    
    function getMarkup(): JSX.Element {
        return properties.allowCustomInput ? getComboBoxMarkup() : getSelectMarkup();
    }
    
    function getValue() {
        for (const [_, optionValue] of properties.options) {
            if(optionValue == value) {
                return optionValue;
            }
        }
        return null;
    }
    
    function getText(): string|null {
        for (let [optionText, optionValue] of properties.options) {
            if (optionValue == value) {
                return optionText;
            }
        }
        
        return null;
    }
    
    return {
        render: getMarkup,
        update: updateValue,
        get: getValue,
        getText: getText,
        getKey: () => inputID,
        isPopulated: () => getValue() !== null
    }
}

export default useOptions;