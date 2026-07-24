// Marketplace / supplier comparison (Tier 2). The fertilizer basket the farm
// actually needs, priced at each supplier and ranked cheapest-first, with the
// best pick highlighted and delivery/rating tradeoffs called out. Catalog is
// seeded/mock — disclosed at the bottom.

const money = (v) => (v == null ? "—" : Number(v).toLocaleString());

export default function SupplierView({ suppliers }) {
  if (!suppliers || suppliers.error) return null;
  const s = suppliers;
  const needs = s.needs_kg || {};
  const bestId = s.best_supplier_id;

  return (
    <div className="card supplier-view">
      <h2>🛒 Where to buy · {s.crop}</h2>

      <p className="sub">
        Fertilizer basket for {s.farm_size_acres} acre:{" "}
        {Object.entries(needs).map(([k, v], i) => (
          <span key={k}>
            {i > 0 && " · "}
            <strong>{money(v)} kg</strong> {k.replace("_kg", "").toUpperCase()}
          </span>
        ))}
      </p>

      <table>
        <thead>
          <tr>
            <th>Supplier</th>
            <th>Basket cost</th>
            <th>Delivery</th>
            <th>Rating</th>
            <th>Distance</th>
          </tr>
        </thead>
        <tbody>
          {s.suppliers?.map((sup) => (
            <tr key={sup.id} className={sup.id === bestId ? "supplier-best" : ""}>
              <td>
                {sup.id === bestId && <span className="best-badge">CHEAPEST</span>}
                {sup.name}
              </td>
              <td>
                <strong>{money(sup.total_input_cost_bdt)} BDT</strong>
              </td>
              <td>{sup.delivery_days} day(s)</td>
              <td>{sup.rating} ★</td>
              <td>{sup.distance_km} km</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="market-rec rec-store">
        <div className="market-rec-call">{s.recommendation}</div>
        <div className="market-rec-because">{s.because}</div>
      </div>

      {s.tradeoffs?.length > 0 && (
        <p className="hint">
          Other options: {s.tradeoffs.join("; ")}.
        </p>
      )}

      <p className="assumptions">{s.catalog_source}</p>
    </div>
  );
}
