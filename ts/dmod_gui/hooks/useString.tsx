import React, {ChangeEvent, ChangeEventHandler, ReactNode, SyntheticEvent, useState} from "react";
import {SelectChangeEvent, TextField} from "@mui/material";
import {BaseFieldHookProperties, FieldHook, StringHook, StringInterface} from "../utils/types/Base";
import {Option, StringCapable} from "./useOptions";

export const useString: StringHook<BaseFieldHookProperties<string>> = (
    properties: BaseFieldHookProperties<string>
): StringInterface => {
    const [value, setValue] = useState<string>(properties.initialValue ?? '');
    const cleanName = properties.name.replace(" ", "-");
    const inputID = `${properties.id}-${cleanName}`;
    
    function valueChanged(event: ChangeEvent<HTMLInputElement>) {
        updateValue(event.target.value);
    }
    
    function updateValue(newName: string) {
        setValue(newName);
        if (properties.applyChange) {
            properties.applyChange(value);
        }
    }
    
    function getMarkup() {
        return (
            <>
                <TextField
                    label={properties.name}
                    id={inputID}
                    className={properties.className ?? "TextHook"}
                    value={value}
                    style={properties.style ?? {}}
                    onChange={valueChanged}
                />
            </>
        );
    }
    
    function getValue() {
        if (value) {
            return value;
        }
        return null;
    }
    
    function isPopulated(): boolean {
        if (properties.required) {
            return value !== '' && value !== null;
        }
        return true;
    }
    
    return {
        render: getMarkup,
        update: updateValue,
        get: getValue,
        getText: getValue,
        getKey: () => inputID,
        isPopulated: isPopulated
    }
}

const textEventHandler: ChangeEventHandler = (event: ChangeEvent) => {};

export interface TextRenderOptions {
    id: string;
    key: string;
    name: string;
    index: number;
    valueChanged: (event: ChangeEvent<HTMLInputElement|HTMLTextAreaElement>) => any;
    currentValue?: string;
    isRequired?: boolean;
    defaultValue?: string;
    style?: Record<string, any>;
    className?: string;
}

export function renderText(properties: TextRenderOptions): JSX.Element {
    const inputID = properties.id.replace(" ", "-");
    return (
        <>
            <TextField
                label={properties.name}
                id={inputID}
                className={properties.className ?? "TextHook"}
                value={properties.currentValue}
                style={properties.style ?? {}}
                onChange={properties.valueChanged}
                inputProps={{"data-index": properties.index, "data-id": properties.id}}
            />
        </>
    );
}

export default useString;