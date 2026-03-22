import { useState, useEffect } from "react";

export default function SettingsPage() {
  const [context, setContext] = useState("Loading gallery context...");

  useEffect(() => {
    fetch("/api/data/context")
      .then((r) => r.text())
      .then(setContext)
      .catch(() => setContext("Could not load gallery context. Make sure the backend server is running."));
  }, []);

  return (
    <div className="space-y-4">
      <h2 className="font-display text-xl font-semibold text-charcoal">
        Gallery Context
      </h2>
      <p className="text-sm text-gray-500">
        This is the gallery context used by the AI assistant. It is read-only.
      </p>
      <textarea
        value={context}
        readOnly
        rows={24}
        className="w-full px-4 py-3 border border-gray-300 rounded-lg text-xs font-mono bg-gray-50 text-gray-600 resize-y focus:outline-none"
      />
    </div>
  );
}
