/**
 * Uploads a recorded audio blob to the backend, which transcribes it (Groq Whisper)
 * and parses it into a structured shopping command (Groq Llama).
 *
 * @param {Blob} audioBlob - recorded audio, e.g. from MediaRecorder
 * @returns {Promise<{transcript: string, action: string, item: string|null, quantity: number|null}>}
 */
export async function sendVoiceCommand(audioBlob) {
  const formData = new FormData();
  // Filename/extension here is just a hint for the backend - MediaRecorder
  // typically produces webm in Chrome/Edge.
  formData.append("audio", audioBlob, "recording.webm");

  const response = await fetch("/api/voice-command", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(
      errorBody.error || `Request failed with status ${response.status}`,
    );
  }

  return response.json();
}
/**
 * Fetches the current shopping list from the backend (SQLite-backed).
 * Used to hydrate state on app load / refresh.
 *
 * @returns {Promise<{list: Array<{id: number, name: string, quantity: number, unit: string|null, category: string}>}>}
 */
export async function fetchItems() {
  const response = await fetch("/api/items", {
    method: "GET",
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(
      errorBody.error || `Request failed with status ${response.status}`,
    );
  }

  return response.json();
}
