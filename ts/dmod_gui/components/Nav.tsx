import Link from "next/link"
import styles from "../styles/Nav.module.css"

export const Nav = () => {

    return <nav className={styles.nav}>
        <ul className={styles.nav_list}>
            <li className={styles.nav_item}><Link href="/datasets" className={styles.nav_link}>Datasets</Link></li>
            <li className={styles.nav_item}><Link href="/results" className={styles.nav_link}>Results</Link></li>
            <li className={styles.nav_item}><Link href="/simulations" className={styles.nav_link}>Simulations</Link></li>
        </ul>
    </nav>
}

export default Nav
