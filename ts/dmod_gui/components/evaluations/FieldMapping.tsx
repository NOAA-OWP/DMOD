import {useState} from "react";
import {Label} from "@mui/icons-material";
import FormLabel from "@mui/material/FormLabel";
import getTemplates from "./Templates";

export interface FieldMappingProperties {
    id: string;
    count: number
}

function useTemplateName(specificationType: string) {
    const [selectedTemplateID, setSelectedTemplateID] = useState()
    const templates = getTemplates(specificationType)
    
    function selectTemplate() {
        // This should handle the onChange event from the markup
    }
    
    function getMarkup() {
        // Generate a select box that displays information about all found templates
    }
    
    function getSelectedTemplate() {
        // Get all template data that was selected in the proper object format (i.e. not just the id or name)
    }
    
    return [getMarkup, getSelectedTemplate]
}

function FieldMapping(properties: FieldMappingProperties) {
    const [name, setName] = useState<string>()
    // TODO: Find a way to get template names dynamically
    const [templateName, setTemplateName] = useState<string>();
    const [field, setField] = useState<string>()
    const [mapType, setMapType] = useState<string>()
    const [value, setValue] = useState<string>()
    
    const mappingID = `${properties.id}-FieldMapping-${properties.count}`
    const isEvenElement = properties.count % 2 == 0;
    
    return (
        <div
            id={mappingID}
            className={'FieldMapping'}
        >
            <label htmlFor={`${mappingID}-Name`}>Name</label>
            <input type={"text"} id={`${mappingID}-Name`} name={`${mappingID}-Name`} value={name}/>
            <br/>
            <label htmlFor={`${mappingID}-TemplateName`}>Template Name</label>
        </div>
    );
}

export default FieldMapping;