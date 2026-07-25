// Shows the farm profile the agent has collected so far (Tier-0 #1 intake +
// memory made visible). Judges can watch fields fill in as the farmer talks.
// Labels come from the static dictionary; enum VALUES (soil, water, season)
// go through the deterministic token map in lib/bn.js — never the model.
import { t } from "../lib/i18n.js";
import { tk, d, placeName } from "../lib/bn.js";

const FIELDS = [
  ["location", "profile.location"],
  ["farm_size_acres", "profile.size"],
  ["soil_type", "profile.soil"],
  ["water_availability", "profile.water"],
  ["budget_bdt", "profile.budget"],
  ["target_season", "profile.season"],
];

// Render a profile value: numbers → Bengali digits; location → place name;
// soil/water/season enums → token map; anything else → as-is.
function fmtValue(key, v, lang) {
  if (typeof v === "number") return d(v.toLocaleString(), lang);
  if (key === "location") return placeName(v, lang);
  return tk(String(v), lang);
}

export default function ProfileCard({ farm, lang = "en" }) {
  if (!farm) return null;
  const known = FIELDS.filter(([k]) => farm[k] != null && farm[k] !== "");
  return (
    <div className="card profile">
      <h2>
        {t(lang, "profile.title")}{" "}
        <span className="profile-count">
          {d(known.length, lang)}/{d(FIELDS.length, lang)} {t(lang, "profile.collected")}
        </span>
      </h2>
      <div className="profile-grid">
        {FIELDS.map(([key, labelKey]) => {
          const v = farm[key];
          const has = v != null && v !== "";
          return (
            <div key={key} className={`profile-item ${has ? "known" : "missing"}`}>
              <span className="profile-label">{t(lang, labelKey)}</span>
              <span className="profile-value">
                {has ? fmtValue(key, v, lang) : "—"}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
