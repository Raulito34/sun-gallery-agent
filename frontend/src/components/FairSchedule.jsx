import { useState, useEffect } from "react";

export default function FairSchedule() {
  const [fairs, setFairs] = useState([]);

  useEffect(() => {
    fetch("/api/data/fairs")
      .then((r) => r.json())
      .then(setFairs)
      .catch(() => setFairs([]));
  }, []);

  const statusColors = {
    preparing: "bg-amber-100 text-amber-700",
    confirmed: "bg-green-100 text-green-700",
    completed: "bg-gray-100 text-gray-500",
  };

  return (
    <div className="space-y-4">
      <h2 className="font-display text-xl font-semibold text-charcoal">
        2026 Fair Schedule
      </h2>

      <div className="grid gap-4 md:grid-cols-2">
        {fairs.map((fair, i) => (
          <div
            key={i}
            className="bg-white border border-gray-200 rounded-lg p-5 hover:shadow-md transition-shadow"
          >
            <div className="flex justify-between items-start mb-3">
              <h3 className="font-display font-semibold text-charcoal text-lg leading-tight">
                {fair.name}
              </h3>
              <span
                className={`px-2 py-0.5 text-xs rounded-full capitalize ${
                  statusColors[fair.status] || statusColors.preparing
                }`}
              >
                {fair.status}
              </span>
            </div>
            <div className="space-y-1.5 text-sm text-gray-600">
              <p>{fair.dates}</p>
              {fair.booth && (
                <p>
                  Booth: <span className="font-medium text-charcoal">{fair.booth}</span>
                  {fair.sector && ` (${fair.sector})`}
                </p>
              )}
              {fair.exhibition_title && (
                <p className="italic text-gold-dark">
                  &ldquo;{fair.exhibition_title}&rdquo;
                </p>
              )}
            </div>
            {fair.artists && fair.artists.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1">
                {fair.artists.map((artist) => (
                  <span
                    key={artist}
                    className="px-2 py-0.5 bg-light-gray text-charcoal text-xs rounded-full"
                  >
                    {artist}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
