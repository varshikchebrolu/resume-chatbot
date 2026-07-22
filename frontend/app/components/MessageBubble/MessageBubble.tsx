import type { ChatMessageProps } from "@/app/types";
import styles from "./MessageBubble.module.scss";

export default function MessageBubble({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={`${styles.messageRow} ${isUser ? styles.user : styles.assistant}`}
    >
      <div
        className={`${styles.bubble} ${isUser ? styles.userBubble : styles.assistantBubble}`}
      >
        {message.parts.map((part, i) =>
          part.type === "text" ? <span key={i}>{part.text}</span> : null
        )}
      </div>
    </div>
  );
}
