// Visible agent trace (Tier-0 #8). Renders every thought, tool call (params
// sent) and tool result (raw values returned) so a judge can confirm each
// number came from a real call.
const KIND_ICON = {
  thought: "",
  tool_call: "",
  tool_result: "",
  message: "",
};

export default function TracePanel({ trace }) {
  return (
    <div className="card trace">
      <h2>Agent trace</h2>
      {(!trace || trace.length === 0) && (
        <p className="hint">Tool calls and results will appear here live.</p>
      )}
      <ol className="trace-list">
        {trace?.map((s) => (
          <li key={s.step} className={`trace-step ${s.kind}`}>
            <div className="trace-head">
              <span className="icon">{KIND_ICON[s.kind] || "•"}</span>
              <span className="kind">{s.tool || s.kind}</span>
            </div>
            {s.summary && <div className="trace-summary">{s.summary}</div>}
            {s.params && (
              <pre className="trace-json">
                params: {JSON.stringify(s.params, null, 2)}
              </pre>
            )}
            {s.result !== undefined && s.result !== null && (
              <pre className="trace-json">
                result: {JSON.stringify(s.result, null, 2)}
              </pre>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}
