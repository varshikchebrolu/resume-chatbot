import Link from "next/link";
import styles from "./ChatHeader.module.scss";

export default function ChatHeader() {
  return (
    <header className={styles.header}>
      <h1>Chat with Resume</h1>
      <Link href="/optimize" className={styles.navLink}>
        Resume Optimizer →
      </Link>
    </header>
  );
}
