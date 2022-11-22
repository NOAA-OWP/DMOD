import { setByString } from "./setByString";

describe("setByString", () => {
    it("create simple object", () => {
        const o = {}
        setByString(o, "a", 12)
        expect(o.a).toEqual(12)
    })

    it("creates nested object", () => {
        const o = {}
        setByString(o, "a.b.c", 12)
        expect(o.a.b.c).toEqual(12)
    })
    it("update nested object", () => {
        const o = {
            a: {
                b: {
                    c: 10
                }
            }
        }
        setByString(o, "a.b.c", 12)
        expect(o.a.b.c).toEqual(12)
    })

})
