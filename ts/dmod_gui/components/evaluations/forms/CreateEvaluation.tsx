import Form from "@rjsf/mui";
import { useState } from "react";
import schema from "../../../schemas/EvaluationSpecification.schema.json";
import FieldMapping from "../FieldMapping";
import {useVariableComponents} from "../../../hooks/useVariableComponents";
import {FieldMappingSpecification} from "../../../lib/evaluation/Specification";

export const CreateEvaluation = () => {
    const [data, setData] = useState({});
    
    const [fieldMappings, setFieldMappings] = useState<FieldMappingSpecification[]>([
            {field: "date", mapType: "column", value: "valid_date"},
            {field: "location_id", mapType: "key", value: "location"},
            {field: "measurement", mapType: "value", value: "value"}
        ])
    
    const fieldMappingInterfaces = useVariableComponents<FieldMappingSpecification>({
        id: "Field Mapping",
        name: "Field Mapping",
        createEntry: (): FieldMappingSpecification => {return {}},
        render: FieldMapping,
        innerProperties: {
            id: "Evaluations-FieldMapping",
            name: "Field Mapping"
        },
        values: fieldMappings,
        setValues: setFieldMappings,
        canAdd: (values: FieldMappingSpecification[]): boolean => {
            const invalidValues: (string|undefined|null)[] = [undefined, null];
            
            for (const value of values) {
                const fieldIsInvalid = invalidValues.includes(value?.field);
                const mapTypeIsInvalid = invalidValues.includes(value?.mapType);
                const valueIsInvalid = invalidValues.includes(value?.value)
                if (fieldIsInvalid || mapTypeIsInvalid || valueIsInvalid) {
                    return false;
                }
            }
            return true;
        }
    });
    
    return (
        <>
            {fieldMappingInterfaces.render()}
        </>
    );
};

export default CreateEvaluation;
