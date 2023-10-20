import Image from "next/image"
import styles from "../styles/Header.module.css"
import Nav from "./Nav"

export const Header = () => {
    return <header className={styles.header}>
        <Image className={styles.logo} src="/logo.png" alt="NOAA Office of Water Prediction (OWP) Logo" width={1035} height={194} />
        < Nav />
    </header>
}

export default Header
