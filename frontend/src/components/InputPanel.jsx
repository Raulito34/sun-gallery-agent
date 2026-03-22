import { useState } from "react";

const MODE_ENDPOINTS = {
  email: "/api/email-draft",
  whatsapp: "/api/whatsapp-reply",
  marketing: "/api/marketing-content",
  document: "/api/gallery-document",
  translate: "/api/translate",
  fair: "/api/fair-prep",
};

const MODE_PLACEHOLDERS = {
  email: "e.g., Write a follow-up email to Ahmed about Youngji Lee paintings he saw at Art Central HK...",
  whatsapp: "e.g., Ahmed asked about new Youngji Lee works available...",
  marketing: "e.g., Create an Instagram post for Art Basel HK 2026, booth 3D28, featuring Chungji Lee solo show...",
  document: "e.g., Generate a Sale Offer for Youngji Lee 'Tree and Bird - Spring' 2024, 130x162cm...",
  translate: "e.g., Translate the following artist statement to Arabic: ...",
  fair: "e.g., Create a pre-fair checklist for Art Central Hong Kong 2026...",
};

export default function InputPanel({ mode, onResponse, onLoading }) {
  const [recipient, setRecipient] = useState("");
  const [message, setMessage] = useState("");
  const [language, setLanguage] = useState("en");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!message.trim()) return;

    setIsSubmitting(true);
    onLoading(true);

    try {
      const res = await fetch(MODE_ENDPOINTS[mode], {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode,
          message,
          recipient: recipient || null,
          sender: "Joonwha Lee",
          language,
        }),
      });

      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const data = await res.json();
      onResponse(data);
    } catch (err) {
      onResponse({
        content: `Error: ${err.message}. Make sure the backend server is running (uvicorn main:app --reload).`,
        mode,
        metadata: { error: true },
      });
    } finally {
      setIsSubmitting(false);
      onLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-charcoal mb-1">
            Recipient
          </label>
          <input
            type="text"
            value={recipient}
            onChange={(e) => setRecipient(e.target.value)}
            placeholder="Name or email"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gold focus:border-transparent"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-charcoal mb-1">
            Language
          </label>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gold focus:border-transparent bg-white"
          >
            <option value="en">English</option>
            <option value="ko">한국어</option>
            <option value="ar">العربية</option>
          </select>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-charcoal mb-1">
          Request
        </label>
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder={MODE_PLACEHOLDERS[mode] || "Describe your request..."}
          rows={6}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gold focus:border-transparent resize-y"
        />
      </div>

      <button
        type="submit"
        disabled={isSubmitting || !message.trim()}
        className="w-full bg-gold hover:bg-gold-dark text-white font-medium py-2.5 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
      >
        {isSubmitting ? "Generating..." : "Generate"}
      </button>
    </form>
  );
}
