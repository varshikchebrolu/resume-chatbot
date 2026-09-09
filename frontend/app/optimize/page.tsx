"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { ResumeSource } from "../components";
import { runOptimize } from "../lib/api";
import type { OptimizeResult } from "../types";
import styles from "./page.module.scss";

// The optimizer runs several AI passes; give it a generous client timeout.
const CLIENT_TIMEOUT_MS = 5 * 60 * 1000;

export default function OptimizePage() {
  const [jd, setJd] = useState("");
  const [title, setTitle] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<OptimizeResult | null>(null);

  const canSubmit = jd.trim().length > 0 && !isLoading;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;

    setIsLoading(true);
    setError(null);
    setResult(null);

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), CLIENT_TIMEOUT_MS);

    try {
      const data = await runOptimize(
        { jd, title: title.trim() || undefined, save: true },
        controller.signal
      );
      setResult(data);
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        setError("The optimizer took too long and was cancelled. Try shorter input.");
      } else {
        setError(err instanceof Error ? err.message : "Something went wrong.");
      }
    } finally {
      clearTimeout(timer);
      setIsLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1>Resume Optimizer</h1>
        <nav className={styles.nav}>
          <Link href="/optimize/saved" className={styles.navLink}>
            Saved
          </Link>
          <Link href="/chat" className={styles.navLink}>
            Chat →
          </Link>
        </nav>
      </header>

      <main className={styles.main}>
        <ResumeSource />

        <form className={styles.form} onSubmit={handleSubmit}>
          <label className={styles.field}>
            <span className={styles.label}>Title (optional)</span>
            <input
              className={styles.input}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Backend Engineer @ Acme"
            />
          </label>

          <label className={styles.field}>
            <span className={styles.label}>Job Description</span>
            <textarea
              className={styles.textarea}
              value={jd}
              onChange={(e) => setJd(e.target.value)}
              placeholder="Paste the job description here…"
              rows={14}
            />
          </label>

          <div className={styles.actions}>
            <button type="submit" className={styles.button} disabled={!canSubmit}>
              {isLoading ? "Optimizing…" : "Optimize & save"}
            </button>
            {isLoading && (
              <span className={styles.hint}>
                Uses your current resume above. This runs several AI passes and can
                take a minute or two.
              </span>
            )}
          </div>
        </form>

        {error && <div className={styles.error}>{error}</div>}
        {result && <Results result={result} />}
      </main>
    </div>
  );
}

function Results({ result }: { result: OptimizeResult }) {
  return (
    <section className={styles.results}>
      <div className={styles.scoreRow}>
        <div className={styles.scoreCard}>
          <span className={styles.scoreValue}>{Math.round(result.ats_score)}</span>
          <span className={styles.scoreLabel}>ATS score</span>
        </div>
        <div className={styles.meta}>
          <p>
            <strong>{result.iterations}</strong> optimization pass
            {result.iterations === 1 ? "" : "es"}
          </p>
          <p>
            <strong>{result.matched_keywords.length}</strong> matched ·{" "}
            <strong>{result.unmatched_keywords.length}</strong> missing keywords
          </p>
          <p className={styles.savedNote}>
            {result.saved ? (
              <>
                Saved as &ldquo;{result.title}&rdquo; ·{" "}
                <Link href="/optimize/saved">view all saved</Link>
              </>
            ) : (
              "Not saved."
            )}
          </p>
        </div>
      </div>

      <div className={styles.keywordCols}>
        <KeywordList
          title="Matched keywords"
          items={result.matched_keywords}
          variant="matched"
        />
        <KeywordList
          title="Missing from resume"
          items={result.unmatched_keywords}
          variant="missing"
        />
      </div>

      <div className={styles.resumeBlock}>
        <h2>Optimized resume</h2>
        <pre className={styles.resumeText}>{result.updated_resume}</pre>
        <button
          type="button"
          className={styles.copyButton}
          onClick={() => navigator.clipboard?.writeText(result.updated_resume)}
        >
          Copy to clipboard
        </button>
      </div>
    </section>
  );
}

function KeywordList({
  title,
  items,
  variant,
}: {
  title: string;
  items: string[];
  variant: "matched" | "missing";
}) {
  return (
    <div className={styles.keywordCard}>
      <h3>{title}</h3>
      {items.length === 0 ? (
        <p className={styles.empty}>None</p>
      ) : (
        <ul className={styles.tags}>
          {items.map((kw) => (
            <li key={kw} className={`${styles.tag} ${styles[variant]}`}>
              {kw}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
