"use client";

import { useChat } from "@ai-sdk/react";
import { TextStreamChatTransport } from "ai";
import {
  useMemo,
  useState,
  type FormEvent,
  type ChangeEvent,
} from "react";
import { ChatHeader, ChatInput, MessageList, ResumeSource } from "../components";
import { API_URL } from "../lib/constants";
import styles from "./page.module.scss";

export default function Home() {
  const [input, setInput] = useState("");
  const [jd, setJd] = useState("");
  const [jdOpen, setJdOpen] = useState(false);

  // Rebuild the transport when the JD changes so it's sent with each message.
  const transport = useMemo(
    () =>
      new TextStreamChatTransport({
        api: API_URL,
        body: { jd },
      }),
    [jd]
  );

  const { messages, status, sendMessage } = useChat({ transport });

  const isLoading = status === "streaming" || status === "submitted";

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    sendMessage({ text: input });
    setInput("");
  };

  const handleInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    setInput(e.target.value);
  };

  return (
    <div className={styles.container}>
      <ChatHeader />

      <div className={styles.context}>
        <ResumeSource />
        <div className={styles.jdBox}>
          <button
            type="button"
            className={styles.jdToggle}
            onClick={() => setJdOpen((v) => !v)}
          >
            {jd.trim()
              ? "Target JD attached ✓"
              : "Add a target job description (optional)"}
            <span>{jdOpen ? "▲" : "▼"}</span>
          </button>
          {jdOpen && (
            <textarea
              className={styles.jdTextarea}
              rows={5}
              placeholder="Paste a job description to ask about fit and gaps…"
              value={jd}
              onChange={(e) => setJd(e.target.value)}
            />
          )}
        </div>
      </div>

      <MessageList messages={messages} isLoading={isLoading} />
      <ChatInput
        value={input}
        onChange={handleInputChange}
        onSubmit={handleSubmit}
        isLoading={isLoading}
      />
    </div>
  );
}
