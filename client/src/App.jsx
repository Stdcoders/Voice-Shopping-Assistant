import { useState, useCallback, useEffect } from "react";
import MicButton from "./components/MicButton.jsx";
import ShoppingList from "./components/ShoppingList.jsx";
import TranscriptDisplay from "./components/TranscriptDisplay.jsx";
import { sendVoiceCommand, fetchItems } from "./api.js";

export default function App() {
  const [items, setItems] = useState([]); // hydrated from server, server is source of truth
  const [transcript, setTranscript] = useState("");
  const [status, setStatus] = useState("idle"); // idle | loading | processing | error
  const [errorMessage, setErrorMessage] = useState("");

  // Hydrate the list from SQLite on first load / refresh.
  useEffect(() => {
    let cancelled = false;

    async function loadItems() {
      setStatus("loading");
      try {
        const result = await fetchItems();
        if (!cancelled) {
          setItems(result.list || []);
          setStatus("idle");
        }
      } catch (err) {
        console.error("Failed to load shopping list:", err);
        if (!cancelled) {
          setErrorMessage("Couldn't load your saved list. Try refreshing.");
          setStatus("error");
        }
      }
    }

    loadItems();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleRecordingComplete = useCallback(async (audioBlob) => {
    setStatus("processing");
    setErrorMessage("");

    try {
      const result = await sendVoiceCommand(audioBlob);
      setTranscript(result.transcript || "");

      if (result.action === "unknown" || !result.transcript) {
        setErrorMessage(
          result.message || "Didn't quite catch that — try again."
        );
      }

      // Server already applied the command to SQLite and returns the
      // full, up-to-date list — just trust it, no client-side merging.
      if (result.list) {
        setItems(result.list);
      }

      setStatus("idle");
    } catch (err) {
      console.error("Voice command failed:", err);
      setErrorMessage("Something went wrong reaching the server. Try again.");
      setStatus("error");
    }
  }, []);

  const handleRecordingError = useCallback((message) => {
    setErrorMessage(message);
    setStatus("error");
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <h1>🛒 Voice Shopping Assistant</h1>
        <p>Tap the mic and say something like "add milk" or "remove eggs"</p>
      </header>

      <MicButton
        onRecordingComplete={handleRecordingComplete}
        onError={handleRecordingError}
        disabled={status === "processing"}
      />

      <TranscriptDisplay
        transcript={transcript}
        status={status}
        errorMessage={errorMessage}
      />

      <ShoppingList items={items} />
    </div>
  );
}