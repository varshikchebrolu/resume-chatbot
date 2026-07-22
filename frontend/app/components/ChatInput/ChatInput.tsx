import type { ChatInputProps } from "@/app/types";
import styles from "./ChatInput.module.scss";

export default function ChatInput({
  value,
  onChange,
  onSubmit,
  isLoading,
}: ChatInputProps) {
  return (
    <footer className={styles.footer}>
      <form onSubmit={onSubmit} className={styles.form}>
        <input
          value={value}
          onChange={onChange}
          disabled={isLoading}
          placeholder="Type a message..."
          className={styles.input}
        />
        <button
          type="submit"
          disabled={isLoading || !value.trim()}
          className={styles.sendButton}
        >
          Send
        </button>
      </form>
    </footer>
  );
}
