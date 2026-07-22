"use client";

import { useRef, useEffect } from "react";
import type { MessageListProps } from "@/app/types";
import MessageBubble from "../MessageBubble";
import LoadingIndicator from "../LoadingIndicator";
import styles from "./MessageList.module.scss";

export default function MessageList({ messages, isLoading }: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <main className={styles.messages}>
      <div className={styles.messagesInner}>
        {messages.length === 0 && (
          <div className={styles.emptyState}>
            <p>Send a message to start the conversation.</p>
          </div>
        )}

        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}

        {isLoading && <LoadingIndicator />}

        <div ref={messagesEndRef} />
      </div>
    </main>
  );
}
