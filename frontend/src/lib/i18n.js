// Static UI-label translations for Bangla mode (Tier 2 accessibility).
//
// Scope is deliberate: only fixed UI chrome (headings, buttons, table headers)
// is translated, via this hand-written dictionary — deterministic, no model
// involvement, nothing to garble. Tool DATA (because-strings, crop names,
// numbers in panels, the trace) stays English: it is the inspectable grounding
// a judge cross-checks against the agent trace.
const STR = {
  // ---- top bar + tabs ----
  "tab.crops": ["🌱 Crop options", "🌱 ফসলের বিকল্প"],
  "tab.calendar": ["📅 Season calendar", "📅 মৌসুম পঞ্জিকা"],
  "tab.finance": ["💰 Finance", "💰 আর্থিক হিসাব"],
  "tab.fertilizer": ["🧪 Fertilizer", "🧪 সার ও সেচ"],
  "tab.pests": ["🐛 Pest risk", "🐛 পোকা-রোগের ঝুঁকি"],
  "tab.scenario": ["🔮 What-if", "🔮 যদি এমন হয়"],
  "tab.weather": ["🌦️ Weather alerts", "🌦️ আবহাওয়া সতর্কতা"],
  "tab.market": ["💹 Market", "💹 বাজারদর"],
  "tab.suppliers": ["🛒 Suppliers", "🛒 সরবরাহকারী"],
  "tab.disease": ["🔬 Diagnosis", "🔬 রোগ নির্ণয়"],
  "tab.payment": ["💳 Premium", "💳 প্রিমিয়াম"],
  "top.sessions": ["🗂️ Sessions", "🗂️ সেশন"],
  "top.new": ["↻ New session", "↻ নতুন সেশন"],

  // ---- chat ----
  "chat.title": ["Conversation", "কথোপকথন"],
  "chat.hint": [
    "Try: “I have some land near Rangpur and want to plant something this season.” — or tap 🎤 to speak, or 📷 to diagnose a sick plant.",
    "লিখুন: “রংপুরের কাছে আমার কিছু জমি আছে, এই মৌসুমে কী চাষ করব?” — অথবা 🎤 চেপে মুখে বলুন, বা 📷 দিয়ে অসুস্থ গাছের ছবি দিন।",
  ],
  "chat.thinking": ["thinking…", "ভাবছি…"],
  "chat.placeholder": ["Message AgriSense…", "AgriSense-কে লিখুন…"],
  "chat.listening": ["Listening…", "শুনছি…"],
  "chat.send": ["Send", "পাঠান"],
  "chat.photoTitle": [
    "Upload a crop photo for disease diagnosis",
    "রোগ নির্ণয়ের জন্য ফসলের ছবি দিন",
  ],
  "chat.micTitle": ["Speak your message", "মুখে বলুন"],
  "chat.micStop": ["Listening… tap to stop", "শুনছি… থামাতে চাপুন"],

  // ---- farm profile ----
  "profile.title": ["Farm profile", "খামারের তথ্য"],
  "profile.collected": ["collected", "সংগ্রহ হয়েছে"],
  "profile.location": ["Location", "অবস্থান"],
  "profile.size": ["Farm size (acres)", "জমির পরিমাণ (একর)"],
  "profile.soil": ["Soil type", "মাটির ধরন"],
  "profile.water": ["Water", "সেচের উৎস"],
  "profile.budget": ["Budget (BDT)", "বাজেট (টাকা)"],
  "profile.season": ["Season", "মৌসুম"],

  // ---- crop options ----
  "crops.title": ["Crop options", "ফসলের বিকল্প"],
  "crops.summary": [
    "Crops that don't fit your season, water, or budget were removed, then the rest ranked by how well they suit your farm and their profit after risk.",
    "মৌসুম, পানি বা বাজেটের সাথে না মেলা ফসল বাদ দিয়ে বাকিগুলো আপনার খামারের উপযুক্ততা ও ঝুঁকি-সমন্বিত লাভ অনুযায়ী সাজানো হয়েছে।",
  ],
  "crops.rankFor": ["Rank for:", "সাজান:"],
  "crops.balanced": ["⚖️ Balanced", "⚖️ ভারসাম্য"],
  "crops.profit": ["💰 Most profit", "💰 সর্বোচ্চ লাভ"],
  "crops.safe": ["🛡️ Lowest risk", "🛡️ সর্বনিম্ন ঝুঁকি"],
  "crops.suitability": ["suitability", "উপযুক্ততা"],
  "crops.offseason": ["off-season", "মৌসুম-বহির্ভূত"],
  "crops.risk": ["risk:", "ঝুঁকি:"],
  "crops.acreProfit": ["/acre profit", "/একর লাভ"],
  "crops.beforeDiscount": ["before risk discount", "ঝুঁকি-ছাড়ের আগে"],
  "crops.afford1": ["💡 Budget covers about ", "💡 বাজেটে এই ফসলের প্রায় "],
  "crops.afford2": [
    " acre of this crop — consider a smaller area.",
    " একর সম্ভব — ছোট জমিতে করার কথা ভাবুন।",
  ],
  "crops.pick": ["Plan this crop", "এই ফসলের পরিকল্পনা করুন"],
  "crops.working": ["Working…", "কাজ চলছে…"],
  "crops.ruledOut1": ["Ruled out (", "বাদ পড়েছে ("],
  "crops.ruledOut2": [") — why these don't fit", ") — কেন মিলল না"],
  "crops.how": ["ⓘ How these are ranked", "ⓘ কীভাবে সাজানো হয়েছে"],
  "crops.kb": ["KB sources:", "জ্ঞানভান্ডার সূত্র:"],

  // ---- season plan ----
  "plan.title": ["Season calendar", "মৌসুম পঞ্জিকা"],
  "plan.timeline": ["📋 Timeline", "📋 তালিকা"],
  "plan.calendar": ["🗓️ Calendar", "🗓️ ক্যালেন্ডার"],
  "plan.expand": ["⤢ Expand", "⤢ বড় করুন"],
  "plan.window": ["Sowing window", "বপন সময়"],
  "plan.sow": ["sow", "বপন"],
  "plan.harvest": ["harvest", "ফসল কাটা"],
  "plan.days": ["days", "দিন"],
  "plan.source": ["Calendar source:", "পঞ্জিকার সূত্র:"],
  "plan.legendWindow": ["Sowing window", "বপন সময়"],
  "plan.hoverHint": ["Hover a marked day for its details", "বিস্তারিত দেখতে চিহ্নিত দিনে মাউস রাখুন"],

  // ---- finance ----
  "fin.title": ["Financial projection", "আর্থিক হিসাব"],
  "fin.item": ["Item", "খাত"],
  "fin.qty": ["Qty", "পরিমাণ"],
  "fin.unitCost": ["Unit cost", "একক দর"],
  "fin.totalBdt": ["Total (BDT)", "মোট (টাকা)"],
  "fin.totalCost": ["Total cost", "মোট খরচ"],
  "fin.yield": ["Expected yield", "প্রত্যাশিত ফলন"],
  "fin.revenue": ["Revenue", "আয়"],
  "fin.net": ["Net profit", "নিট মুনাফা"],
  "fin.roi": ["ROI", "ROI"],
  "fin.breakEven": ["Break-even price", "ব্রেক-ইভেন দাম"],
  "fin.assumptions": ["Assumptions:", "অনুমানসমূহ:"],

  // ---- scenario (what-if) ----
  "scen.title": ["🔮 What-if", "🔮 যদি এমন হয়"],
  "scen.metric": ["Metric", "সূচক"],
  "scen.baseline": ["Baseline", "আগে"],
  "scen.scenario": ["Scenario", "পরে"],
  "scen.change": ["Change", "পরিবর্তন"],
  "scen.noChange": ["no change", "অপরিবর্তিত"],
  "scen.resized1": [
    "⚠ The budget no longer funds the full area — the plan is resized to ",
    "⚠ বাজেটে পুরো জমি আর সম্ভব নয় — পরিকল্পনা নতুন আয়তনে: ",
  ],
  "scen.resized2": [" acre.", " একর।"],
  "scen.how": ["How this was calculated", "কীভাবে হিসাব করা হলো"],
  "scen.better": ["Better options under this constraint", "এই সীমার মধ্যে ভালো বিকল্প"],
  "scen.risk": ["risk", "ঝুঁকি"],
  "scen.rainfall": ["Rainfall", "বৃষ্টিপাত"],
  "scen.budget": ["Budget", "বাজেট"],
  "scen.newBudget": ["New budget", "নতুন বাজেট"],
  "scen.price": ["Price", "দাম"],
  "scen.yield": ["Yield", "ফলন"],
  "scen.inputCosts": ["Input costs", "উপকরণ খরচ"],

  // ---- market ----
  "market.title": ["💹 Market price", "💹 বাজারদর"],
  "market.vsLast": ["vs last period", "গত সময়ের তুলনায়"],
  "market.estHarvest": ["Est. harvest", "সম্ভাব্য ফলন"],
  "market.gross": ["Gross at today's price", "আজকের দামে মোট আয়"],
  "market.bdtPer": ["BDT / ", "টাকা / "],

  // ---- suppliers ----
  "sup.title": ["🛒 Where to buy", "🛒 কোথায় কিনবেন"],
  "sup.basket1": ["Fertilizer basket for ", "সারের ঝুড়ি — "],
  "sup.basket2": [" acre:", " একরের জন্য:"],
  "sup.supplier": ["Supplier", "সরবরাহকারী"],
  "sup.basketCost": ["Basket cost", "ঝুড়ির দাম"],
  "sup.delivery": ["Delivery", "ডেলিভারি"],
  "sup.rating": ["Rating", "রেটিং"],
  "sup.distance": ["Distance", "দূরত্ব"],
  "sup.cheapest": ["CHEAPEST", "সবচেয়ে সস্তা"],
  "sup.days": ["day(s)", "দিন"],
  "sup.other": ["Other options:", "অন্যান্য বিকল্প:"],

  // ---- weather alerts ----
  "wa.title": ["🌦️ Weather alerts", "🌦️ আবহাওয়া সতর্কতা"],
  "wa.clear": [
    "✅ No weather conflicts — the forecast is clear for the upcoming plan actions.",
    "✅ আবহাওয়ায় কোনো সংঘাত নেই — সামনের কাজগুলোর জন্য পূর্বাভাস অনুকূল।",
  ],
  "wa.actNow": ["act now", "এখনই করণীয়"],
  "wa.watch": ["watch", "নজর রাখুন"],
  "wa.tip": ["tip", "পরামর্শ"],
  "wa.forecast": ["Forecast:", "পূর্বাভাস:"],
  "wa.planActions1": ["Plan actions inside the forecast window (", "পূর্বাভাস সময়ের মধ্যে পরিকল্পনার কাজ ("],
  "wa.planActions2": [")", ")"],

  // ---- fertilizer ----
  "fert.title": ["🧪 Fertilizer & irrigation", "🧪 সার ও সেচ"],
  "fert.schedule": ["Application schedule", "প্রয়োগ সূচি"],
  "fert.irrigation": ["Irrigation", "সেচ"],
  "fert.seasonTotal": ["Season total by input", "উপকরণ অনুযায়ী মৌসুমি মোট"],
  "fert.input": ["Input", "উপকরণ"],
  "fert.kgPerAcre": ["kg/acre", "কেজি/একর"],
  "fert.kgTotal": ["kg total", "মোট কেজি"],
  "fert.bdtPerKg": ["BDT/kg", "টাকা/কেজি"],
  "fert.cost": ["Cost", "খরচ"],
  "fert.organic": ["🌿 Organic alternative", "🌿 জৈব বিকল্প"],
  "fert.rules": [
    "Weather rules for fertilizer timing (from the knowledge base)",
    "সার প্রয়োগের আবহাওয়া-নিয়ম (জ্ঞানভান্ডার থেকে)",
  ],

  // ---- pest risk ----
  "pest.title": ["🐛 Pest & disease risk", "🐛 পোকা ও রোগের ঝুঁকি"],
  "pest.activeNow": ["Active now", "এখন সক্রিয়"],
  "pest.upcoming1": ["Coming later in the season (", "মৌসুমের পরে আসতে পারে ("],
  "pest.upcoming2": [")", ")"],
  "pest.lookFor": ["Look for:", "লক্ষণ:"],
  "pest.actWhen": ["Act when:", "কখন ব্যবস্থা:"],
  "pest.prevent": ["Prevent", "প্রতিরোধ"],
  "pest.treat": ["Treat", "প্রতিকার"],
  "pest.high": ["High risk", "উচ্চ ঝুঁকি"],
  "pest.watch": ["Watch", "নজর রাখুন"],
  "pest.low": ["Low", "কম"],
  "pest.source": ["Source:", "সূত্র:"],

  // ---- sessions sidebar ----
  "sess.title": ["🗂️ Sessions", "🗂️ সেশনসমূহ"],
  "sess.new": ["+ New", "+ নতুন"],
  "sess.hint": ["Past conversations will appear here.", "আগের কথোপকথন এখানে দেখা যাবে।"],
  "sess.msg": ["msg", "বার্তা"],

  // ---- disease diagnosis ----
  "dz.title": ["🔬 Photo diagnosis", "🔬 ছবি থেকে রোগ নির্ণয়"],
  "dz.confidence": ["confidence", "আস্থা"],
  "dz.kb": ["KB-grounded", "জ্ঞানভান্ডার-ভিত্তিক"],
  "dz.ai": ["AI estimate", "AI অনুমান"],
  "dz.symptoms": ["Visible symptoms", "দৃশ্যমান লক্ষণ"],
  "dz.treatment": ["Treatment", "প্রতিকার"],
  "dz.prevention": ["Prevention (IPM-first)", "প্রতিরোধ (আইপিএম-প্রথম)"],
  "dz.threshold": ["Action threshold", "ব্যবস্থার সীমা"],
  "dz.costAcre": ["Est. cost/acre", "আনুমানিক খরচ/একর"],
  "dz.kbSource": ["KB source:", "জ্ঞানভান্ডার সূত্র:"],
};

const idx = (lang) => (lang === "bn" ? 1 : 0);

/** Translate a UI label. Falls back to English, then to the key itself. */
export function t(lang, key) {
  const entry = STR[key];
  if (!entry) return key;
  return entry[idx(lang)] ?? entry[0];
}

// Month / weekday names for the calendar views (Gregorian, Bangla script).
export const MONTHS_FULL = {
  en: [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
  ],
  bn: [
    "জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন",
    "জুলাই", "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর",
  ],
};
export const MONTHS_SHORT = {
  en: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
  bn: ["জানু", "ফেব্রু", "মার্চ", "এপ্রিল", "মে", "জুন", "জুলাই", "আগস্ট", "সেপ্টে", "অক্টো", "নভে", "ডিসে"],
};
export const WEEKDAYS = {
  en: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
  bn: ["রবি", "সোম", "মঙ্গল", "বুধ", "বৃহ", "শুক্র", "শনি"],
};
