import {TemplateMetadata, TemplateType} from "../../components/evaluations/Templates";
import FieldMapping from "../../components/evaluations/FieldMapping";
const FM = TemplateType.FieldMapping;

function makeTemplateMap(): Record<string, TemplateMetadata[]> {
    let templateMap: Record<string, TemplateMetadata[]> = {};
    templateMap[TemplateType.FieldMapping] = [
        {
            description: "This is the first Field Mapping",
            name: "First Field Mapping",
            specification_type: TemplateType.FieldMapping,
            id: 1,
            author: "Some Person"
        },
        {
            description: "This is the second Field Mapping Value",
            name: "Second Field Mapping",
            specification_type: TemplateType.FieldMapping,
            id: 2,
            author: "Some other person"
        },
        {
            description: "This is the third Field Mapping Value",
            name: "Third Field Mapping",
            specification_type: TemplateType.FieldMapping,
            id: 3,
            author: "Still some other person"
        },
    ];
    
    templateMap[TemplateType.AssociatedField] = [
        {
            description: "This is the first Associated Field",
            name: "First Associated Field",
            specification_type: TemplateType.AssociatedField,
            id: 4,
            author: "Some Person"
        },
        {
            description: "This is the second Associated Field",
            name: "Second Associated Field",
            specification_type: TemplateType.AssociatedField,
            id: 5,
            author: "Some other person"
        },
        {
            description: "This is the third Associated Field",
            name: "Third Associated Field",
            specification_type: TemplateType.AssociatedField,
            id: 6,
            author: "Still some other person"
        },
    ];
    
    templateMap[TemplateType.Backend] = [
        {
            description: "This is the first Backend",
            name: "First Backend",
            specification_type: TemplateType.Backend,
            id: 7,
            author: "Some Person"
        },
        {
            description: "This is the second Backend",
            name: "Second Backend",
            specification_type: TemplateType.Backend,
            id: 8,
            author: "Some other person"
        },
    ];
    return templateMap;
}

export const TemplateMap = makeTemplateMap();
