import { useState } from "react";

export default function OutputPanel({ response, isLoading }) {
  const [copied, setCopied] = useState(false);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-3 border-gold border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-gray-500">Generating response...</p>
        </div>
      </div>
    );
  }

  if (!response) {
    return (
      <div className="flex items-center justify-center py-16 text-gray-400">
        <p className="text-sm">AI response will appear here</p>
      </div>
    );
  }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(response.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const ta = document.createElement("textarea");
      ta.value = response.content;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleMailto = () => {
    const lines = response.content.split("\n");
    const subjectLine = lines.find((l) => l.toLowerCase().startsWith("subject:"));
    const subject = subjectLine ? subjectLine.replace(/^subject:\s*/i, "") : "Sun Gallery";
    const body = response.content;
    const recipient = response.metadata?.recipient || "";
    window.open(
      `mailto:${encodeURIComponent(recipient)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
    );
  };

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <button
          onClick={handleCopy}
          className="px-3 py-1.5 text-xs border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors cursor-pointer"
        >
          {copied ? "Copied!" : "Copy to Clipboard"}
        </button>
        {response.mode === "email" && (
          <button
            onClick={handleMailto}
            className="px-3 py-1.5 text-xs bg-gold text-white rounded-lg hover:bg-gold-dark transition-colors cursor-pointer"
          >
            Send via Email
          </button>
        )}
      </div>
      <div className="bg-white border border-gray-200 rounded-lg p-4 text-sm whitespace-pre-wrap leading-relaxed font-[Inter]">
        {response.content}
      </div>
    </div>
  );
}
