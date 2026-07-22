"use client";

import { useChat } from "@ai-sdk/react";
import { TextStreamChatTransport } from "ai";
import { useState, type FormEvent, type ChangeEvent } from "react";
import { ChatHeader, ChatInput, MessageList } from "../components";
import { API_URL } from "../lib/constants";
import styles from "./page.module.scss";

export default function Home() {
  const [input, setInput] = useState("");
  const { messages, status, sendMessage } = useChat({
    transport: new TextStreamChatTransport({
      api: API_URL,
    }),
  });

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
