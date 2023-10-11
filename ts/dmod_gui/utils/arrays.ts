export function removeArrayIndex<Type>(array: Type[], index: number): Type[] {
    const copiedArray = array.map<Type>(entry => entry);
    const beginning = copiedArray.splice(0, index);
    copiedArray.splice(0, 1);
    beginning.push(...copiedArray);
    return beginning;
}

export function insertIntoArray(values: any[]|null|undefined, newValue: any, index?: number): any[] {
    if (!index) {
        index = 0;
    }
    
    const newElement = [newValue];
    
    if (!values) {
        return newElement;
    }
    
    return values.slice(0, index).concat(newElement).concat(values.slice(index))
}

export function selectRandom<Type>(values: Type[]|null|undefined): Type|null {
    if (values) {
        const index = Math.floor(Math.random() * values.length)
        return values[index];
    }
    return null;
}