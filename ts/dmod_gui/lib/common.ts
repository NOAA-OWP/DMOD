export async function getJSON<T>(url: string, options?: Record<string, any>): Promise<T> {
    return await fetch(url, options)
        .then(
            (response: globalThis.Response): T => {
                return response.json() as T;
            }
        )
        .catch((reason: string) => {
            throw new Error(`Could not retrieve JSON data: ${reason}`)
        });
}