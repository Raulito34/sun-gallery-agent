import { useState, useEffect } from "react";

export default function CollectorList() {
  const [collectors, setCollectors] = useState([]);
  const [search, setSearch] = useState("");
  const [filterType, setFilterType] = useState("all");

  useEffect(() => {
    fetch("/api/data/collectors")
      .then((r) => r.json())
      .then(setCollectors)
      .catch(() => setCollectors([]));
  }, []);

  const filtered = collectors.filter((c) => {
    const matchesSearch =
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.region.toLowerCase().includes(search.toLowerCase()) ||
      (c.notes && c.notes.toLowerCase().includes(search.toLowerCase()));
    const matchesType = filterType === "all" || c.type === filterType;
    return matchesSearch && matchesType;
  });

  const types = [...new Set(collectors.map((c) => c.type))];

  return (
    <div className="space-y-4">
      <h2 className="font-display text-xl font-semibold text-charcoal">
        Collectors & Partners
      </h2>

      <div className="flex gap-3">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name, region..."
          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gold"
        />
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-gold"
        >
          <option value="all">All Types</option>
          {types.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </div>

      <div className="grid gap-3">
        {filtered.map((c, i) => (
          <div
            key={i}
            className="bg-white border border-gray-200 rounded-lg p-4"
          >
            <div className="flex justify-between items-start">
              <div>
                <h3 className="font-medium text-charcoal">{c.name}</h3>
                <p className="text-xs text-gray-500 mt-0.5">
                  {c.region} &middot;{" "}
                  <span className="capitalize">{c.type?.replace("_", " ")}</span>
                </p>
              </div>
              {c.interests && c.interests.length > 0 && (
                <div className="flex gap-1 flex-wrap">
                  {c.interests.map((artist) => (
                    <span
                      key={artist}
                      className="px-2 py-0.5 bg-gold/10 text-gold-dark text-xs rounded-full"
                    >
                      {artist}
                    </span>
                  ))}
                </div>
              )}
            </div>
            {c.notes && (
              <p className="text-xs text-gray-500 mt-2">{c.notes}</p>
            )}
          </div>
        ))}
        {filtered.length === 0 && (
          <p className="text-sm text-gray-400 text-center py-8">
            No collectors found
          </p>
        )}
      </div>
    </div>
  );
}
