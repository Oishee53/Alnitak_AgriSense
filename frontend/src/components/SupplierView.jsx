// Marketplace / supplier comparison (Tier 2). The fertilizer basket the farm
// actually needs, priced at each supplier and ranked cheapest-first, with the
// best pick highlighted and delivery/rating tradeoffs called out. Catalog is
// seeded/mock — disclosed at the bottom. Bangla mode: labels from the static
// dictionary, recommendation + tradeoffs + disclosure via lib/bn.js.
import { t } from "../lib/i18n.js";
import { localize, cropName, d } from "../lib/bn.js";

const money = (v, lang) => (v == null ? "—" : d(Number(v).toLocaleString(), lang));

export default function SupplierView({ suppliers, lang = "en" }) {
  if (!suppliers || suppliers.error) return null;
  const s = suppliers;
  const needs = s.needs_kg || {};
  const bestId = s.best_supplier_id;

  return (
    <div className="card supplier-view">
      <h2>{t(lang, "sup.title")} · {cropName(s.crop, lang)}</h2>

      <p className="sub">
        {t(lang, "sup.basket1")}{d(s.farm_size_acres, lang)}{t(lang, "sup.basket2")}{" "}
        {Object.entries(needs).map(([k, v], i) => (
          <span key={k}>
            {i > 0 && " · "}
            <strong>{money(v, lang)} kg</strong> {k.replace("_kg", "").toUpperCase()}
          </span>
        ))}
      </p>

      <table>
        <thead>
          <tr>
            <th>{t(lang, "sup.supplier")}</th>
            <th>{t(lang, "sup.basketCost")}</th>
            <th>{t(lang, "sup.delivery")}</th>
            <th>{t(lang, "sup.rating")}</th>
            <th>{t(lang, "sup.distance")}</th>
          </tr>
        </thead>
        <tbody>
          {s.suppliers?.map((sup) => (
            <tr key={sup.id} className={sup.id === bestId ? "supplier-best" : ""}>
              <td>
                {sup.id === bestId && (
                  <span className="best-badge">{t(lang, "sup.cheapest")}</span>
                )}
                {sup.name}
              </td>
              <td>
                <strong>{money(sup.total_input_cost_bdt, lang)} BDT</strong>
              </td>
              <td>{d(sup.delivery_days, lang)} {t(lang, "sup.days")}</td>
              <td>{d(sup.rating, lang)} ★</td>
              <td>{d(sup.distance_km, lang)} km</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="market-rec rec-store">
        <div className="market-rec-call">{localize(s.recommendation, lang)}</div>
        <div className="market-rec-because">{localize(s.because, lang)}</div>
      </div>

      {s.tradeoffs?.length > 0 && (
        <p className="hint">
          {t(lang, "sup.other")}{" "}
          {s.tradeoffs.map((tr) => localize(tr, lang)).join("; ")}.
        </p>
      )}

      <p className="assumptions">{localize(s.catalog_source, lang)}</p>
    </div>
  );
}
