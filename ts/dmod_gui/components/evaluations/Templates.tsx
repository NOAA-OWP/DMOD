import { TemplateMap } from "../../mock_data/evaluations/templates"
export enum TemplateType {
    FieldMapping = "FieldMappingSpecification",
    Backend = "BackendSpecification",
    Loader = "LoaderSpecification",
    AssociatedField = "AssociatedField",
    ValueSelector = "ValueSelector",
    Location = "LocationSpecification",
    Unit = "UnitSpecification",
    Metric = "MetricSpecification",
    Scheme = "SchemeSpecification",
    Threshold = "ThresholdDefinition",
    ThresholdApplicationRule = "ThresholdApplicationRules",
    Evaluation = "EvaluationSpecification"
}


/**
 * Metadata describing a template
 */
export interface TemplateMetadata {
    description: string
    name: string
    specification_type: string
    id?: number;
    author?: string
}



function getTemplates(type: TemplateType): TemplateMetadata[] {
    let templates: TemplateMetadata[];
    
    switch(type) {
        case TemplateType.FieldMapping:
            templates = TemplateMap.FieldMapping;
            break
        default:
            throw new Error(`Templates cannot be found for a type named "${type}"`);
    }
    
    
    return templates;
}

export default getTemplates;