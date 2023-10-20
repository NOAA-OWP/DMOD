

import {TemplateMetadata, TemplateType} from "../utils/types/templates";
import path from "path";
import {Evaluations} from "../utils/types/Base";
import BaseResponse = Evaluations.BaseResponse;
import {getJSON} from "./common";

interface TemplateCollectionResponse extends BaseResponse{
    templates: Record<TemplateType, TemplateMetadata[]>
}

interface TemplateResponse extends BaseResponse {
    template: Record<string, any>;
}

interface TemplateSearchOptions {
    address: string;
    specificationType: TemplateType;
    author?: string;
    name?: string;
}

async function getTemplates(
    {
        address,
        specificationType,
        name,
        author
    }: TemplateSearchOptions
): Promise<TemplateMetadata[]> {
    const queryParts = [];
    
    if (specificationType) {
        queryParts.push(`specification_type=${specificationType}`);
    }
    
    if (name) {
        queryParts.push(`name=${name}`)
    }
    
    if (author) {
        queryParts.push(`author=${author}`);
    }
    
    const query = "?" + queryParts.join("&");
    
    const url = address + "/" + path.join("templates", "search") + query;
    
    console.log(`Searching for data at ${url}`);
    
    const templateData = await getJSON<TemplateCollectionResponse>(url)
        .then(
            (templateResponse: TemplateCollectionResponse): TemplateMetadata[] => {
                const templates: Record<TemplateType, TemplateMetadata[]> = templateResponse.templates;
                
                if (templates.hasOwnProperty(specificationType)) {
                    return templates[specificationType];
                }
                
                return [];
            }
        ).catch(
            (errorData) => {
                throw new Error(`Encountered error loading template data: ${errorData}`)
            }
        );
    return templateData;
}

export async function getTemplateByID(address: string, id: number): Promise<Record<string, any>> {
    const url = address + "/" + path.join("templates", id.toString());
    
    console.log(`Retrieving template ${id} from "${url}"`);
    
    const template: Record<string, any> = await getJSON<TemplateResponse>(url)
        .then(
            (response: TemplateResponse): Record<string, any> => {
                if (response.status_code >= 400) {
                    const errors = ["Could not retrieve a template:"];
                    
                    if (Array.isArray(response.errors)) {
                        errors.push(...response.errors);
                    }
                    else if (typeof response.errors === 'string') {
                        errors.push(response.errors)
                    }
                    
                    const errorMessage = errors.join("\n");
                    throw new Error(errorMessage);
                }
                return response.template;
            }
        )
        .catch((reason: string) => {
            throw new Error(`Encountered an error when loading a template via ID: ${reason} at address ${url}`);
        })
    
    return template;
}

export default getTemplates;