// Renders the itemized financial projection (Tier-0 #5): cost lines + derived
// yield, revenue, net profit, ROI, break-even. The math is inspectable here.
export default function FinanceTable({ financials }) {
  if (!financials) return null;
  const f = financials;
  return (
    <div className="card finance">
      <h2>Financial projection · {f.crop}</h2>
      <table>
        <thead>
          <tr>
            <th>Item</th>
            <th>Qty</th>
            <th>Unit cost</th>
            <th>Total (BDT)</th>
          </tr>
        </thead>
        <tbody>
          {f.costs?.map((c, i) => (
            <tr key={i}>
              <td>{c.item}</td>
              <td>{c.qty}</td>
              <td>{c.unit_cost}</td>
              <td>{c.total}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <dl className="metrics">
        <div><dt>Total cost</dt><dd>{f.total_cost_bdt} BDT</dd></div>
        <div><dt>Expected yield</dt><dd>{f.expected_yield} {f.expected_yield_unit}</dd></div>
        <div><dt>Revenue</dt><dd>{f.revenue_bdt} BDT</dd></div>
        <div><dt>Net profit</dt><dd>{f.net_profit_bdt} BDT</dd></div>
        <div><dt>ROI</dt><dd>{f.roi != null ? `${(f.roi * 100).toFixed(1)}%` : "—"}</dd></div>
        <div><dt>Break-even price</dt><dd>{f.break_even_price_bdt_per_unit} BDT/unit</dd></div>
      </dl>
      {f.assumptions?.length > 0 && (
        <p className="assumptions">Assumptions: {f.assumptions.join("; ")}</p>
      )}
    </div>
  );
}
