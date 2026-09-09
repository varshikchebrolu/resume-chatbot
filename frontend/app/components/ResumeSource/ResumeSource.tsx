"use client";

import { useEffect, useRef, useState } from "react";
import {
  clearResume,
  getResumeStatus,
  setResumeText,
  uploadResume,
} from "../../lib/api";
import type { ResumeStatus } from "../../types";
import styles from "./ResumeSource.module.scss";

export default function ResumeSource({
  onChange,
}: {
  onChange?: (status: ResumeStatus) => void;
}) {
  const [status, setStatus] = useState<ResumeStatus | null>(null);
  const [pasteOpen, setPasteOpen] = useState(false);
  const [pasteText, setPasteText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const apply = (s: ResumeStatus) => {
    setStatus(s);
    onChange?.(s);
  };

  useEffect(() => {
    getResumeStatus()
      .then(apply)
      .catch((e) => setError(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const run = async (fn: () => Promise<ResumeStatus>) => {
    setBusy(true);
    setError(null);
    try {
      apply(await fn());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  };

  const onFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) run(() => uploadResume(file));
    if (fileRef.current) fileRef.current.value = "";
  };

  return (
    <div className={styles.wrap}>
      <div className={styles.row}>
        <span className={styles.badge}>
          {status?.has_custom_resume ? "Custom resume" : "Default resume"}
          {status ? ` · ${status.length} chars` : ""}
        </span>

        <div className={styles.actions}>
          <button
            type="button"
            className={styles.btn}
            disabled={busy}
            onClick={() => fileRef.current?.click()}
          >
            Upload
          </button>
          <button
            type="button"
            className={styles.btn}
            disabled={busy}
            onClick={() => setPasteOpen((v) => !v)}
          >
            Paste
          </button>
          {status?.has_custom_resume && (
            <button
              type="button"
              className={styles.btn}
              disabled={busy}
              onClick={() => run(clearResume)}
            >
              Reset
            </button>
          )}
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.docx,.txt,.md"
            hidden
            onChange={onFile}
          />
        </div>
      </div>

      {pasteOpen && (
        <div className={styles.paste}>
          <textarea
            className={styles.textarea}
            rows={6}
            placeholder="Paste your resume text…"
            value={pasteText}
            onChange={(e) => setPasteText(e.target.value)}
          />
          <button
            type="button"
            className={styles.btnPrimary}
            disabled={busy || !pasteText.trim()}
            onClick={() =>
              run(async () => {
                const s = await setResumeText(pasteText);
                setPasteText("");
                setPasteOpen(false);
                return s;
              })
            }
          >
            Save resume
          </button>
        </div>
      )}

      {status?.preview && (
        <p className={styles.preview}>{status.preview}…</p>
      )}
      {error && <p className={styles.error}>{error}</p>}
    </div>
  );
}
