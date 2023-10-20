import NextHead from "next/head"

export interface Props {
    title: string
}

export const Head = (props: Props) => {
    return <NextHead>
        <title>{props.title}</title>
        <meta charSet="UTF-8" />
        <meta httpEquiv="X-UA-Compatible" content="IE=edge" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="shortcut icon" href="/favicon.ico" />
    </NextHead>
}

export default Head
