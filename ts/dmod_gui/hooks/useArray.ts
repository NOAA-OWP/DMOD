import {useState } from "react"

export const useArray = <T>(initialState?: T[]) => {
    const [data, setData] = useState<T[]>(initialState ?? [])

    const Insert = (idx: number, element: T): boolean => {
        if (idx > data.length || idx < 0) {
            return false
        }

        setData(curr => [...curr.slice(0, idx), element, ...curr.slice(idx)])
        return true
    }

    const Delete = (idx: number): boolean => {
        if (idx > data.length || idx < 0) {
            return false
        }

        setData(curr => [...curr.slice(0, idx),...curr.slice(idx+1)])
        return true
    }

    const Append = (element: T) => {
        setData(curr => [...curr, element])
    }


    return {data, Insert, Delete, Append}
}

export default useArray
