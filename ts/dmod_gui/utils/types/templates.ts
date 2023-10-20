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
    Evaluation = "EvaluationSpecification",
    DataSource = "DataSourceSpecification"
}


/**
 * Metadata describing a template
 */
export interface TemplateMetadata {
    description: string
    name: string
    specification_type: TemplateType;
    id?: number;
    author?: string
    path?: string|null
}