import Header from "../components/Header";
import "../styles/globals.css";
import type { AppProps } from "next/app";
import ServiceRouteProvider from "../components/ServiceRoutes";

export default function App({ Component, pageProps }: AppProps) {
    return (
        <>
            <main>
                <Header />
                <Component {...pageProps} />
            </main>
        </>
    );
}
