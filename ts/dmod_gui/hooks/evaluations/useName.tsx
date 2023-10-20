import {ChangeEvent, useState} from "react";
import {TextField} from "@mui/material";
import {BaseFieldHookProperties, FieldHook, HookInterface} from "../../utils/types/Base";


export const useName: FieldHook<string, BaseFieldHookProperties<string>> = (
    properties: BaseFieldHookProperties<string>
): HookInterface<string> => {
    const [name, setName] = useState<string>(properties.initialValue ?? '');
    const inputID = `${properties.id}-name`;
    
    function nameChanged(event: ChangeEvent<HTMLInputElement>) {
        updateName(event.target.value);
    }
    
    function updateName(newName: string) {
        setName(newName);
        if (properties.applyChange) {
            properties.applyChange(name);
        }
    }
    
    function getMarkup() {
        return (
            <>
                <TextField
                    label={properties.name ?? 'Name'}
                    id={inputID}
                    className={"name"}
                    value={name}
                    onChange={nameChanged}
                />
            </>
        );
    }
    
    function getName() {
        if (name) {
            return name;
        }
        return null;
    }
    
    return {
        render: getMarkup,
        update: updateName,
        get: getName
    }
}

export default useName;