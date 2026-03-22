const MODES = [
  { id: "email", label: "Email Draft", icon: "✉", description: "이메일 드래프트" },
  { id: "whatsapp", label: "WhatsApp", icon: "💬", description: "WhatsApp 답장" },
  { id: "marketing", label: "Marketing", icon: "📢", description: "마케팅 콘텐츠" },
  { id: "document", label: "Document", icon: "📄", description: "갤러리 문서" },
  { id: "translate", label: "Translate", icon: "🌐", description: "번역" },
  { id: "fair", label: "Fair Prep", icon: "🎪", description: "페어 준비" },
];

export default function ModeSelector({ selectedMode, onSelectMode }) {
  return (
    <div className="space-y-1">
      {MODES.map((mode) => (
        <button
          key={mode.id}
          onClick={() => onSelectMode(mode.id)}
          className={`w-full text-left px-3 py-2.5 rounded-lg transition-all text-sm flex items-center gap-2.5 cursor-pointer ${
            selectedMode === mode.id
              ? "bg-gold text-white font-medium"
              : "text-gray-300 hover:bg-charcoal-light hover:text-white"
          }`}
        >
          <span className="text-base">{mode.icon}</span>
          <div>
            <div className="leading-tight">{mode.label}</div>
            <div className="text-xs opacity-60">{mode.description}</div>
          </div>
        </button>
      ))}
    </div>
  );
}
