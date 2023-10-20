import getTemplates, {getTemplateByID} from "../../lib/Templates";
import React, {useEffect, useState} from "react";
import {TemplateMetadata, TemplateType} from "../../utils/types/templates";
import {useServiceAddress} from "../../components/ServiceRoutes";
import {ServiceName} from "../../utils/constants";
import {InputLabel, ListSubheader, MenuItem, Select, SelectChangeEvent} from "@mui/material";


function renderAuthorTemplateOptions(id: string, author: string, templates: TemplateMetadata[]): JSX.Element[] {
    const cleanAuthorName = author.replace(" ", "-");
    const authorID = `${id}-${cleanAuthorName}`;
    
    const options: JSX.Element[] = templates.map(
        (template) => {
            return (
                <MenuItem
                    key={`${authorID}-template-${template.id}`}
                    id={`${authorID}-template-${template.id}`}
                    value={template.id}
                >
                    {template.name}
                </MenuItem>
            );
        }
    )
    
    return [
        <ListSubheader key={`${authorID}`}>{author}</ListSubheader>,
        ...options
    ];
}

// TODO: This will need to be converted from a standard hook to a component since this
//  will end up getting created in some form of loop that will break the rules of 'useState'
function useTemplateName(
    id: string,
    specificationType: TemplateType,
    applyTemplate: (data: Record<string, any>) => any
): () => JSX.Element {
    const [selectedTemplateID, setSelectedTemplateID] = useState<number|null>(null)
    const serviceAddress = useServiceAddress(ServiceName.EVALUATION_SERVICE);
    const [templates, setTemplates] = useState<Record<string, TemplateMetadata[]>>({})
    
    useEffect(
        () => {
            console.log("Loading templates...");
            //this isn't setting the values as needed.
            getTemplates({
                address: serviceAddress,
                specificationType: specificationType}
            ).then(
                (templates: TemplateMetadata[]): Record<string, TemplateMetadata[]> => {
                    const organizedTemplates: Record<string, TemplateMetadata[]> = {};
                    
                    for (const metadata of templates) {
                        const author = metadata?.author ?? "Unknown";
                        if (!Object.hasOwn(organizedTemplates, author)) {
                            organizedTemplates[author] = [];
                        }
                        organizedTemplates[author].push(metadata);
                    }
                    
                    return organizedTemplates;
                }
            )
             .then(setTemplates);
        }, [specificationType, serviceAddress]
    )
    
    useEffect(
        () => {
            if (selectedTemplateID) {
                getTemplateByID(serviceAddress, selectedTemplateID)
                    .then(applyTemplate)
            }
        }, [selectedTemplateID, applyTemplate, serviceAddress]
    )
    
    function selectTemplate(event: SelectChangeEvent) {
        let value: number|string = event.target.value;
        
        if (value === undefined || value === null || value === '') {
            return;
        }
        
        value = parseInt(value);
        
        if (value === selectedTemplateID) {
            return;
        }
        
        try {
            setSelectedTemplateID(value);
        } catch(e) {
            console.error(e);
            return;
        }
    }
    
    function getMarkup() {
        const selectID: string = `${id}-template-name`;
        const selectOptions = Object.entries(templates).map(
            ([author, authorsTemplates]) => {
                return renderAuthorTemplateOptions(selectID, author, authorsTemplates);
            }
        );
        const flattenedOptions = selectOptions.flat(1)
        const allOptions = [<MenuItem value={''} key={`${selectID}-blank`}>No Template</MenuItem>, ...flattenedOptions]
        return (
                <Select id={selectID}
                        className={"template-name"}
                        onChange={selectTemplate}
                        label={"Template"}
                >
                    {allOptions}
                </Select>
        );
    }
    
    return getMarkup
}

export default useTemplateName;