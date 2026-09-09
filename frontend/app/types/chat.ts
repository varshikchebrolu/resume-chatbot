import type { UIMessage } from "@ai-sdk/react";

export type ChatStatus = "streaming" | "submitted" | "ready" | "error";

export interface ChatMessageProps {
  message: UIMessage;
}

export interface ChatInputProps {
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onSubmit: (e: React.FormEvent) => void;
  isLoading: boolean;
}

export interface MessageListProps {
  messages: UIMessage[];
  isLoading: boolean;
}
