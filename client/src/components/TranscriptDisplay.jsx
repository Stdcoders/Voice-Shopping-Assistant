
export default function TranscriptDisplay({ transcript, status, errorMessage }) {
  if (status === "processing") {
    return (
      <div className="transcript-display processing">
        <p>🎧 Listening… processing your command…</p>
      </div>
    );
  }

  if (errorMessage) {
    return (
      <div className="transcript-display error">
        <p>⚠️ {errorMessage}</p>
      </div>
    );
  }

  if (transcript) {
    return (
      <div className="transcript-display">
        <p>
          Heard: <em>"{transcript}"</em>
        </p>
      </div>
    );
  }

  return null;
}