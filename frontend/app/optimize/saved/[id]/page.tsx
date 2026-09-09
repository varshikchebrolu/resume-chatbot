"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { getOptimization } from "../../../lib/api";
import type { OptimizationDetail } from "../../../types";
import styles from "./page.module.scss";

export default function SavedDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [item, setItem] = useState<OptimizationDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getOptimization(Number(id))
      .then(setItem)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <Link href="/optimize/saved" className={styles.back}>
          ← Saved
        </Link>
        <h1>{item?.title ?? "Optimization"}</h1>
      </header>

      <main className={styles.main}>
        {loading && <p className={styles.muted}>Loading…</p>}
        {error && <p className={styles.error}>{error}</p>}

        {item && (
          <>
            <div className={styles.scoreRow}>
              <div className={styles.scoreCard}>
                <span className={styles.scoreValue}>
                  {Math.round(item.ats_score)}
                </span>
                <span className={styles.scoreLabel}>ATS score</span>
              </div>
              <div className={styles.meta}>
                <p>
                  <strong>{item.iterations}</strong> optimization pass
                  {item.iterations === 1 ? "" : "es"}
                </p>
                <p>
                  <strong>{item.matched_keywords.length}</strong> matched ·{" "}
                  <strong>{item.unmatched_keywords.length}</strong> missing
                </p>
              </div>
            </div>

            <Section title="Job description">
              <pre className={styles.text}>{item.jd}</pre>
            </Section>

            <Section title="Optimized resume">
              <pre className={styles.text}>{item.optimized_resume}</pre>
              <button
                type="button"
                className={styles.copyButton}
                onClick={() =>
                  navigator.clipboard?.writeText(item.optimized_resume)
                }
              >
                Copy to clipboard
              </button>
            </Section>

            <Section title="Original resume">
              <pre className={styles.text}>{item.original_resume}</pre>
            </Section>
          </>
        )}
      </main>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className={styles.section}>
      <h2>{title}</h2>
      {children}
    </section>
  );
}
