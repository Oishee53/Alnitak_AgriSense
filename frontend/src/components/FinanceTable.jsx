// Renders the itemized financial projection (Tier-0 #5): cost lines + derived
// yield, revenue, net profit, ROI, break-even. The math is inspectable here.
// Labels follow the language toggle; the NUMBERS stay exactly as computed so
// they match the agent trace digit-for-digit.
import { t } from "../lib/i18n.js";
import { localize, cropName, tk, d } from "../lib/bn.js";

export default function FinanceTable({ financials, lang = "en" }) {
  if (!financials) return null;
  const f = financials;
  return (
    <div className="card finance">
      <h2>{t(lang, "fin.title")} · {cropName(f.crop, lang)}</h2>
      <table>
        <thead>
          <tr>
            <th>{t(lang, "fin.item")}</th>
            <th>{t(lang, "fin.qty")}</th>
            <th>{t(lang, "fin.unitCost")}</th>
            <th>{t(lang, "fin.totalBdt")}</th>
          </tr>
        </thead>
        <tbody>
          {f.costs?.map((c, i) => (
            <tr key={i}>
              <td>{localize(c.item, lang)}</td>
              <td>{d(c.qty, lang)}</td>
              <td>{d(c.unit_cost, lang)}</td>
              <td>{d(c.total, lang)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <dl className="metrics">
        <div><dt>{t(lang, "fin.totalCost")}</dt><dd>{d(f.total_cost_bdt, lang)} BDT</dd></div>
        <div><dt>{t(lang, "fin.yield")}</dt><dd>{d(f.expected_yield, lang)} {tk(f.expected_yield_unit, lang)}</dd></div>
        <div><dt>{t(lang, "fin.revenue")}</dt><dd>{d(f.revenue_bdt, lang)} BDT</dd></div>
        <div><dt>{t(lang, "fin.net")}</dt><dd>{d(f.net_profit_bdt, lang)} BDT</dd></div>
        <div><dt>{t(lang, "fin.roi")}</dt><dd>{f.roi != null ? `${d((f.roi * 100).toFixed(1), lang)}%` : "—"}</dd></div>
        <div><dt>{t(lang, "fin.breakEven")}</dt><dd>{d(f.break_even_price_bdt_per_unit, lang)} BDT/{tk("unit", lang) === "unit" ? (lang === "bn" ? "একক" : "unit") : "unit"}</dd></div>
      </dl>
      {f.assumptions?.length > 0 && (
        <p className="assumptions">
          {t(lang, "fin.assumptions")}{" "}
          {f.assumptions.map((a) => localize(a, lang)).join("; ")}
        </p>
      )}
    </div>
  );
}
