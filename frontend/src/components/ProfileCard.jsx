// Shows the farm profile the agent has collected so far (Tier-0 #1 intake +
// memory made visible). Judges can watch fields fill in as the farmer talks.
const FIELDS = [
  ["location", "Location"],
  ["farm_size_acres", "Farm size (acres)"],
  ["soil_type", "Soil type"],
  ["water_availability", "Water"],
  ["budget_bdt", "Budget (BDT)"],
  ["target_season", "Season"],
];

export default function ProfileCard({ farm }) {
  if (!farm) return null;
  const known = FIELDS.filter(([k]) => farm[k] != null && farm[k] !== "");
  return (
    <div className="card profile">
      <h2>
        Farm profile{" "}
        <span className="profile-count">
          {known.length}/{FIELDS.length} collected
        </span>
      </h2>
      <div className="profile-grid">
        {FIELDS.map(([key, label]) => {
          const v = farm[key];
          const has = v != null && v !== "";
          return (
            <div key={key} className={`profile-item ${has ? "known" : "missing"}`}>
              <span className="profile-label">{label}</span>
              <span className="profile-value">
                {has ? (typeof v === "number" ? v.toLocaleString() : String(v)) : "—"}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
