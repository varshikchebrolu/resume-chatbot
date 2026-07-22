import styles from "./LoadingIndicator.module.scss";

export default function LoadingIndicator() {
  return (
    <div className={styles.loadingRow}>
      <div className={styles.loadingBubble}>
        <span className={styles.dot} />
        <span className={styles.dot} />
        <span className={styles.dot} />
      </div>
    </div>
  );
}
