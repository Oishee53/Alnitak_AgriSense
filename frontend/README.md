# AgriSense frontend (Vite + React)

Minimal two-column demo UI: **conversation + season plan + finance** on the left,
the **live agent trace** on the right. Deliberately light on styling — judging
says not to over-invest in UI/UX; the trace panel is the part that scores.

## Run
```bash
npm install
cp .env.example .env     # set VITE_API_BASE (default http://localhost:8000)
npm run dev              # http://localhost:5173
```

## Structure
```
src/
├── App.jsx                 layout + chat/trace state
├── lib/api.js              backend client (chat, trace, SSE, checkout)
├── components/
│   ├── ChatPanel.jsx       farmer conversation + intake follow-ups
│   ├── TracePanel.jsx      visible agent trace (Tier-0 #8)
│   ├── PlanView.jsx        dated season calendar (Tier-0 #4)
│   └── FinanceTable.jsx    itemized financials (Tier-0 #5)
└── styles.css
```

`streamTrace()` in `lib/api.js` is wired for Server-Sent Events; switch the trace
panel from the per-turn snapshot to the live stream once the backend SSE endpoint
is emitting.
