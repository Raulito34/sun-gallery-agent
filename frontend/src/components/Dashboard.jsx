import { useState } from "react";
import ModeSelector from "./ModeSelector";
import InputPanel from "./InputPanel";
import OutputPanel from "./OutputPanel";
import CollectorList from "./CollectorList";
import FairSchedule from "./FairSchedule";
import SettingsPage from "./SettingsPage";

const PAGES = {
  assistant: "AI Assistant",
  collectors: "Collectors",
  fairs: "Fair Schedule",
  settings: "Settings",
};

export default function Dashboard() {
  const [page, setPage] = useState("assistant");
  const [mode, setMode] = useState("email");
  const [response, setResponse] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const renderPage = () => {
    switch (page) {
      case "collectors":
        return <CollectorList />;
      case "fairs":
        return <FairSchedule />;
      case "settings":
        return <SettingsPage />;
      default:
        return (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div>
              <h2 className="font-display text-lg font-semibold text-charcoal mb-4">
                Request
              </h2>
              <InputPanel
                mode={mode}
                onResponse={setResponse}
                onLoading={setIsLoading}
              />
            </div>
            <div>
              <h2 className="font-display text-lg font-semibold text-charcoal mb-4">
                Response
              </h2>
              <OutputPanel response={response} isLoading={isLoading} />
            </div>
          </div>
        );
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Mobile hamburger */}
      <button
        className="lg:hidden fixed top-4 left-4 z-50 p-2 bg-charcoal text-white rounded-lg cursor-pointer"
        onClick={() => setSidebarOpen(!sidebarOpen)}
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          {sidebarOpen ? (
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          ) : (
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          )}
        </svg>
      </button>

      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/50 z-30"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed lg:static inset-y-0 left-0 z-40 w-64 bg-charcoal text-white flex flex-col transform transition-transform lg:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="p-5 border-b border-white/10">
          <h1 className="font-display text-xl font-bold text-gold">
            Sun Gallery
          </h1>
          <p className="text-xs text-gray-400 mt-1">AI Assistant</p>
        </div>

        {/* Navigation */}
        <nav className="p-4 space-y-1">
          {Object.entries(PAGES).map(([key, label]) => (
            <button
              key={key}
              onClick={() => {
                setPage(key);
                setSidebarOpen(false);
              }}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors cursor-pointer ${
                page === key
                  ? "bg-white/10 text-white font-medium"
                  : "text-gray-400 hover:text-white hover:bg-white/5"
              }`}
            >
              {label}
            </button>
          ))}
        </nav>

        {/* Mode selector (only on assistant page) */}
        {page === "assistant" && (
          <div className="px-4 mt-2">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-2 px-3">
              Mode
            </p>
            <ModeSelector selectedMode={mode} onSelectMode={setMode} />
          </div>
        )}

        {/* Footer */}
        <div className="mt-auto p-4 border-t border-white/10">
          <p className="text-xs text-gray-500">Sun Gallery | Seoul, Korea</p>
          <p className="text-xs text-gray-500">Since 1977</p>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 lg:ml-0">
        <div className="max-w-5xl mx-auto p-6 lg:p-8 pt-16 lg:pt-8">
          <div className="mb-6">
            <h1 className="font-display text-2xl font-bold text-charcoal">
              {PAGES[page]}
            </h1>
          </div>
          {renderPage()}
        </div>
      </main>
    </div>
  );
}
