import {BaseFieldHookProperties, BaseHookContainerProperties, HookInterface, RenderFunction} from "../utils/types/Base";
import React, {ReactNode, SyntheticEvent, useState} from "react";
import FieldSet, {FieldSetOptions, LegendaryAction} from "../components/FieldSet";
import AddCircleIcon from "@mui/icons-material/AddCircle";
import {ExtendButtonBase, IconButton, IconButtonTypeMap, List, ListItem} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import {removeArrayIndex} from "../utils/arrays";


export type RenderEntryFunction<ValueType> = (
    id: string,
    index: number,
    onChange: (id: string, index: number, value: ValueType) => any,
    currentValue: ValueType
) => JSX.Element;

export interface VariableFieldHookProperties<
    ValueType,
    InnerPropertyType extends BaseFieldHookProperties<ValueType> = BaseFieldHookProperties<ValueType>,
    InterfaceType extends HookInterface<ValueType> = HookInterface<ValueType>
> {
    id: string;
    name: string;
    render: RenderEntryFunction<ValueType>;
    createEntry: (baseProperties: InnerPropertyType) => ValueType;
    innerProperties: InnerPropertyType;
    values: ValueType[];
    setValues: (values: ValueType[]) => any;
    instance?: number;
    canAdd: (values: ValueType[]) => boolean;
}


export function useVariableComponents<
    ValueType,
    InnerPropertyType extends BaseFieldHookProperties<ValueType> = BaseFieldHookProperties<ValueType>
>(
    properties: VariableFieldHookProperties<ValueType, InnerPropertyType>
): HookInterface<ValueType[]> {
    function getCleanID(): string {
        return `${properties.id.replace(" ", "-")}-${properties.name.replace(" ", "-")}`;
    }
    
    function updateValues(id: string, index: number, value: ValueType) {
        const newValues = [...properties.values];
        
        newValues[index] = {...value}
        
        properties.setValues(newValues);
    }
    
    function getInnerProperties(entryInstance?: number, newValue?: ValueType): InnerPropertyType {
        const newProperties = {...properties.innerProperties};
        
        newProperties.instance = entryInstance;
        
        let cleanInnerID = null;
        
        if (properties.innerProperties.id) {
            cleanInnerID = properties.innerProperties.id.replace(" ", "-");
        }
        
        const formattedInnerID = cleanInnerID ? `-${cleanInnerID}` : '';
        newProperties.id = `${getCleanID()}${formattedInnerID}-${newProperties.instance}`
        
        if (newValue) {
            newProperties.initialValue = newValue;
        }
        
        return newProperties;
    }
    
    function getMarkup(): JSX.Element {
        const legendaryActions: LegendaryAction[] = [
            {
                key: `${getCleanID()}-add-field`,
                action: addEntry,
                buttonProperties: {},
                icon: <AddCircleIcon color={"primary"}/>,
                shouldShow: () => isPopulated()
            }
        ]
        
        const fieldSetOptions: FieldSetOptions = {
            parentID: getCleanID(),
            name: properties.name,
            actions: legendaryActions
        }
        
        const renderedEntries: JSX.Element[] = []
        
        for (let entryIndex = 0; entryIndex < properties.values.length; entryIndex++) {
            if (entryIndex > 0) {
                renderedEntries.push(<br key={`${getCleanID()}-break-${entryIndex}`}/>);
            }
            
            const renderedEntry = properties.render(getCleanID(), entryIndex, updateValues, properties.values[entryIndex]);
            const deleteEntryMarkup = <IconButton edge={"end"} data-index={entryIndex} onClick={removeEntry}>
                            <DeleteIcon data-index={entryIndex} color={"error"}/>
                        </IconButton>
            
            const listItem = <ListItem
                                    key={`${getCleanID()}-${entryIndex}`}
                                    secondaryAction={deleteEntryMarkup}
                                    data-index={entryIndex}
                                >
                                {renderedEntry}
                            </ListItem>
            
            renderedEntries.push(listItem);
        }
        
        return (
            <>
                <FieldSet {...fieldSetOptions}>
                    <List>
                        {
                            renderedEntries
                        }
                    </List>
                </FieldSet>
            </>
        );
    }
    
    function addEntry(event: SyntheticEvent<HTMLButtonElement, MouseEvent>) {
        if (properties.canAdd(properties.values)) {
            const newElements = [...properties.values];
            newElements.push(properties.createEntry(getInnerProperties()))
            properties.setValues(newElements);
        }
        else {
            console.warn(
                `A new entry will not be created within "${getCleanID()}" -
                there is already an entry that needs to be completed`
            )
        }
    }
    
    function removeEntry(event: SyntheticEvent<HTMLButtonElement, MouseEvent>) {
        const entryIndex = parseInt(event.currentTarget.dataset?.index ?? '-1')
        
        if (entryIndex < 0) {
            return;
        }
        
        const updatedValues = removeArrayIndex(properties.values, entryIndex);
        properties.setValues(updatedValues);
    }
    
    function update(newValues: ValueType[]) {
        properties.setValues(newValues);
    }
    
    function isPopulated(): boolean {
        return true;
    }
    
    return {
        render: getMarkup,
        get: () => properties.values,
        update: update,
        getKey: () => getCleanID(),
        isPopulated: isPopulated
    }
}