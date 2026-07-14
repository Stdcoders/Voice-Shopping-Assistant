import { useState, useCallback, useEffect } from "react";
import MicButton from "./components/MicButton.jsx";
import ShoppingList from "./components/ShoppingList.jsx";
import TranscriptDisplay from "./components/TranscriptDisplay.jsx";
import RecommendationsPanel from "./components/RecommendationsPanel.jsx";
import SearchPanel from "./components/SearchPanel.jsx";
import { sendVoiceCommand, fetchItems } from "./api.js";

export default function App() {
  const [items, setItems] = useState([]); // hydrated from server, server is source of truth
  const [transcript, setTranscript] = useState("");
  const [status, setStatus] = useState("idle"); // idle | loading | processing | error
  const [errorMessage, setErrorMessage] = useState("");
  // Bumped whenever the list changes via voice, forcing RecommendationsPanel
  // to remount and refetch — keeps suggestions in sync with the live list.
  const [refreshKey, setRefreshKey] = useState(0);
  // Results from a voice/text command with action === "search" (e.g.
  // "find toothpaste under $5"). Passed down into SearchPanel so it can
  // show them alongside its own manual-filter search results.
  const [voiceSearchResults, setVoiceSearchResults] = useState(null);

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

      // Search commands return { results }, not { list } — route them to
      // SearchPanel instead of trying to treat them as a list update.
      if (result.action === "search") {
        setVoiceSearchResults(result.results || []);
      } else if (result.list) {
        // Server already applied the command to SQLite and returns the
        // full, up-to-date list — just trust it, no client-side merging.
        setItems(result.list);
        setRefreshKey((k) => k + 1); // list changed via voice — refresh suggestions too
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

      <div className="panels-grid">
        <ShoppingList items={items} />
        <RecommendationsPanel key={refreshKey} onListUpdate={setItems} />
        <SearchPanel voiceResults={voiceSearchResults} onListUpdate={setItems} />
      </div>
    </div>
  );
}