
interface O extends Object{
    [key: string]: any
}

export const setByString = (o: O, path: string, value: any) => {
    // a.b.c = value;
    // equivalent to:
    // o["a"]["b"]["c"] = value; // or
    // o.a.b.c = value;

    const nodes = path.split(".")

    for (const node of nodes.slice(0, nodes.length - 1)) {
        if (!(node in o)) {
            o[node] = {}
        }
        o = o[node];
    }
    o[nodes[nodes.length-1]] = value;
}
