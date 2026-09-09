// Base URL of the Resume Toolkit backend.
// Override in development/production via NEXT_PUBLIC_API_BASE_URL.
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8001";

// Chatbot streaming endpoint (used by the chat page).
export const API_URL = `${API_BASE_URL}/getAIResponse`;

// Resume optimizer.
export const OPTIMIZE_URL = `${API_BASE_URL}/optimize`;
export const OPTIMIZATIONS_URL = `${API_BASE_URL}/optimizations`;

// Session resume management.
export const RESUME_URL = `${API_BASE_URL}/resume`;
export const RESUME_TEXT_URL = `${API_BASE_URL}/resume/text`;
export const RESUME_UPLOAD_URL = `${API_BASE_URL}/resume/upload`;
