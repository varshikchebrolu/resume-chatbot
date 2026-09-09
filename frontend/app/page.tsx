import Link from "next/link";
import styles from "./page.module.scss";

export default function HomePage() {
  return (
    <div className={styles.container}>
      <div className={styles.inner}>
        <h1 className={styles.title}>Resume Toolkit</h1>
        <p className={styles.subtitle}>
          Tools to sharpen your resume and land the interview.
        </p>

        <div className={styles.cards}>
          <Link href="/optimize" className={styles.card}>
            <h2>Resume Optimizer</h2>
            <p>
              Match your resume against a job description, see keyword gaps, and get
              an ATS-optimized rewrite.
            </p>
          </Link>

          <Link href="/chat" className={styles.card}>
            <h2>Chat with Resume</h2>
            <p>Ask questions and get grounded answers from your resume.</p>
          </Link>
        </div>
      </div>
    </div>
  );
}
