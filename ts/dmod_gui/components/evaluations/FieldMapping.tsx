import React, {ChangeEvent, ReactNode} from "react";
import {renderText} from "../../hooks/useString";
import {Option, renderSelect} from "../../hooks/useOptions";
import {FieldMappingSpecification} from "../../lib/evaluation/Specification";
import {SelectChangeEvent} from "@mui/material";

export function FieldMapping(
    mappingID: string,
    index: number,
    mappingChanged: (id: string, index: number, mapping: FieldMappingSpecification) => any,
    specification: FieldMappingSpecification
): JSX.Element {
    const style = {
        marginLeft: "10px",
        marginRight: "10px"
    }
    function getFieldMappingArticle(): "a"|"an" {
        const selectedMapType = specification.mapType;
        
        if (!selectedMapType) {
            return "a";
        }
        
        let selectedText: string|null = null;
        
        for (let [optionText, optionValue] of mapTypeOptions) {
            if (optionValue === selectedMapType) {
                selectedText = optionText;
                break;
            }
        }
        
        if (!selectedText) {
            return "a";
        }
        
        const firstCharacter = selectedText[0].toLowerCase();
        
        if ('aeiou'.includes(firstCharacter)) {
            return 'an';
        }
        
        return 'a';
    }
    
    const mapTypeOptions: Option<string>[] = [
            ["Object Key", "key"],
            ["Object Value", "value"],
            ["Column", "column"]
        ]
    
    function originalFieldChanged(event: ChangeEvent<HTMLInputElement|HTMLTextAreaElement>) {
        const newMapping: FieldMappingSpecification = {
            field: event.target.value
        };
        
        if (specification.mapType) {
            newMapping.mapType = specification.mapType;
        }
        
        if (specification.value) {
            newMapping.value = specification.value;
        }
        
        mappingChanged(mappingID, index, newMapping);
    }
    
    function mapTypeChanged(event: SelectChangeEvent) {
        const newMapping: FieldMappingSpecification = {};
        
        if (specification.field) {
            newMapping.field = specification.field;
        }
        
        const updatedMapType = event.target.value;
        
        for (const [_, value] of mapTypeOptions) {
            if (value === updatedMapType) {
                newMapping.mapType = value;
                break;
            }
        }
        
        if (specification.value) {
            newMapping.value = specification.value;
        }
        
        mappingChanged(mappingID, index, newMapping)
    }
    
    function newFieldChanged(event: ChangeEvent<HTMLInputElement|HTMLTextAreaElement>) {
        const newMapping: FieldMappingSpecification = {};
        
        if (specification.field) {
            newMapping.field = specification.field;
        }
        
        if (specification.mapType) {
            newMapping.mapType = specification.mapType;
        }
        
        const updatedNewField = event.target.value;
        
        if (updatedNewField) {
            newMapping.value = updatedNewField;
        }
        
        mappingChanged(mappingID, index, newMapping);
    }
    
    const renderedMapType: JSX.Element = renderSelect({
        id: `${mappingID}-map-type`,
        key: `${mappingID}-map-type`,
        name: "Field Type",
        index: index,
        options: [
            ["Object Key", "key"],
            ["Object Value", "value"],
            ["Column", "column"]
        ],
        selectValueChanged: mapTypeChanged,
        currentValue: specification.mapType,
        style: style
    })
    
    const renderedFieldText: JSX.Element = renderText({
        id: `${mappingID}-field`,
        key: `${mappingID}-field`,
        name: "Original Field",
        index: index,
        valueChanged: originalFieldChanged,
        currentValue: specification.field,
        style: style
    })
    
    const renderedValueText: JSX.Element = renderText({
        id: `${mappingID}-value`,
        key: `${mappingID}-value`,
        name: "New Field",
        index: index,
        valueChanged: newFieldChanged,
        currentValue: specification.value,
        style: style
    })
    
    return (
        <div id={mappingID} key={mappingID}>
            Data within {getFieldMappingArticle()}
            {renderedMapType} at {renderedFieldText} should map to a new field named
            {renderedValueText}
        </div>
    );
}

export default FieldMapping;