import {useState} from "react";
import {Label} from "@mui/icons-material";
import FormLabel from "@mui/material/FormLabel";

export interface FieldMappingProperties {
    id: string;
    count: number
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