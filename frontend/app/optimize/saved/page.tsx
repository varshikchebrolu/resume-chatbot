"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { deleteOptimization, listOptimizations } from "../../lib/api";
import type { OptimizationSummary } from "../../types";
import styles from "./page.module.scss";

export default function SavedPage() {
  const [items, setItems] = useState<OptimizationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    listOptimizations()
      .then((data) => {
        setItems(data);
        setError(null);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const onDelete = async (id: number) => {
    try {
      await deleteOptimization(id);
      setItems((prev) => prev.filter((i) => i.id !== id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed.");
    }
  };

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1>Saved optimizations</h1>
        <Link href="/optimize" className={styles.navLink}>
          + New
        </Link>
      </header>

      <main className={styles.main}>
        {loading && <p className={styles.muted}>Loading…</p>}
        {error && <p className={styles.error}>{error}</p>}
        {!loading && !error && items.length === 0 && (
          <p className={styles.muted}>
            Nothing saved yet. <Link href="/optimize">Run an optimization →</Link>
          </p>
        )}

        <ul className={styles.list}>
          {items.map((item) => (
            <li key={item.id} className={styles.card}>
              <Link href={`/optimize/saved/${item.id}`} className={styles.cardMain}>
                <span className={styles.cardTitle}>{item.title}</span>
                <span className={styles.cardMeta}>
                  ATS {Math.round(item.ats_score)} · {item.iterations} pass
                  {item.iterations === 1 ? "" : "es"}
                  {item.created_at
                    ? ` · ${new Date(item.created_at).toLocaleString()}`
                    : ""}
                </span>
              </Link>
              <button
                type="button"
                className={styles.delete}
                onClick={() => onDelete(item.id)}
                aria-label="Delete"
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      </main>
    </div>
  );
}
