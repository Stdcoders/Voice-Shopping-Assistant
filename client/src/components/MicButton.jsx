import { useRef, useState, useCallback } from "react";

/**
 * Tap-to-record mic button. Uses the browser's MediaRecorder API to capture
 * a short audio clip, then hands the resulting Blob to onRecordingComplete.
 *
 * We deliberately don't use the browser's SpeechRecognition API here -
 * raw audio gets sent to the backend, which transcribes it via Groq Whisper.
 * This keeps quality consistent across browsers instead of relying on
 * whatever speech engine the browser happens to ship.
 */
export default function MicButton({ onRecordingComplete, onError, disabled }) {
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);

  const stopStream = () => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  };

  const startRecording = useCallback(async () => {
    if (disabled || isRecording) return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];

      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(chunksRef.current, { type: "audio/webm" });
        stopStream();
        if (audioBlob.size === 0) {
          onError?.("No audio captured — try holding the mic button a bit longer.");
          return;
        }
        onRecordingComplete(audioBlob);
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (err) {
      console.error("Mic access failed:", err);
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        onError?.("Microphone permission was denied. Allow mic access to use voice commands.");
      } else if (err.name === "NotFoundError") {
        onError?.("No microphone found on this device.");
      } else {
        onError?.("Couldn't access the microphone. Try again.");
      }
    }
  }, [disabled, isRecording, onRecordingComplete, onError]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  }, [isRecording]);

  const handleClick = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={disabled}
      className={`mic-button ${isRecording ? "recording" : ""}`}
      aria-pressed={isRecording}
    >
      {isRecording ? "⏹ Stop" : "🎤 Tap to speak"}
    </button>
  );
}