import {ValueType} from "@sinclair/typebox/value/is";
import {SyntheticEvent} from "react";

export namespace Evaluations {
    export enum StatusCode {
        UNKNOWN = "UNKNOWN",
        SUCCESS = "SUCCESS",
        WARNING = "WARNING",
        ERROR = "ERROR"
    }
    
    export interface BaseResponse {
        response_to: string;
        response_time: string;
        result: StatusCode;
        status_code: number;
        errors?: string|string[];
    }
}

export interface BaseProperties {
    id: string;
    required?: boolean;
    instance?: number;
    className?: string;
    style?: Record<string, string>;
    sx?: Record<string, string>;
}

export interface BaseFieldHookProperties<ValueType = any> extends BaseProperties {
    name: string;
    applyChange?: (newValue: ValueType|null) => any;
    initialValue?: ValueType;
}

export interface BaseHookContainerProperties<
    ValueType,
    InnerHookPropertyType extends BaseFieldHookProperties<ValueType> = BaseFieldHookProperties<ValueType>,
    InterfaceType extends HookInterface<ValueType> = HookInterface<ValueType>
> {
    id: string;
    name: string;
    createEntry: (properties: InnerHookPropertyType) => ValueType;
    innerProperties: InnerHookPropertyType;
    initialValues?: ValueType[]
}

export type RenderFunction = () => JSX.Element;

export interface HookInterface<ValueType> {
    render: RenderFunction;
    update: (value: ValueType) => any;
    get: () => ValueType|null;
    getKey: () => string;
    isPopulated: () => boolean;
}

export interface StringInterface extends HookInterface<string> {
    getText: () => string|null;
}

export type KeyValueInterface<Type = string> = HookInterface<Record<string, Type|null>|null>;

export type FieldHook<ValueType, PropertyType extends BaseFieldHookProperties<ValueType>> =
    (properties: PropertyType) => HookInterface<ValueType>;

export type StringHook<PropertyType extends BaseFieldHookProperties<string>> =
    (properties: PropertyType) => StringInterface;