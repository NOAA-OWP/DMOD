import { ReactNode, SyntheticEvent} from "react";
import {IconButton} from "@mui/material";

const DEFAULT_MARGIN = '10px';
const DEFAULT_PADDING = '10px;'
const FIELDSET_CLASSNAME = "DMODFieldSet";


export interface LegendaryAction {
    key: string;
    action: (event: SyntheticEvent<HTMLButtonElement, MouseEvent>) => any;
    buttonProperties: Record<string, any>;
    icon: JSX.Element;
    shouldShow: () => boolean;
}


export interface FieldSetOptions extends Record<string, any> {
    parentID: string;
    name: string;
    showName?: boolean;
    classes?: string[]|string;
    styles?: Record<string, any>
    legendParameters?: Record<string, any>
    children?: ReactNode | undefined;
    actions?: LegendaryAction[]
}

function setFieldSetDefaults(options: FieldSetOptions): FieldSetOptions {
    let classes: string|string[];
    
    if (Array.isArray(options.classes)) {
        options.classes.push(FIELDSET_CLASSNAME)
        classes = options.classes;
    }
    else if (!options.classes) {
        classes = FIELDSET_CLASSNAME
    }
    else {
        classes = [options.classes, FIELDSET_CLASSNAME];
    }
    
    let styles: Record<string, any>;
    
    if (!(typeof options?.styles === 'object')) {
        styles = {};
    }
    else {
        styles = options.styles;
    }
    
    styles['margin-top'] = styles['margin-top'] || DEFAULT_MARGIN;
    styles['margin-bottom'] = styles['margin-bottom'] || DEFAULT_MARGIN;
    styles['margin-right'] = styles['margin-right'] || DEFAULT_MARGIN;
    styles['margin-left'] = styles['margin-left'] || DEFAULT_MARGIN;
    
    styles['paddingTop'] = styles['paddingTop'] || DEFAULT_PADDING;
    styles['paddingBottom'] = styles['paddingBottom'] || DEFAULT_PADDING;
    styles['paddingRight'] = styles['paddingRight'] || DEFAULT_PADDING;
    styles['paddingLeft'] = styles['paddingLeft'] || DEFAULT_PADDING;
    
    styles['width'] = styles['width'] || 'fit-content';
    
    return {
        parentID: options.parentID,
        name: options.name,
        showName: options.showName || true,
        classes: classes,
        legendParameters: options.legendParameters,
        styles: styles,
        children: options.children,
        actions: options.actions ?? []
    };
}

function buildLegendaryAction(parameters: LegendaryAction): JSX.Element {
    const buttonParameters = {...parameters.buttonProperties};
    buttonParameters['onClick'] = parameters.action;
    
    if (!parameters.shouldShow || parameters.shouldShow()) {
        return (
            <IconButton {...buttonParameters} key={parameters.key}>
                {parameters.icon}
            </IconButton>
        );
    }
    
    return <></>
}


export function FieldSet(fieldOptions: FieldSetOptions): JSX.Element {
    const options = setFieldSetDefaults(fieldOptions);
    
    const parameters: Record<string, any> = {
        id: `${options.parentID}-${options.name.replace(' ', '-')}`
    };
    
    if (options.styles) {
        parameters['style'] = options.styles;
    }
    
    if (options.classes && Array.isArray(options.classes)) {
        parameters['className'] = options.classes.join(" ");
    }
    else if (typeof options.classes === 'string') {
        parameters.className = options.classes;
    }
    
    const legendParameters = options?.legendParameters || {};
    
    legendParameters['id'] = legendParameters?.id ?? `${parameters.id}-legend`;
    
    let legend: JSX.Element;
    if (options.showName) {
        const actions = [];
        
        for (const action of options.actions || []) {
            actions.push(buildLegendaryAction(action));
        }
        
        legend = <legend {...legendParameters}>
            {options.name}
            {actions}
        </legend>
    }
    else {
        legend = <></>
    }
    
    return (
        <>
            <fieldset {...parameters}>
                {legend}
                {options.children}
            </fieldset>
        </>
    );
}

export default FieldSet;