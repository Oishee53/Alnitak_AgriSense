// Deterministic English→Bangla translation of the backend's TEMPLATED data
// strings — translate, not generate. No model is involved anywhere here:
// every backend sentence is assembled from a fixed template + enums + numbers,
// so each template gets a hand-written Bangla counterpart and the numbers /
// names are carried through by regex capture. Anything that matches no known
// pattern falls back to the original English (safe degradation, never garbled).
// Numbers stay in Western digits so they match the agent trace exactly.
//
// The agent trace is deliberately NOT translated — it is the raw, judge-
// verifiable grounding.

// ---------------------------------------------------------------------------
// Crop names (the full 19-crop seed universe). Rendered as "বাংলা (English)"
// so the farmer reads Bangla while the English name stays cross-checkable.
export const CROPS_BN = {
  "T. Aman Rice": "রোপা আমন ধান",
  "Boro Rice": "বোরো ধান",
  "Maize (Kharif)": "ভুট্টা (খরিফ)",
  "Potato": "আলু",
  "Wheat": "গম",
  "Mustard": "সরিষা",
  "Jute": "পাট",
  "Aus Rice": "আউশ ধান",
  "Lentil": "মসুর",
  "Chickpea": "ছোলা",
  "Mungbean": "মুগ",
  "Onion": "পেঁয়াজ",
  "Garlic": "রসুন",
  "Chili": "মরিচ",
  "Tomato": "টমেটো",
  "Brinjal": "বেগুন",
  "Groundnut": "চিনাবাদাম",
  "Sugarcane": "আখ",
  "Sweet Potato": "মিষ্টি আলু",
};

export function cropName(name, lang) {
  if (lang !== "bn" || !name) return name;
  // Bengali-only for low-literacy accessibility (fall back to English only if we
  // have no Bangla name for the crop).
  return CROPS_BN[name] || name;
}

// ---------------------------------------------------------------------------
// Western → Bengali numerals. Applied to every farmer-facing string in Bangla
// mode (NOT the agent trace). Pure character map — the numeric VALUE is
// untouched, only the script changes.
const _W2BN = { "0": "০", "1": "১", "2": "২", "3": "৩", "4": "৪", "5": "৫", "6": "৬", "7": "৭", "8": "৮", "9": "৯" };
export function toBnDigits(s) {
  return String(s).replace(/[0-9]/g, (c) => _W2BN[c]);
}

/** Format any raw value for display: Bengali digits in bn mode, else as-is.
 *  Use for numbers rendered directly in JSX (prices, counts, %, dates). */
export function d(value, lang) {
  if (value == null) return value;
  return lang === "bn" ? toBnDigits(value) : value;
}

// District / place names (proper nouns) — the profile "location" value and
// common location strings. Rendered "বাংলা (English)" so the place stays
// cross-checkable. Falls back to the raw English string if unknown.
const PLACES_BN = {
  Rangpur: "রংপুর", Bogura: "বগুড়া", Bogra: "বগুড়া", Dhaka: "ঢাকা",
  Chattogram: "চট্টগ্রাম", Chittagong: "চট্টগ্রাম", Cumilla: "কুমিল্লা",
  Comilla: "কুমিল্লা", Rajshahi: "রাজশাহী", Khulna: "খুলনা", Sylhet: "সিলেট",
  Barishal: "বরিশাল", Barisal: "বরিশাল", Mymensingh: "ময়মনসিংহ",
  Jashore: "যশোর", Jessore: "যশোর", Dinajpur: "দিনাজপুর", Kurigram: "কুড়িগ্রাম",
  Bandarban: "বান্দরবান", Tangail: "টাঙ্গাইল", Pabna: "পাবনা", Faridpur: "ফরিদপুর",
  Noakhali: "নোয়াখালী", Feni: "ফেনী", Jamalpur: "জামালপুর", Naogaon: "নওগাঁ",
  Natore: "নাটোর", Gaibandha: "গাইবান্ধা", Nilphamari: "নীলফামারী",
  Thakurgaon: "ঠাকুরগাঁও", Panchagarh: "পঞ্চগড়", Lalmonirhat: "লালমনিরহাট",
  Sirajganj: "সিরাজগঞ্জ", Satkhira: "সাতক্ষীরা", Meherpur: "মেহেরপুর",
};
export function placeName(loc, lang) {
  if (lang !== "bn" || !loc) return loc;
  const key = String(loc).trim();
  // Bengali-only; unknown place falls back to the original string.
  return PLACES_BN[key] || key;
}

// Supplier business names (the seeded/mock catalog in data/seed/suppliers.json),
// transliterated to Bangla so the whole supplier panel reads in Bengali.
const SUPPLIERS_BN = {
  "Rangpur Agro Depot": "রংপুর এগ্রো ডিপো",
  "Krishi Bhandar": "কৃষি ভান্ডার",
  "GreenField Inputs": "গ্রিনফিল্ড ইনপুটস",
};
export function supplierName(name, lang) {
  if (lang !== "bn" || !name) return name;
  return SUPPLIERS_BN[String(name).trim()] || name;
}
const _sn = (name) => SUPPLIERS_BN[String(name).trim()] || name;

// ---------------------------------------------------------------------------
// Word/value tokens: enums the backend emits inside sentences and as values.
const TOKENS = {
  // water need / availability
  "low": "কম",
  "low-medium": "কম-মাঝারি",
  "medium": "মাঝারি",
  "high": "বেশি",
  "tubewell": "টিউবওয়েল",
  "rainfed": "বৃষ্টিনির্ভর",
  "canal": "খাল",
  "limited": "সীমিত",
  "reliable": "নির্ভরযোগ্য",
  "unknown": "অজানা",
  // soil
  "sandy": "বেলে",
  "sandy loam": "বেলে-দোআঁশ",
  "loam": "দোআঁশ",
  "clay": "এঁটেল",
  "silt": "পলি",
  // seasons
  "rabi": "রবি",
  "Rabi": "রবি",
  "kharif-1": "খরিফ-1",
  "kharif-2": "খরিফ-2",
  "Kharif-1": "খরিফ-1",
  "Kharif-2": "খরিফ-2",
  "Aman": "আমন",
  "aman": "আমন",
  "Boro": "বোরো",
  "boro": "বোরো",
  "Aus": "আউশ",
  "aus": "আউশ",
  // trend
  "rising": "বাড়ছে",
  "falling": "কমছে",
  "stable": "স্থির",
  // disease severity
  "mild": "মৃদু",
  "moderate": "মাঝারি",
  "severe": "তীব্র",
  // disease condition
  "healthy": "সুস্থ",
  "disease": "রোগ",
  "pest": "পোকা",
  "deficiency": "পুষ্টির অভাব",
  // misc
  "maund": "মণ",
  "acre": "একর",
};

// Display units that appear as bare tokens in JSX (prices, weights, distances,
// fertilizer product codes).
const UNITS = {
  BDT: "টাকা", kg: "কেজি", km: "কিমি", "day(s)": "দিন", days: "দিন",
  UREA: "ইউরিয়া", TSP: "টিএসপি", MOP: "এমওপি", MoP: "এমওপি",
};
export function unit(u, lang) {
  if (lang !== "bn" || u == null) return u;
  return UNITS[String(u)] ?? u;
}

export function tk(value, lang) {
  if (lang !== "bn" || value == null) return value;
  return toBnDigits(TOKENS[String(value)] ?? value);
}

// ---------------------------------------------------------------------------
// Exact-phrase dictionary: finite string sets from the seed data.
const PHRASES = {
  // --- sowing-window labels (all 19 from crop_profiles.json) ---
  "transplant mid-Jul to mid-Aug": "রোপণ: মধ্য জুলাই থেকে মধ্য আগস্ট",
  "transplant early Jan to mid-Feb": "রোপণ: জানুয়ারির শুরু থেকে মধ্য ফেব্রুয়ারি",
  "sow mid-Jun to end-Jul": "বপন: মধ্য জুন থেকে জুলাইয়ের শেষ",
  "plant mid-Nov to mid-Dec": "রোপণ: মধ্য নভেম্বর থেকে মধ্য ডিসেম্বর",
  "sow mid-Nov to early Dec": "বপন: মধ্য নভেম্বর থেকে ডিসেম্বরের শুরু",
  "sow mid-Oct to mid-Nov": "বপন: মধ্য অক্টোবর থেকে মধ্য নভেম্বর",
  "sow mid-Mar to end-Apr": "বপন: মধ্য মার্চ থেকে এপ্রিলের শেষ",
  "direct sow mid-Mar to end-Apr": "সরাসরি বপন: মধ্য মার্চ থেকে এপ্রিলের শেষ",
  "sow late Oct to mid-Nov": "বপন: অক্টোবরের শেষ থেকে মধ্য নভেম্বর",
  "sow late Oct to late Nov": "বপন: অক্টোবরের শেষ থেকে নভেম্বরের শেষ",
  "sow mid-Feb to end-Mar (also after Aman)": "বপন: মধ্য ফেব্রুয়ারি থেকে মার্চের শেষ (আমনের পরেও)",
  "transplant Nov to mid-Dec": "রোপণ: নভেম্বর থেকে মধ্য ডিসেম্বর",
  "plant late Oct to late Nov": "রোপণ: অক্টোবরের শেষ থেকে নভেম্বরের শেষ",
  "transplant mid-Oct to end-Nov": "রোপণ: মধ্য অক্টোবর থেকে নভেম্বরের শেষ",
  "transplant mid-Sep to mid-Nov": "রোপণ: মধ্য সেপ্টেম্বর থেকে মধ্য নভেম্বর",
  "sow Nov to mid-Dec (also Feb-Mar)": "বপন: নভেম্বর থেকে মধ্য ডিসেম্বর (ফেব্রু-মার্চেও)",
  "plant Oct-Nov (autumn) or Feb-Mar": "রোপণ: অক্টোবর-নভেম্বর (শরৎ) বা ফেব্রু-মার্চ",
  "plant mid-Oct to mid-Dec": "রোপণ: মধ্য অক্টোবর থেকে মধ্য ডিসেম্বর",

  // --- stage names (all 41 from crop_profiles.json) ---
  "Disease checkpoint": "রোগ পরিদর্শন",
  "Drain field": "জমির পানি নিষ্কাশন",
  "Earthing + urea": "মাটি তোলা + ইউরিয়া",
  "Fertilizer - basal": "বেসাল (গোড়া) সার",
  "First harvest": "প্রথম ফসল তোলা",
  "Gap filling": "ফাঁক পূরণ",
  "Gypsum at pegging": "পেগিং-এ জিপসাম",
  "Harvest": "ফসল কাটা",
  "Haulm cutting": "গাছ কাটা (হাউম)",
  "Irrigation": "সেচ",
  "Irrigation (optional)": "সেচ (ঐচ্ছিক)",
  "Irrigation 1": "সেচ 1",
  "Irrigation 1 (CRI)": "সেচ 1 (CRI)",
  "Irrigation 2": "সেচ 2",
  "Irrigation 2-3": "সেচ 2-3",
  "Irrigation 3": "সেচ 3",
  "Irrigation critical": "জরুরি সেচ",
  "Land preparation": "জমি তৈরি",
  "Mulching": "মালচিং",
  "Nursery": "বীজতলা",
  "Pest checkpoint": "পোকা পরিদর্শন",
  "Pest/disease checkpoint": "পোকা/রোগ পরিদর্শন",
  "Planting": "রোপণ",
  "Retting": "জাগ দেওয়া",
  "Sowing": "বপন",
  "Staking": "খুঁটি দেওয়া",
  "Stop irrigation": "সেচ বন্ধ",
  "Thinning & weeding": "পাতলাকরণ ও নিড়ানি",
  "Thinning & weeding 1": "পাতলাকরণ ও নিড়ানি 1",
  "Transplanting": "চারা রোপণ",
  "Tying/propping": "বাঁধা/ঠেকনা দেওয়া",
  "Urea top-dress": "ইউরিয়া টপ-ড্রেস",
  "Urea top-dress + earthing": "ইউরিয়া টপ-ড্রেস + মাটি তোলা",
  "Urea top-dress 1": "ইউরিয়া টপ-ড্রেস 1",
  "Urea top-dress 2": "ইউরিয়া টপ-ড্রেস 2",
  "Urea top-dress 3": "ইউরিয়া টপ-ড্রেস 3",
  "Weeding": "নিড়ানি",
  "Weeding & earthing": "নিড়ানি ও মাটি তোলা",
  "Weeding & vine lifting": "নিড়ানি ও লতা তোলা",
  "Weeding 1": "নিড়ানি 1",
  "Weeding 2": "নিড়ানি 2",

  // --- finance cost items (all 12 from crop_economics.json) ---
  "Fertilizer": "সার",
  "Labour": "শ্রম",
  "Labour (incl. retting)": "শ্রম (জাগসহ)",
  "Miscellaneous": "বিবিধ",
  "Pesticide": "কীটনাশক",
  "Seed": "বীজ",
  "Seed (cloves)": "বীজ (কোয়া)",
  "Seed (setts)": "বীজ (সেট)",
  "Seed (tubers)": "বীজ (কন্দ)",
  "Seed (vines)": "বীজ (লতা)",

  // --- scenario metric names (scenario.py deltas) ---
  "Planted area": "রোপণকৃত জমি",
  "Yield per acre": "একরপ্রতি ফলন",
  "Total yield": "মোট ফলন",
  "Price": "দাম",
  "Total cost": "মোট খরচ",
  "Revenue": "আয়",
  "Net profit": "নিট মুনাফা",
  "ROI": "ROI",
  "Break-even price": "ব্রেক-ইভেন দাম",

  // --- market recommendation calls (market.py) ---
  "SELL NOW": "এখনই বিক্রি করুন",
  "SELL SOON": "শিগগিরই বিক্রি করুন",
  "STORE / WAIT": "মজুত করুন / অপেক্ষা করুন",
  "SELL NOW or STORE": "এখনই বিক্রি বা মজুত করুন",

  // --- scenario fixed verdicts ---
  "This scenario turns a profit into a LOSS.": "এই পরিস্থিতিতে লাভ লোকসানে পরিণত হয়।",
  "No change to the bottom line.": "শেষ হিসাবে কোনো পরিবর্তন নেই।",

  // --- disease detection: diagnosis fallbacks + fixed messages (disease.py) ---
  "Unclear": "অস্পষ্ট",
  "Healthy": "সুস্থ",
  "AI photo estimate — confirm with a local agriculture extension officer before applying any chemical.":
    "এআই ছবি-অনুমান — কোনো রাসায়নিক প্রয়োগের আগে স্থানীয় কৃষি সম্প্রসারণ কর্মকর্তার সঙ্গে যাচাই করুন।",
  "That doesn't look like a crop plant — please upload a close-up photo of the affected leaf or plant.":
    "এটি ফসলের গাছ বলে মনে হচ্ছে না — আক্রান্ত পাতা বা গাছের কাছ থেকে তোলা স্পষ্ট ছবি দিন।",
  "could not analyse the image — please try a clearer, well-lit close-up of the affected leaf":
    "ছবিটি বিশ্লেষণ করা গেল না — আক্রান্ত পাতার আরও স্পষ্ট, ভালো আলোয় তোলা ছবি দিন",
};

// ---------------------------------------------------------------------------
// Season-plan stage ACTIONS — the 163 unique per-crop instruction strings from
// crop_profiles.json. Free text, so each is hand-translated (translate, not
// generate). Numbers convert to Bengali digits via localize(); cultivar codes
// (BARI/BRRI/…) are kept for recognisability.
const ACTIONS = {
  "1/2 urea + full TSP, MoP at planting": "রোপণের সময় ১/২ ইউরিয়া + পুরো টিএসপি, এমওপি",
  "1/2 urea + full TSP, MoP, gypsum": "১/২ ইউরিয়া + পুরো টিএসপি, এমওপি, জিপসাম",
  "1/2 urea + full TSP, MoP, gypsum, boron, zinc": "১/২ ইউরিয়া + পুরো টিএসপি, এমওপি, জিপসাম, বোরন, জিংক",
  "1/2 urea + full TSP, MoP, gypsum, zinc, boron": "১/২ ইউরিয়া + পুরো টিএসপি, এমওপি, জিপসাম, জিংক, বোরন",
  "1/3 urea + full TSP, MoP, gypsum": "১/৩ ইউরিয়া + পুরো টিএসপি, এমওপি, জিপসাম",
  "1/3 urea + full TSP, MoP, gypsum, zinc": "১/৩ ইউরিয়া + পুরো টিএসপি, এমওপি, জিপসাম, জিংক",
  "1/3 urea + full TSP, MoP, gypsum, zinc in furrow": "নালায় ১/৩ ইউরিয়া + পুরো টিএসপি, এমওপি, জিপসাম, জিংক",
  "1/3 urea + full TSP, MoP, gypsum, zinc, boron": "১/৩ ইউরিয়া + পুরো টিএসপি, এমওপি, জিপসাম, জিংক, বোরন",
  "1/3 urea after seedling establishment": "চারা লেগে যাওয়ার পর ১/৩ ইউরিয়া",
  "1/3 urea and earthing up": "১/৩ ইউরিয়া ও মাটি তোলা",
  "1/3 urea at active tillering": "ভরা কুশি অবস্থায় ১/৩ ইউরিয়া",
  "1/3 urea at flowering": "ফুল আসার সময় ১/৩ ইউরিয়া",
  "1/3 urea at knee-high (V8), earth up": "হাঁটু-সমান উচ্চতায় (V8) ১/৩ ইউরিয়া, মাটি তোলা",
  "1/3 urea at maximum tillering": "সর্বোচ্চ কুশি অবস্থায় ১/৩ ইউরিয়া",
  "1/3 urea at panicle initiation": "শীষ গঠন শুরুতে ১/৩ ইউরিয়া",
  "1/3 urea at tillering": "কুশি অবস্থায় ১/৩ ইউরিয়া",
  "1/3 urea at vegetative growth": "কাণ্ড-পাতা বৃদ্ধির সময় ১/৩ ইউরিয়া",
  "1/3 urea before tasseling": "মোচা আসার আগে ১/৩ ইউরিয়া",
  "1/3 urea; keep 2-3 cm standing water": "১/৩ ইউরিয়া; ২-৩ সেমি দাঁড়ানো পানি রাখুন",
  "2-3 ploughings with residual moisture": "রস থাকতে ২-৩ বার চাষ",
  "2-3 ploughings; make drainage furrows": "২-৩ বার চাষ; পানি নিষ্কাশনের নালা করুন",
  "2/3 urea + full TSP, MoP, gypsum, boron": "২/৩ ইউরিয়া + পুরো টিএসপি, এমওপি, জিপসাম, বোরন",
  "60x20 cm spacing, 1 seed/hill, 8-9 kg/acre hybrid seed": "৬০x২০ সেমি দূরত্ব, প্রতি গর্তে ১টি বীজ, ৮-৯ কেজি/একর হাইব্রিড বীজ",
  "Anthracnose fruit rot watch in wet weather; spray as needed": "ভেজা আবহাওয়ায় অ্যানথ্রাকনোজ ফল-পচা নজরে রাখুন; প্রয়োজনে স্প্রে",
  "Aphid colonies on inflorescence; spray only past threshold": "মঞ্জরিতে জাব পোকার ঝাঁক; সীমা ছাড়ালে তবেই স্প্রে",
  "Aphid scouting at podding": "শুঁটি ধরার সময় জাব পোকা পর্যবেক্ষণ",
  "Apply full TSP, MoP and gypsum at final land preparation": "শেষ জমি তৈরির সময় পুরো টিএসপি, এমওপি ও জিপসাম দিন",
  "Booting stage irrigation": "থোড় অবস্থায় সেচ",
  "Botrytis grey mould watch in cloudy humid spells": "মেঘলা আর্দ্র সময়ে বোট্রাইটিস ধূসর ছাতা নজরে রাখুন",
  "Broadcast/line sow 15 kg/acre (BARI Masur-6/8)": "ছিটিয়ে/সারিতে ১৫ কেজি/একর বপন (বারি মসুর-৬/৮)",
  "Broadcast/line sow 3 kg/acre (BARI Sarisha-14/17)": "ছিটিয়ে/সারিতে ৩ কেজি/একর বপন (বারি সরিষা-১৪/১৭)",
  "Coarse tilth on residual moisture; do not over-pulverize": "রস থাকতে মোটা করে চাষ; বেশি ঝুরঝুরে করবেন না",
  "Crown root initiation irrigation — most critical": "ক্রাউন রুট গঠনের সেচ — সবচেয়ে গুরুত্বপূর্ণ",
  "Cut at small pod stage for best fibre": "ভালো আঁশের জন্য ছোট শুঁটি অবস্থায় কাটুন",
  "Cut haulms to harden skin": "খোসা শক্ত করতে গাছ কেটে দিন",
  "Deep ploughing; open furrows 90-120 cm apart": "গভীর চাষ; ৯০-১২০ সেমি দূরে দূরে নালা করুন",
  "Dibble healthy cloves 10x10 cm, tip up (BARI Rosun-1/3/4)": "সুস্থ কোয়া ১০x১০ সেমি দূরত্বে আগা উপরে করে পুঁতুন (বারি রসুন-১/৩/৪)",
  "Direct broadcast/line sow 12-15 kg/acre (BRRI dhan48/98)": "সরাসরি ছিটিয়ে/সারিতে ১২-১৫ কেজি/একর বপন (ব্রি ধান৪৮/৯৮)",
  "Drain 10-15 days before harvest": "ফসল কাটার ১০-১৫ দিন আগে পানি নিষ্কাশন",
  "Drain before harvest": "ফসল কাটার আগে পানি নিষ্কাশন",
  "Dry ploughing 2-3 times before pre-monsoon showers": "প্রাক-বর্ষার বৃষ্টির আগে ২-৩ বার শুকনা চাষ",
  "Fall armyworm scouting in whorls; hand-pick egg masses": "পাতার গোড়ায় ফল আর্মিওয়ার্ম পর্যবেক্ষণ; হাতে ডিমের গাদা সংগ্রহ",
  "Fill gaps to keep full stand": "পূর্ণ চারা রাখতে ফাঁক পূরণ করুন",
  "Final 1/3 urea before grand growth": "দ্রুত বৃদ্ধির আগে শেষ ১/৩ ইউরিয়া",
  "Fine tilth on residual moisture after Aman": "আমনের পর রস থাকতে ঝুরঝুরে চাষ",
  "Fine tilth or zero-till dibbling on soft moist soil": "নরম রসালো মাটিতে ঝুরঝুরে চাষ বা বিনা চাষে পুঁতুন",
  "Fine tilth; 2-3 ploughings": "ঝুরঝুরে চাষ; ২-৩ বার চাষ",
  "Fine tilth; raised beds; cowdung 4 t/acre": "ঝুরঝুরে চাষ; উঁচু বেড; গোবর ৪ টন/একর",
  "Fine tilth; ridges 60 cm apart; cowdung 4 t/acre": "ঝুরঝুরে চাষ; ৬০ সেমি দূরে আইল; গোবর ৪ টন/একর",
  "Fine tilth; ridges/beds with good drainage": "ঝুরঝুরে চাষ; ভালো নিষ্কাশনসহ আইল/বেড",
  "Fine tilth; ridges; cowdung 4 t/acre": "ঝুরঝুরে চাষ; আইল; গোবর ৪ টন/একর",
  "First pick at breaker stage": "রং ধরার শুরুতে প্রথম তোলা",
  "First pick of glossy tender fruit": "চকচকে কচি ফলের প্রথম তোলা",
  "First pick of mature dry pods": "পরিপক্ক শুকনা শুঁটির প্রথম তোলা",
  "First pick of mature green/red fruit": "পরিপক্ক সবুজ/লাল ফলের প্রথম তোলা",
  "First weeding and earthing up": "প্রথম নিড়ানি ও মাটি তোলা",
  "First weeding at tillering": "কুশি অবস্থায় প্রথম নিড়ানি",
  "First weeding; keep beds clean": "প্রথম নিড়ানি; বেড পরিষ্কার রাখুন",
  "First weeding; thin dense patches": "প্রথম নিড়ানি; ঘন জায়গা পাতলা করুন",
  "Full TSP, MoP, gypsum, zinc at final prep": "শেষ জমি তৈরিতে পুরো টিএসপি, এমওপি, জিপসাম, জিংক",
  "Full urea (light), TSP, MoP, gypsum, boron at sowing": "বপনে পুরো ইউরিয়া (অল্প), টিএসপি, এমওপি, জিপসাম, বোরন",
  "Grain filling irrigation": "দানা ভরাট অবস্থায় সেচ",
  "Hairy caterpillar — collect egg-mass leaves": "লোমশ শুঁয়াপোকা — ডিমের গাদাসহ পাতা সংগ্রহ করুন",
  "Hand weeding or rotary weeder": "হাতে নিড়ানি বা রোটারি উইডার",
  "Hand weeding; avoid damaging shallow roots": "হাতে নিড়ানি; অগভীর শিকড়ের ক্ষতি এড়ান",
  "Harvest April-May before pre-monsoon hail": "প্রাক-বর্ষার শিলাবৃষ্টির আগে এপ্রিল-মে-তে ফসল কাটুন",
  "Harvest Jul-Aug at 80% ripening before monsoon flood": "বর্ষার বন্যার আগে ৮০% পাকলে জুলাই-আগস্টে ফসল কাটুন",
  "Harvest at 80% golden grain; dry to 14% moisture": "৮০% দানা সোনালি হলে কাটুন; ১৪% আর্দ্রতায় শুকান",
  "Harvest at maturity; deliver to mill/gur promptly": "পরিপক্ক হলে কাটুন; দ্রুত মিল/গুড়ে পৌঁছান",
  "Harvest mid-March before heat stress": "তাপ-চাপের আগে মধ্য মার্চে ফসল কাটুন",
  "Harvest when 50-70% tops fall; cure in shade before storage": "৫০-৭০% গাছ নুয়ে পড়লে কাটুন; সংরক্ষণের আগে ছায়ায় শুকান",
  "Harvest when 75-80% siliquae turn straw colour": "৭৫-৮০% ফল খড়ের রং ধরলে কাটুন",
  "Harvest when 80% pods turn brown": "৮০% শুঁটি বাদামি হলে কাটুন",
  "Harvest when husks dry and black layer forms": "খোসা শুকিয়ে কালো স্তর পড়লে কাটুন",
  "Harvest when inner shell veins darken; dry pods well": "ভেতরের খোলার শিরা কালচে হলে কাটুন; শুঁটি ভালো শুকান",
  "Harvest when leaves yellow; cure roots before storage": "পাতা হলুদ হলে কাটুন; সংরক্ষণের আগে কন্দ শুকান",
  "Harvest when plants yellow and pods dry": "গাছ হলুদ ও শুঁটি শুকালে কাটুন",
  "Harvest when tops dry; cure and bundle for storage": "গাছ শুকালে কাটুন; শুকিয়ে আঁটি বেঁধে রাখুন",
  "Harvest, cure in shade, grade before storage": "কাটুন, ছায়ায় শুকান, সংরক্ষণের আগে বাছাই করুন",
  "Irrigation at pegging and pod fill if dry": "শুকনা হলে পেগিং ও শুঁটি ভরাটে সেচ",
  "Late blight watch in fog; prophylactic mancozeb": "কুয়াশায় নাবি ধসা নজরে রাখুন; প্রতিরোধে ম্যানকোজেব",
  "Late blight watch when night fog + 10-20°C; prophylactic mancozeb": "রাতে কুয়াশা + ১০-২০°C হলে নাবি ধসা নজরে রাখুন; প্রতিরোধে ম্যানকোজেব",
  "Leaf blight/purple blotch watch in humid spells": "আর্দ্র সময়ে পাতা ধসা/বেগুনি দাগ নজরে রাখুন",
  "Light irrigation at stolon initiation": "স্টোলন গঠনের সময় হালকা সেচ",
  "Light irrigation every 10-12 days during bulb growth": "কন্দ বৃদ্ধির সময় প্রতি ১০-১২ দিনে হালকা সেচ",
  "Light irrigation every 8-10 days during bulbing": "কন্দ গঠনের সময় প্রতি ৮-১০ দিনে হালকা সেচ",
  "Light urea + full TSP, MoP, gypsum at sowing": "বপনে অল্প ইউরিয়া + পুরো টিএসপি, এমওপি, জিপসাম",
  "Light urea + full TSP, MoP, gypsum, boron at sowing": "বপনে অল্প ইউরিয়া + পুরো টিএসপি, এমওপি, জিপসাম, বোরন",
  "Line sow 12-14 kg/acre (BARI Chola-5/9/10)": "সারিতে ১২-১৪ কেজি/একর বপন (বারি ছোলা-৫/৯/১০)",
  "Line sow 2.5-3 kg/acre (O-9897 / Robi-1)": "সারিতে ২.৫-৩ কেজি/একর বপন (O-৯৮৯৭ / রবি-১)",
  "Line sow 40-48 kg/acre in-shell (BARI Chinabadam-8/9)": "খোসাসহ সারিতে ৪০-৪৮ কেজি/একর বপন (বারি চিনাবাদাম-৮/৯)",
  "Line sow 5-6 kg/acre (BARI Mug-6/8)": "সারিতে ৫-৬ কেজি/একর বপন (বারি মুগ-৬/৮)",
  "Line sowing 20 cm rows, 48-50 kg/acre seed": "২০ সেমি সারিতে বপন, ৪৮-৫০ কেজি/একর বীজ",
  "Loose fine tilth (light soils ideal)": "আলগা ঝুরঝুরে চাষ (হালকা মাটি আদর্শ)",
  "Low urea + full TSP, MoP, half gypsum at sowing": "বপনে কম ইউরিয়া + পুরো টিএসপি, এমওপি, অর্ধেক জিপসাম",
  "Make ridges/mounds 60 cm apart on loose soil": "আলগা মাটিতে ৬০ সেমি দূরে আইল/ঢিবি করুন",
  "Multiple pickings; dry red chili if selling dry": "একাধিকবার তোলা; শুকনা বিক্রি করলে লাল মরিচ শুকান",
  "Multiple pickings; sell staggered to avoid glut price": "একাধিকবার তোলা; দর-পতন এড়াতে ভাগে ভাগে বিক্রি করুন",
  "No stress at tasseling-silking if dry spell": "খরা হলে মোচা-সিল্ক অবস্থায় পানির টান দেবেন না",
  "No water stress from booting to grain fill": "থোড় থেকে দানা ভরাট পর্যন্ত পানির টান নয়",
  "One hand weeding": "একবার হাতে নিড়ানি",
  "One light irrigation at flowering if soil very dry": "মাটি খুব শুকনা হলে ফুল আসার সময় একবার হালকা সেচ",
  "One light irrigation at siliqua fill if dry": "শুকনা হলে ফল ভরাটে একবার হালকা সেচ",
  "One weeding at branching": "ডাল ছাড়ার সময় একবার নিড়ানি",
  "One weeding at early branching": "প্রথম ডাল ছাড়ার সময় একবার নিড়ানি",
  "Pick every 4-5 days over a long season": "লম্বা মৌসুম জুড়ে প্রতি ৪-৫ দিনে তোলা",
  "Plant 25-30 cm vine cuttings on ridges (BARI Mishti Alu varieties)": "আইলে ২৫-৩০ সেমি লতার কাটিং রোপণ (বারি মিষ্টি আলু জাত)",
  "Plant 3-budded setts end to end in furrows (BSRI Ganda varieties)": "নালায় ৩-চোখওয়ালা সেট মাথায়-মাথায় রোপণ (বিএসআরআই গাদা জাত)",
  "Plough 2-3 times, puddle, level; incorporate cowdung 2 t/acre": "২-৩ বার চাষ, কাদা করে সমান; গোবর ২ টন/একর মেশান",
  "Pod borer — pheromone traps, spray at flowering/podding if past threshold": "শুঁটি ছিদ্রকারী পোকা — ফেরোমন ফাঁদ, সীমা ছাড়ালে ফুল/শুঁটির সময় স্প্রে",
  "Puddle and level; ensure irrigation channel": "কাদা করে সমান করুন; সেচের নালা নিশ্চিত করুন",
  "Raise seedlings 28-30 days before transplant": "রোপণের ২৮-৩০ দিন আগে চারা তৈরি করুন",
  "Raise seedlings 35-40 days before transplant": "রোপণের ৩৫-৪০ দিন আগে চারা তৈরি করুন",
  "Raise seedlings in raised beds 30-35 days before transplant": "রোপণের ৩০-৩৫ দিন আগে উঁচু বেডে চারা তৈরি করুন",
  "Remaining 1/2 urea after weeding": "নিড়ানির পর বাকি ১/২ ইউরিয়া",
  "Remaining 1/2 urea and earthing up": "বাকি ১/২ ইউরিয়া ও মাটি তোলা",
  "Remaining 1/2 urea at bulb initiation": "কন্দ গঠনের শুরুতে বাকি ১/২ ইউরিয়া",
  "Remaining 1/2 urea at bulbing": "কন্দ গঠনের সময় বাকি ১/২ ইউরিয়া",
  "Remaining 1/2 urea before flowering, with irrigation if dry": "ফুল আসার আগে বাকি ১/২ ইউরিয়া, শুকনা হলে সেচসহ",
  "Remaining 1/2 urea in 2 splits from flowering": "ফুল আসার পর থেকে ২ কিস্তিতে বাকি ১/২ ইউরিয়া",
  "Remaining 1/2 urea; earth up ridges": "বাকি ১/২ ইউরিয়া; আইলে মাটি তুলুন",
  "Remaining 1/3 urea right after CRI irrigation": "সিআরআই সেচের পরপরই বাকি ১/৩ ইউরিয়া",
  "Remaining gypsum at pegging for pod fill (calcium)": "শুঁটি ভরাটের জন্য পেগিংয়ে বাকি জিপসাম (ক্যালসিয়াম)",
  "Remaining urea in splits through the harvest period": "ফসল তোলার সময় জুড়ে কিস্তিতে বাকি ইউরিয়া",
  "Replace failed cuttings": "মরা কাটিং বদলে দিন",
  "Ret in clean slow water 12-15 days; strip and dry": "পরিষ্কার ধীর পানিতে ১২-১৫ দিন জাগ দিন; আঁশ ছাড়িয়ে শুকান",
  "Scout for stem borer dead-hearts and leaf folder; perching": "মাজরা পোকার মরা-ডগা ও পাতা মোড়ানো পোকা খুঁজুন; ডালপালা পুঁতুন",
  "Second weeding": "দ্বিতীয় নিড়ানি",
  "Second weeding before top-dress": "টপ-ড্রেসের আগে দ্বিতীয় নিড়ানি",
  "Second/final pick when pods blacken": "শুঁটি কালো হলে দ্বিতীয়/শেষ তোলা",
  "Shoot & fruit borer — pheromone traps, clip infested shoots weekly": "ডগা ও ফল ছিদ্রকারী পোকা — ফেরোমন ফাঁদ, প্রতি সপ্তাহে আক্রান্ত ডগা কেটে ফেলুন",
  "Single fine tilth; quick turnaround crop": "একবার ঝুরঝুরে চাষ; দ্রুত মেয়াদি ফসল",
  "Stake plants; begin tying": "গাছে খুঁটি দিন; বাঁধা শুরু করুন",
  "Stem borer and rice bug scouting": "মাজরা পোকা ও ধানের গান্ধি পোকা পর্যবেক্ষণ",
  "Stem borer, BPH scouting at base of hills": "গোছার গোড়ায় মাজরা পোকা, বাদামি গাছফড়িং পর্যবেক্ষণ",
  "Stem/top borer — remove dead-hearts, release Trichogramma": "মাজরা/ডগা পোকা — মরা-ডগা তুলে ফেলুন, ট্রাইকোগ্রামা ছাড়ুন",
  "Stemphylium blight watch in fog; spray mancozeb if needed": "কুয়াশায় স্টেমফাইলিয়াম ধসা নজরে রাখুন; দরকারে ম্যানকোজেব স্প্রে",
  "Stop watering to harden bulbs": "কন্দ শক্ত করতে পানি দেওয়া বন্ধ করুন",
  "Stop watering to mature bulbs": "কন্দ পরিপক্ক করতে পানি দেওয়া বন্ধ করুন",
  "Straw mulch to conserve moisture and suppress weeds": "রস ধরে রাখতে ও আগাছা দমাতে খড়ের মালচ",
  "Thin to 5 cm plant spacing": "৫ সেমি দূরত্বে পাতলা করুন",
  "Thin to 7-8 cm; first weeding": "৭-৮ সেমি দূরত্বে পাতলা করুন; প্রথম নিড়ানি",
  "Thin to one plant/hill; first weeding": "প্রতি গর্তে একটি গাছ রাখুন; প্রথম নিড়ানি",
  "Thrips and purple blotch — spray if past threshold": "থ্রিপস ও বেগুনি দাগ — সীমা ছাড়ালে স্প্রে",
  "Thrips/mite (leaf curl) — spray if leaves cup/curl": "থ্রিপস/মাইট (পাতা কোঁকড়ানো) — পাতা কুঁকড়ে গেলে স্প্রে",
  "Tie canes to prevent lodging in storms": "ঝড়ে হেলে পড়া রোধে আখ বেঁধে দিন",
  "Tikka leaf spot watch; spray if spotting spreads": "টিক্কা পাতার দাগ নজরে রাখুন; দাগ ছড়ালে স্প্রে",
  "Transplant 25-30 day seedlings, 2-3 per hill, 20x15 cm spacing": "২৫-৩০ দিনের চারা রোপণ, প্রতি গর্তে ২-৩টি, ২০x১৫ সেমি দূরত্বে",
  "Transplant 35-40 day seedlings (older for cold)": "৩৫-৪০ দিনের চারা রোপণ (ঠান্ডায় আরও বড়)",
  "Transplant 40-45 day seedlings 10x10 cm (BARI Peyaj-1/4)": "৪০-৪৫ দিনের চারা ১০x১০ সেমি দূরত্বে রোপণ (বারি পেঁয়াজ-১/৪)",
  "Transplant 60x40 cm (BARI Tomato-14/15 or hybrids)": "৬০x৪০ সেমি দূরত্বে রোপণ (বারি টমেটো-১৪/১৫ বা হাইব্রিড)",
  "Transplant 75x60 cm (BARI Begun varieties)": "৭৫x৬০ সেমি দূরত্বে রোপণ (বারি বেগুন জাত)",
  "Transplant seedlings 50x40 cm (BARI Morich-1/3)": "চারা ৫০x৪০ সেমি দূরত্বে রোপণ (বারি মরিচ-১/৩)",
  "Tuber bulking irrigations; stop 10 days pre-harvest": "কন্দ বৃদ্ধির সেচ; ফসল কাটার ১০ দিন আগে বন্ধ",
  "Watch BLB/blast at booting; avoid excess N": "থোড় অবস্থায় বিএলবি/ব্লাস্ট নজরে রাখুন; বেশি নাইট্রোজেন এড়ান",
  "Weed and lift vines to stop rooting at nodes": "নিড়ানি করুন ও গিঁটে শিকড় ঠেকাতে লতা তুলে দিন",
  "Weed and loosen soil for peg entry": "নিড়ানি করুন ও পেগ ঢোকার জন্য মাটি আলগা করুন",
  "Weed before second top-dress": "দ্বিতীয় টপ-ড্রেসের আগে নিড়ানি",
  "Weevil — keep ridges earthed; avoid soil cracks": "উইভিল পোকা — আইলে মাটি তুলে রাখুন; মাটি ফাটতে দেবেন না",
  "Wheat blast watch if Feb is warm and humid": "ফেব্রুয়ারি গরম ও আর্দ্র হলে গমের ব্লাস্ট নজরে রাখুন",
  "Whitefly (leaf curl) and fruit borer — pheromone traps": "সাদা মাছি (পাতা কোঁকড়ানো) ও ফল ছিদ্রকারী পোকা — ফেরোমন ফাঁদ",
  "Whitefly (yellow mosaic) and thrips scouting": "সাদা মাছি (হলুদ মোজাইক) ও থ্রিপস পর্যবেক্ষণ",
  "Whole/cut seed tubers 25 cm apart on ridges": "গোটা/কাটা বীজ কন্দ আইলে ২৫ সেমি দূরে দূরে",
};

// ---------------------------------------------------------------------------
// Pest / disease reference free-text (symptoms, thresholds, prevention bullets,
// treatments, cost-basis notes) from pest_reference.json. Hand-translated;
// chemical + cultivar names kept in Latin for the dealer/farmer to recognise.
const PEST = {
  // pest / disease NAMES
  "Blast": "ব্লাস্ট", "Stem borer": "মাজরা পোকা", "Brown planthopper (BPH)": "বাদামি গাছফড়িং (BPH)",
  "Sheath blight": "শীথ ব্লাইট", "Bacterial leaf blight (BLB)": "ব্যাকটেরিয়াল লিফ ব্লাইট (BLB)",
  "Yellow stem borer": "হলুদ মাজরা পোকা", "Rice bug": "ধানের গান্ধি পোকা", "Leaf folder": "পাতা মোড়ানো পোকা",
  "Late blight": "নাবি ধসা", "Early blight": "আগাম ধসা", "Aphid": "জাব পোকা", "Aphids": "জাব পোকা",
  "Whitefly": "সাদা মাছি", "Thrips": "থ্রিপস", "Fall armyworm": "ফল আর্মিওয়ার্ম",
  "Shoot & fruit borer": "ডগা ও ফল ছিদ্রকারী পোকা", "Fruit borer": "ফল ছিদ্রকারী পোকা",
  "Pod borer": "শুঁটি ছিদ্রকারী পোকা", "Yellow mosaic virus": "হলুদ মোজাইক ভাইরাস",
  "Leaf curl virus": "পাতা কোঁকড়ানো ভাইরাস", "Tikka leaf spot": "টিক্কা পাতার দাগ",
  "Stemphylium blight": "স্টেমফাইলিয়াম ব্লাইট", "Purple blotch": "বেগুনি দাগ",
  "Botrytis grey mould": "বোট্রাইটিস ধূসর ছাতা", "Anthracnose": "অ্যানথ্রাকনোজ",
  "Wheat blast": "গমের ব্লাস্ট", "Top borer": "ডগা ছিদ্রকারী পোকা", "Sweet potato weevil": "মিষ্টি আলুর উইভিল",
  "Hairy caterpillar": "লোমশ শুঁয়াপোকা", "Mite": "মাইট", "Red spider mite": "লাল মাকড়সা মাইট",
  // symptoms
  "Bright yellow mosaic mottling on leaves": "পাতায় উজ্জ্বল হলুদ মোজাইক ছোপ",
  "Bore holes in fruit": "ফলে ছিদ্র",
  "Bleached spikes above the flag leaf": "ফ্ল্যাগ পাতার উপরে সাদা হয়ে যাওয়া শীষ",
  "Colonies at podding": "শুঁটি ধরার সময় পোকার ঝাঁক",
  "Colonies on shoots and pods": "ডগা ও শুঁটিতে পোকার ঝাঁক",
  "Dark leaf spots spreading in humid weather": "আর্দ্র আবহাওয়ায় ছড়ানো গাঢ় পাতার দাগ",
  "Dead-hearts at tillering, white-heads at heading": "কুশি অবস্থায় মরা-ডগা, শীষে সাদা-ডগা",
  "Dead-hearts in young canes; bored top shoots": "কচি আখে মরা-ডগা; ছিদ্রযুক্ত ডগা",
  "Diamond-shaped lesions on leaves and neck": "পাতা ও গলায় হীরক-আকৃতির দাগ",
  "Gregarious larvae skeletonize the leaves": "দলবদ্ধ লার্ভা পাতা কঙ্কাল করে ফেলে",
  "Grey fuzzy mould on stems and flowers in wet years": "ভেজা বছরে কাণ্ড ও ফুলে ধূসর ছাতা",
  "Hopper-burn patches from field centre": "মাঠের মাঝ থেকে হপার-বার্ন দাগ",
  "Hopper-burn patches spreading from the field centre": "মাঠের মাঝ থেকে ছড়ানো হপার-বার্ন দাগ",
  "Larvae boring into flowers and pods": "ফুল ও শুঁটিতে ঢুকে পড়া লার্ভা",
  "Leaf lesions spreading in humid weather": "আর্দ্র আবহাওয়ায় ছড়ানো পাতার দাগ",
  "Leaves cup and curl upward or downward": "পাতা উপরে বা নিচে কুঁকড়ে যায়",
  "Purple-centred leaf lesions": "বেগুনি-কেন্দ্রের পাতার দাগ",
  "Ragged whorl feeding with sawdust-like frass": "করাত-গুঁড়ার মতো বিষ্ঠাসহ ছেঁড়া পাতা",
  "Rapidly spreading leaf lesions in foggy cloudy spells": "কুয়াশা-মেঘলা সময়ে দ্রুত ছড়ানো পাতার দাগ",
  "Silvered, distorted leaves and flower drop": "রুপালি বিকৃত পাতা ও ফুল ঝরা",
  "Silvery streaks on leaves, stunted bulbs": "পাতায় রুপালি দাগ, খর্ব কন্দ",
  "Sucked, discoloured and empty grains at milk stage": "দুধ অবস্থায় চোষা, বিবর্ণ ও ফাঁপা দানা",
  "Sudden wilting of healthy-looking plants": "সুস্থ-দেখতে গাছের হঠাৎ ঢলে পড়া",
  "Sunken dark lesions on ripening fruit": "পাকা ফলে দেবে যাওয়া গাঢ় দাগ",
  "Tunnelled roots with a bitter taste": "সুড়ঙ্গযুক্ত তেতো স্বাদের শিকড়",
  "Upward-curling, stunted leaves; whiteflies on the underside": "উপরে কোঁকড়ানো খর্ব পাতা; নিচে সাদা মাছি",
  "Water-soaked leaf lesions with white mould on the under-surface": "নিচে সাদা ছাতাসহ পানি-ভেজা পাতার দাগ",
  "Water-soaked lesions spreading fast in fog": "কুয়াশায় দ্রুত ছড়ানো পানি-ভেজা দাগ",
  "Wilting shoot tips and bored fruit": "ঢলে পড়া ডগা ও ছিদ্রযুক্ত ফল",
  "Yellow wavy leaf edges, appearing after storms": "ঝড়ের পর হলুদ ঢেউখেলানো পাতার কিনারা",
  // thresholds
  "10% dead-hearts": "১০% মরা-ডগা",
  "10% infested plants": "১০% আক্রান্ত গাছ",
  "Act in humid spells": "আর্দ্র সময়ে ব্যবস্থা নিন",
  "Act in prolonged cloudy humid spells": "দীর্ঘ মেঘলা আর্দ্র সময়ে ব্যবস্থা নিন",
  "Any spread after a storm": "ঝড়ের পর যেকোনো বিস্তার",
  "Colonies on shoots and pods ": "ডগা ও শুঁটিতে পোকার ঝাঁক",
  "Outbreak only": "শুধু প্রাদুর্ভাব হলে",
  "Scout at flowering": "ফুল আসার সময় পর্যবেক্ষণ",
  "Scout at flowering per the crop calendar": "ফসল পঞ্জিকা অনুযায়ী ফুল আসার সময় পর্যবেক্ষণ",
  "Scout at flowering/milk stage": "ফুল/দুধ অবস্থায় পর্যবেক্ষণ",
  "Scout at podding": "শুঁটি ধরার সময় পর্যবেক্ষণ",
  "Scout base of hills weekly after 45 DAT": "রোপণের ৪৫ দিন পর প্রতি সপ্তাহে গোছার গোড়া পর্যবেক্ষণ",
  "Scout from 20 DAS": "বপনের ২০ দিন পর থেকে পর্যবেক্ষণ",
  "Scout from 30 DAS": "বপনের ৩০ দিন পর থেকে পর্যবেক্ষণ",
  "Scout from 45 DAS": "বপনের ৪৫ দিন পর থেকে পর্যবেক্ষণ",
  "Scout from 55 DAS": "বপনের ৫৫ দিন পর থেকে পর্যবেক্ষণ",
  "Scout inflorescences from 30 DAS": "বপনের ৩০ দিন পর থেকে মঞ্জরি পর্যবেক্ষণ",
  "Scout weekly": "প্রতি সপ্তাহে পর্যবেক্ষণ",
  "Trap catches rising": "ফাঁদে বাড়তে থাকা পোকা",
  "~50 aphids/plant on 10% of plants": "১০% গাছে গাছপ্রতি ~৫০টি জাব পোকা",
  "Can destroy a crop in 5–7 days — act at first lesion": "৫–৭ দিনে ফসল নষ্ট করতে পারে — প্রথম দাগেই ব্যবস্থা নিন",
  // prevention bullets
  "Avoid BRRI dhan28 in blast-prone years (highly susceptible)": "ব্লাস্ট-প্রবণ বছরে BRRI dhan28 এড়ান (খুব স্পর্শকাতর)",
  "Avoid continuous standing water": "একটানা দাঁড়ানো পানি এড়ান",
  "Avoid dense over-irrigated canopy": "ঘন ও অতিসেচিত ঝোপ এড়ান",
  "Avoid dense stands": "ঘন গাছ এড়ান",
  "Avoid excess nitrogen": "বেশি নাইট্রোজেন এড়ান",
  "Avoid excess urea": "বেশি ইউরিয়া এড়ান",
  "Avoid excess urea (dense canopy favours BPH)": "বেশি ইউরিয়া এড়ান (ঘন ঝোপ BPH-কে টানে)",
  "Avoid letting the soil dry and crack open": "মাটি শুকিয়ে ফাটতে দেবেন না",
  "Avoid overhead irrigation late in the day": "দিনের শেষে উপর থেকে সেচ এড়ান",
  "Avoid overhead watering late": "শেষ বিকেলে উপর থেকে পানি এড়ান",
  "Avoid water stress": "পানির টান এড়ান",
  "Bird perches": "পাখি বসার খুঁটি",
  "Clip seedling tips": "চারার আগা কেটে দিন",
  "Clip seedling tips before transplanting": "রোপণের আগে চারার আগা কেটে দিন",
  "Conserve ladybird beetles — they control early colonies": "লেডিবার্ড পোকা রক্ষা করুন — এরা প্রথম দিকের ঝাঁক দমন করে",
  "Conserve natural enemies": "প্রাকৃতিক শত্রু রক্ষা করুন",
  "Control the vector early": "বাহক পোকা আগেভাগে দমন করুন",
  "Control whitefly vector early": "সাদা মাছি বাহক আগেভাগে দমন করুন",
  "Crop rotation": "ফসল আবর্তন",
  "Ensure drainage": "পানি নিষ্কাশন নিশ্চিত করুন",
  "Ensure drainage on raised beds": "উঁচু বেডে পানি নিষ্কাশন নিশ্চিত করুন",
  "Ensure drainage — the KB names waterlogged soil as the trigger": "পানি নিষ্কাশন নিশ্চিত করুন — জ্ঞানভান্ডার মতে জলাবদ্ধ মাটিই কারণ",
  "Hand-crush egg masses": "হাতে ডিমের গাদা পিষে ফেলুন",
  "Install bird perches over the field": "মাঠে পাখি বসার খুঁটি বসান",
  "Keep beds weed-free": "বেড আগাছামুক্ত রাখুন",
  "Keep bunds weed-free": "আইল আগাছামুক্ত রাখুন",
  "Keep ridges earthed up so soil does not crack": "মাটি যেন না ফাটে তাই আইলে মাটি তুলে রাখুন",
  "Light traps": "আলোক ফাঁদ",
  "Light traps to catch moths": "মথ ধরতে আলোক ফাঁদ",
  "Pheromone traps": "ফেরোমন ফাঁদ",
  "Pheromone/yellow sticky traps": "ফেরোমন/হলুদ আঠালো ফাঁদ",
  "Plant Bt brinjal lines where available — cuts pesticide sharply": "সম্ভব হলে Bt বেগুন লাগান — কীটনাশক অনেক কমায়",
  "Prevent — keep ridges earthed up": "প্রতিরোধ — আইলে মাটি তুলে রাখুন",
  "Release Trichogramma parasitoids": "ট্রাইকোগ্রামা পরজীবী ছাড়ুন",
  "Ridges/beds with good drainage": "ভালো নিষ্কাশনসহ আইল/বেড",
  "Rogue affected plants immediately": "আক্রান্ত গাছ সঙ্গে সঙ্গে তুলে ফেলুন",
  "Rogue infected plants": "আক্রান্ত গাছ তুলে ফেলুন",
  "Rogue infected plants early": "আক্রান্ত গাছ আগেভাগে তুলে ফেলুন",
  "Sow by early December": "ডিসেম্বরের শুরুতে বপন করুন",
  "Spare natural enemies": "প্রাকৃতিক শত্রু রক্ষা করুন",
  "Staking and spacing for airflow": "বাতাস চলাচলে খুঁটি ও দূরত্ব দিন",
  "Straw mulch and good drainage": "খড়ের মালচ ও ভালো নিষ্কাশন",
  "Use healthy certified seed tubers": "সুস্থ সার্টিফায়েড বীজ কন্দ ব্যবহার করুন",
  "Use resistant BARI Gom-33": "রোগ-সহনশীল BARI Gom-33 ব্যবহার করুন",
  "Use resistant varieties where available": "সম্ভব হলে রোগ-সহনশীল জাত ব্যবহার করুন",
  "Use tolerant BARI Masur-6/7/8": "সহনশীল BARI Masur-6/7/8 ব্যবহার করুন",
  "Weekly clipping and destruction of infested shoots": "প্রতি সপ্তাহে আক্রান্ত ডগা কেটে নষ্ট করুন",
  "Weekly whorl scouting from 20 DAS": "বপনের ২০ দিন পর থেকে সাপ্তাহিক পাতা-গোড়া পর্যবেক্ষণ",
  "Rotate chemistry to slow resistance": "প্রতিরোধ ঠেকাতে ওষুধ বদলে বদলে দিন",
  "Scout at flowering ": "ফুল আসার সময় পর্যবেক্ষণ",
  // treatments
  "At first lesion switch to cymoxanil+mancozeb or dimethomorph; budget 2–4 sprays": "প্রথম দাগেই cymoxanil+mancozeb বা dimethomorph-এ যান; ২–৪টি স্প্রে ধরুন",
  "Biological control (Trichogramma) plus removal of affected canes": "জৈব দমন (Trichogramma) ও আক্রান্ত আখ সরানো",
  "Carbofuran or chlorantraniliprole granules": "Carbofuran বা chlorantraniliprole দানা",
  "Clip infested shoots weekly through the harvest": "ফসল তোলা পর্যন্ত প্রতি সপ্তাহে আক্রান্ত ডগা কাটুন",
  "Collect and destroy egg-mass leaves at 30–50 DAS": "বপনের ৩০–৫০ দিনে ডিমের গাদাসহ পাতা সংগ্রহ করে নষ্ট করুন",
  "Drain the field": "মাঠের পানি নিষ্কাশন করুন",
  "Drain the field, then spray pymetrozine": "মাঠের পানি নিষ্কাশন করে pymetrozine স্প্রে করুন",
  "Do not spray broad-spectrum insecticide — it kills spiders, BPH's natural enemy": "ব্রড-স্পেকট্রাম কীটনাশক স্প্রে করবেন না — এতে BPH-এর শত্রু মাকড়সা মরে",
  "Fungicide spray as needed in wet weather": "ভেজা আবহাওয়ায় প্রয়োজনমতো ছত্রাকনাশক স্প্রে",
  "Fungicide spray if past threshold": "সীমা ছাড়ালে ছত্রাকনাশক স্প্রে",
  "Fungicide spray if spotting spreads": "দাগ ছড়ালে ছত্রাকনাশক স্প্রে",
  "Fungicide spray in humid spells": "আর্দ্র সময়ে ছত্রাকনাশক স্প্রে",
  "Fungicide spray in wet years": "ভেজা বছরে ছত্রাকনাশক স্প্রে",
  "Mancozeb, then systemic fungicide at first lesion": "Mancozeb, প্রথম দাগে systemic ছত্রাকনাশক",
  "Miticide/insecticide spray when curling appears": "পাতা কুঁকড়ালে মাইটনাশক/কীটনাশক স্প্রে",
  "No chemical cure — manage by avoiding excess urea and draining": "রাসায়নিক প্রতিকার নেই — বেশি ইউরিয়া এড়িয়ে ও পানি নিষ্কাশন করে সামলান",
  "No chemical cure — rogue plants and improve drainage": "রাসায়নিক প্রতিকার নেই — আক্রান্ত গাছ তুলে নিষ্কাশন বাড়ান",
  "No cure for the virus — control the whitefly vector": "ভাইরাসের প্রতিকার নেই — সাদা মাছি বাহক দমন করুন",
  "No rescue once spikes bleach — prevention only": "শীষ সাদা হলে আর রক্ষা নেই — শুধু প্রতিরোধ",
  "One propiconazole spray at heading in risk years": "ঝুঁকির বছরে শীষ আসার সময় একবার propiconazole স্প্রে",
  "Prophylactic mancozeb every 7–10 days during fog": "কুয়াশায় প্রতি ৭–১০ দিনে প্রতিরোধমূলক mancozeb",
  "Prophylactic mancozeb in fog": "কুয়াশায় প্রতিরোধমূলক mancozeb",
  "Prophylactic spraying during fog": "কুয়াশায় প্রতিরোধমূলক স্প্রে",
  "Propiconazole at heading — preventive only, no cure after bleaching": "শীষে propiconazole — শুধু প্রতিরোধ, সাদা হলে আর প্রতিকার নেই",
  "Spot spray only if numbers pass threshold": "সংখ্যা সীমা ছাড়ালে কেবল দাগে-দাগে স্প্রে",
  "Spray at first sign": "প্রথম লক্ষণেই স্প্রে",
  "Spray at first spread during fog": "কুয়াশায় প্রথম বিস্তারেই স্প্রে",
  "Spray at flowering/podding only past threshold": "সীমা ছাড়ালে কেবল ফুল/শুঁটির সময় স্প্রে",
  "Spray if leaves cup/curl": "পাতা কুঁকড়ালে স্প্রে",
  "Spray if past threshold": "সীমা ছাড়ালে স্প্রে",
  "Spray if spotting spreads": "দাগ ছড়ালে স্প্রে",
  "Spray in wet weather at fruiting": "ফল ধরার সময় ভেজা আবহাওয়ায় স্প্রে",
  "Spray malathion only past threshold, in late afternoon to spare pollinating bees": "পরাগবাহী মৌমাছি বাঁচাতে সীমা ছাড়ালে কেবল শেষ বিকেলে malathion স্প্রে",
  "Spray mancozeb": "Mancozeb স্প্রে",
  "Spray only on an actual outbreak": "শুধু প্রকৃত প্রাদুর্ভাবে স্প্রে",
  "Spray only past threshold": "সীমা ছাড়ালে কেবল স্প্রে",
  "Spray only past threshold at flowering/podding": "সীমা ছাড়ালে কেবল ফুল/শুঁটির সময় স্প্রে",
  "Spray past threshold": "সীমা ছাড়ালে স্প্রে",
  "Spray past threshold at fruiting": "ফল ধরার সময় সীমা ছাড়ালে স্প্রে",
  "Spray past threshold in humid spells": "আর্দ্র সময়ে সীমা ছাড়ালে স্প্রে",
  "Spray spinetoram or emamectin benzoate into the whorls in the evening": "সন্ধ্যায় পাতার গোড়ায় spinetoram বা emamectin benzoate স্প্রে",
  "Spray tricyclazole at first sign": "প্রথম লক্ষণেই tricyclazole স্প্রে",
  "Remove and destroy bored fruit": "ছিদ্রযুক্ত ফল সংগ্রহ করে নষ্ট করুন",
  "Remove dead-hearts": "মরা-ডগা তুলে ফেলুন",
  "Remove dead-hearts on sight": "চোখে পড়লেই মরা-ডগা তুলে ফেলুন",
  "Remove infected fruit": "আক্রান্ত ফল সরান",
  "Bore holes in fruit ": "ফলে ছিদ্র",
  "IPM first; without IPM this drives very heavy pesticide use": "আগে আইপিএম; আইপিএম ছাড়া এতে খুব বেশি কীটনাশক লাগে",
  // cost-basis notes
  "KB-implied: management only, no chemical cure": "জ্ঞানভান্ডার অনুযায়ী: শুধু ব্যবস্থাপনা, রাসায়নিক প্রতিকার নেই",
  "KB-stated: no chemical cure; cost is management only": "জ্ঞানভান্ডার মতে: রাসায়নিক প্রতিকার নেই; খরচ শুধু ব্যবস্থাপনার",
  "KB-stated: roughly 600–900 BDT/acre per application": "জ্ঞানভান্ডার মতে: প্রতি প্রয়োগে প্রায় ৬০০–৯০০ টাকা/একর",
  "KB-stated: ~700–1000 BDT/acre per spray": "জ্ঞানভান্ডার মতে: প্রতি স্প্রেতে ~৭০০–১০০০ টাকা/একর",
  "KB-stated: ~800 BDT/acre per spray × 2–4 sprays": "জ্ঞানভান্ডার মতে: ~৮০০ টাকা/একর × ২–৪টি স্প্রে",
  "Cultural control — the KB calls this crop otherwise very hardy": "কৃষি-ব্যবস্থাপনা — জ্ঞানভান্ডার মতে এ ফসল এমনিতে খুব শক্ত",
  "estimate — KB advises spray only on outbreak, no figure": "আনুমানিক — জ্ঞানভান্ডার শুধু প্রাদুর্ভাবে স্প্রে বলে, অঙ্ক দেয়নি",
  "estimate — KB describes cultural control only": "আনুমানিক — জ্ঞানভান্ডার শুধু কৃষি-ব্যবস্থাপনার কথা বলে",
  "estimate — KB gives no figure": "আনুমানিক — জ্ঞানভান্ডার কোনো অঙ্ক দেয়নি",
  "estimate — KB gives no figure for this spray": "আনুমানিক — জ্ঞানভান্ডার এই স্প্রের অঙ্ক দেয়নি",
  "estimate — KB gives no figure for this treatment": "আনুমানিক — জ্ঞানভান্ডার এই প্রতিকারের অঙ্ক দেয়নি",
  "estimate — KB names mancozeb but gives no figure": "আনুমানিক — জ্ঞানভান্ডার mancozeb বলে কিন্তু অঙ্ক দেয়নি",
  "estimate — KB names the spray but gives no figure": "আনুমানিক — জ্ঞানভান্ডার স্প্রে বলে কিন্তু অঙ্ক দেয়নি",
  "estimate — KB states heavy pesticide use without IPM/Bt, no figure given": "আনুমানিক — আইপিএম/Bt ছাড়া বেশি কীটনাশকের কথা বলে, অঙ্ক নেই",
  "estimate — crop-profile risk note, no KB figure": "আনুমানিক — ফসল-প্রোফাইলের ঝুঁকি নোট, জ্ঞানভান্ডারে অঙ্ক নেই",
  "estimate — no KB figure": "আনুমানিক — জ্ঞানভান্ডারে অঙ্ক নেই",
  "estimate — no KB figure; long season implies repeat effort": "আনুমানিক — জ্ঞানভান্ডারে অঙ্ক নেই; লম্বা মৌসুমে বারবার লাগে",
  "estimate — parallels the KB potato late-blight spray programme": "আনুমানিক — জ্ঞানভান্ডারের আলুর নাবি ধসা স্প্রে কর্মসূচির অনুরূপ",
  "Scout base of hills weekly after 45 DAT ": "রোপণের ৪৫ দিন পর প্রতি সপ্তাহে গোছার গোড়া পর্যবেক্ষণ",
};

// ---------------------------------------------------------------------------
// Regex rules for the backend's sentence templates. Captured numbers / names
// pass through unchanged; captured enums are re-tokenized via tk().
const T = (v) => TOKENS[v] ?? v;

const RULES = [
  // ===== crop recommendation `because` clauses (crops.py) =====
  [/^([\w\- ]+?) soil suitability ([\d.]+)\/1\.0 \((.+)\)$/,
    (m) => `${T(m[1])} মাটিতে উপযুক্ততা ${m[2]}/1.0 (${m[3]})`],
  [/^water need '([^']+)' vs '([^']+)' supply$/,
    (m) => `পানির চাহিদা '${T(m[1])}' বনাম '${T(m[2])}' উৎস`],
  [/^(low|medium|high) risk → profit discounted ×([\d.]+)$/,
    (m) => `${T(m[1])} ঝুঁকি → লাভে ছাড় ×${m[2]}`],
  [/^fits budget \(~([\d,]+) of ([\d,]+) BDT for ([\d.]+) acre\)$/,
    (m) => `বাজেটের মধ্যে (~${m[3]} একরের জন্য ${m[2]} টাকার মধ্যে ${m[1]})`],
  [/^full ([\d.]+) acre needs ([\d,]+) BDT — budget covers ~([\d.]+) acre$/,
    (m) => `পুরো ${m[1]} একরে লাগবে ${m[2]} টাকা — বাজেটে হবে ~${m[3]} একর`],
  [/^you asked to grow (.+) this (.+) season — shown first as your stated choice$/,
    (m) => `আপনি এই ${T(m[2])} মৌসুমে ${cropName(m[1], "bn")} চেয়েছেন — তাই এটিই প্রথমে দেখানো হলো`],
  [/^only ([\d.]+) mm rain forecast — a stress risk for a ([\w-]+)-water crop without irrigation$/,
    (m) => `পূর্বাভাসে মাত্র ${m[1]} মিমি বৃষ্টি — সেচ ছাড়া '${T(m[2])}' পানির ফসলে চাপের ঝুঁকি`],
  [/^([\d.]+) mm forecast rain raises waterlogging risk$/,
    (m) => `পূর্বাভাসের ${m[1]} মিমি বৃষ্টিতে জলাবদ্ধতার ঝুঁকি`],
  [/^([\d.]+) mm rain forecast over the period supports its ([\w-]+) water need$/,
    (m) => `এ সময়ের ${m[1]} মিমি বৃষ্টির পূর্বাভাস এর '${T(m[2])}' পানির চাহিদা পূরণে সহায়ক`],

  // ===== excluded-crop reasons (crops.py gates) =====
  [/^out of season — grows in (.+), not (.+)$/,
    (m) => `মৌসুমের বাইরে — হয় ${m[1].split("/").map(T).join("/")}-এ, ${T(m[2])}-এ নয়`],
  [/^costs ~([\d,]+) BDT\/acre — above the entire ([\d,]+) BDT budget even for 1 acre$/,
    (m) => `খরচ ~${m[1]} টাকা/একর — 1 একরের জন্যও পুরো ${m[2]} টাকার বাজেট ছাড়িয়ে যায়`],
  [/^water need '([^']+)' far exceeds a '([^']+)' water supply$/,
    (m) => `পানির চাহিদা '${T(m[1])}' — '${T(m[2])}' পানির উৎসের সাধ্যের বাইরে`],

  // ===== season-plan warnings + stage `because` (season_plan.py) =====
  [/^Chosen sowing date (.+) is OUTSIDE the recommended window \((.+) to (.+)\) — expect yield loss; consider a short-duration variety\.$/,
    (m) => `নির্বাচিত বপন তারিখ ${m[1]} সুপারিশকৃত সময়ের (${m[2]} থেকে ${m[3]}) বাইরে — ফলন কমতে পারে; স্বল্পমেয়াদি জাত ভাবুন।`],
  [/^(.+) is poorly suited to sandy soil \(suitability ([\d.]+)\); expect higher irrigation\/nitrogen losses\.$/,
    (m) => `${cropName(m[1], "bn")} বেলে মাটিতে কম উপযোগী (উপযুক্ততা ${m[2]}); সেচ ও নাইট্রোজেন অপচয় বেশি হবে।`],
  [/^([+-]\d+) days from sowing\/transplanting per (.+)$/,
    (m) => `বপন/রোপণ থেকে ${m[1]} দিন — সূত্র: ${m[2]}`],

  // ===== scenario verdicts + reasoning (scenario.py) =====
  [/^Still profitable, but ([\d,.]+) BDT worse off\.$/,
    (m) => `এখনও লাভজনক, তবে ${m[1]} টাকা কম লাভ হবে।`],
  [/^Better off by ([\d,.]+) BDT under this scenario\.$/,
    (m) => `এই পরিস্থিতিতে ${m[1]} টাকা বেশি লাভ হবে।`],
  [/^Rainfall ([+\-\d.]+)% → yield ([+\-\d.]+)%: (.+) is a '([^']+)' water-need crop \(sensitivity ([\d.]+)\), and '([^']+)' water access offsets (\d+)% of the shortfall \((.+)\)\.$/,
    (m) => `বৃষ্টিপাত ${m[1]}% → ফলন ${m[2]}%: ${cropName(m[3], "bn")} '${T(m[4])}' পানির চাহিদার ফসল (সংবেদনশীলতা ${m[5]}); '${T(m[6])}' সেচ-সুবিধা ঘাটতির ${m[7]}% পুষিয়ে দেয় (${m[8]})।`],
  [/^Yield adjusted ([+\-\d.]+)% as asked\.$/,
    (m) => `অনুরোধ অনুযায়ী ফলন ${m[1]}% সমন্বয় করা হয়েছে।`],
  [/^Selling price ([+\-\d.]+)% → ([\d,.]+) BDT\/maund \(baseline ([\d,.]+)\)\.$/,
    (m) => `বিক্রয়মূল্য ${m[1]}% → ${m[2]} টাকা/মণ (আগে ${m[3]})।`],
  [/^Every input cost line moved ([+\-\d.]+)%\.$/,
    (m) => `প্রতিটি খরচের খাত ${m[1]}% পরিবর্তিত হয়েছে।`],
  [/^Budget ([+\-\d.]+)% → ([\d,.]+) BDT \(baseline plan needed ([\d,.]+) BDT for ([\d.]+) acre\)\.$/,
    (m) => `বাজেট ${m[1]}% → ${m[2]} টাকা (আগের পরিকল্পনায় ${m[4]} একরের জন্য দরকার ছিল ${m[3]} টাকা)।`],
  [/^At ([\d,.]+) BDT\/acre, that budget funds only ([\d.]+) of the ([\d.]+) acre — the plan is resized, not just re-priced\.$/,
    (m) => `একরপ্রতি ${m[1]} টাকা হিসাবে এই বাজেটে ${m[3]} একরের মধ্যে কেবল ${m[2]} একর সম্ভব — পরিকল্পনাটি নতুন আয়তনে সাজানো হয়েছে।`],
  [/^The budget still covers all ([\d.]+) acre \(([\d,.]+) BDT needed\) — acreage unchanged\.$/,
    (m) => `বাজেটে পুরো ${m[1]} একরই সম্ভব (${m[2]} টাকা প্রয়োজন) — জমির পরিমাণ অপরিবর্তিত।`],
  [/^Baseline and scenario are both produced by compute_financials — the same deterministic math, only the inputs differ\.$/,
    () => `আগের ও নতুন — দুই হিসাবই compute_financials দিয়ে করা; গণিত একই, শুধু ইনপুট আলাদা।`],

  // ===== finance assumptions (finance.py) =====
  [/^per-acre reference costs for (.+) from seed data \(compiled from public DAE\/BARI extension figures\), scaled by farm size$/,
    (m) => `${cropName(m[1], "bn")}-এর একরপ্রতি রেফারেন্স খরচ (সরকারি DAE/BARI সম্প্রসারণ তথ্য থেকে), জমির আয়তন অনুযায়ী হিসাব`],
  [/^reference yield ([\d.]+) maund\/acre for (.+) \(public extension figures\)$/,
    (m) => `রেফারেন্স ফলন ${m[1]} মণ/একর — ${cropName(m[2], "bn")} (সরকারি সম্প্রসারণ তথ্য)`],
  [/^price ([\d.]+) BDT\/maund from seeded market data \(MOCK — replace with live feed\)$/,
    (m) => `দাম ${m[1]} টাকা/মণ — নমুনা বাজারতথ্য (মক — লাইভ ফিড নয়)`],
  [/^caller-specified yield ([\d.]+) maund\/acre$/,
    (m) => `আপনার দেওয়া ফলন ${m[1]} মণ/একর`],
  [/^caller-specified price ([\d.]+) BDT\/maund$/,
    (m) => `আপনার দেওয়া দাম ${m[1]} টাকা/মণ`],

  // ===== market because + revenue estimate (market.py) =====
  [/^prices are rising \(\+([\d.]+)% vs last period\) and this crop stores well — hold a while to capture the climb, if you have dry storage$/,
    (m) => `দাম বাড়ছে (গত সময়ের চেয়ে +${m[1]}%) এবং এ ফসল মজুতে ভালো থাকে — শুকনা গুদাম থাকলে কিছুদিন ধরে রাখুন`],
  [/^prices are rising \(\+([\d.]+)%\) but this crop is perishable — sell into the high now rather than risk it spoiling before prices peak$/,
    (m) => `দাম বাড়ছে (+${m[1]}%) কিন্তু ফসলটি পচনশীল — নষ্ট হওয়ার ঝুঁকি না নিয়ে এই চড়া দামেই বিক্রি করুন`],
  [/^prices are falling \(([-\d.]+)% vs last period\) — sell now, waiting is likely to fetch less$/,
    (m) => `দাম কমছে (গত সময়ের চেয়ে ${m[1]}%) — এখনই বিক্রি করুন, অপেক্ষায় দাম আরও কমতে পারে`],
  [/^prices are flat — sell now for cash, or store only if you expect the usual post-harvest seasonal rise and can store without loss$/,
    () => `দাম স্থির — নগদ দরকার হলে এখনই বেচুন; ক্ষতি ছাড়া মজুত রাখতে পারলে মৌসুমি দর-বৃদ্ধির আশায় রাখতে পারেন`],
  [/^prices are flat and the crop is perishable — no gain from holding, sell now$/,
    () => `দাম স্থির এবং ফসল পচনশীল — ধরে রেখে লাভ নেই, এখনই বিক্রি করুন`],
  [/^([\d,.]+) (maund) × ([\d,.]+) BDT at today's price \((your stated yield|reference yield)\)$/,
    (m) => `আজকের দামে ${m[1]} মণ × ${m[3]} টাকা (${m[4] === "your stated yield" ? "আপনার দেওয়া ফলন" : "রেফারেন্স ফলন"})`],
  [/^using '(.+)' as a price proxy for '(.+)'$/,
    (m) => `'${cropName(m[2], "bn")}'-এর দামের জন্য '${cropName(m[1], "bn")}' ব্যবহার করা হয়েছে`],

  // ===== supplier comparison (suppliers.py) =====
  [/^Buy from (.+)$/, (m) => `${_sn(m[1])} থেকে কিনুন`],
  [/^(.+) is cheapest for your ([\d,.]+) kg fertilizer basket at ([\d,]+) BDT — saves ([\d,]+) BDT vs (.+)\. It delivers in (\d+) day\(s\), rated ([\d.]+), ([\d.]+) km away\.$/,
    (m) => `আপনার ${m[2]} কেজি সারের ঝুড়ির জন্য ${_sn(m[1])} সবচেয়ে সস্তা — ${m[3]} টাকা (${_sn(m[5])}-এর চেয়ে ${m[4]} টাকা সাশ্রয়)। ডেলিভারি ${m[6]} দিনে, রেটিং ${m[7]}, দূরত্ব ${m[8]} কিমি।`],
  [/^(.+) is cheapest for your ([\d,.]+) kg fertilizer basket at ([\d,]+) BDT\. It delivers in (\d+) day\(s\), rated ([\d.]+), ([\d.]+) km away\.$/,
    (m) => `আপনার ${m[2]} কেজি সারের ঝুড়ির জন্য ${_sn(m[1])} সবচেয়ে সস্তা — ${m[3]} টাকা। ডেলিভারি ${m[4]} দিনে, রেটিং ${m[5]}, দূরত্ব ${m[6]} কিমি।`],
  [/^(.+) delivers fastest \((\d+) day\(s\)\)$/,
    (m) => `${_sn(m[1])} সবচেয়ে দ্রুত ডেলিভারি দেয় (${m[2]} দিন)`],
  [/^(.+) is highest-rated \(([\d.]+)\)$/,
    (m) => `${_sn(m[1])}-এর রেটিং সর্বোচ্চ (${m[2]})`],
  [/^soil type not provided — standard \(non-sandy\) FRG dose assumed; sandy soil would need ~25% more MoP$/,
    () => `মাটির ধরন দেওয়া হয়নি — সাধারণ (অ-বেলে) FRG মাত্রা ধরা হয়েছে; বেলে মাটিতে ~25% বেশি MoP লাগত`],

  // ===== disclosure notes =====
  [/^profit estimates use seeded reference prices \(see data\/seed\) — disclosed as mock$/,
    () => `লাভের হিসাবে নমুনা (মক) রেফারেন্স দাম ব্যবহৃত`],
  [/^seeded\/mock \(data\/seed\/market_prices\.json — not a live feed\)$/,
    () => `নমুনা/মক দাম — লাইভ ফিড নয়`],
  [/^seeded\/mock \(data\/seed\/suppliers\.json — a seeded catalog is allowed by the brief\)$/,
    () => `নমুনা/মক ক্যাটালগ — ব্রিফ অনুযায়ী অনুমোদিত`],
];

// Split on "; " only at parenthesis depth 0 — clause separators inside a KB
// citation like "(BARI brinjal guide; DAE IPM leaflet)" must NOT split the
// clause, or the outer template rule stops matching.
function splitClauses(s) {
  const out = [];
  let depth = 0;
  let start = 0;
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (c === "(") depth++;
    else if (c === ")") depth = Math.max(0, depth - 1);
    else if (depth === 0 && c === ";" && s[i + 1] === " ") {
      out.push(s.slice(start, i));
      start = i + 2;
      i++;
    }
  }
  out.push(s.slice(start));
  return out;
}

// ---------------------------------------------------------------------------
function _loc(s) {
  // exact phrase / stage action / pest reference?
  if (PHRASES[s]) return PHRASES[s];
  if (ACTIONS[s]) return ACTIONS[s];
  if (PEST[s]) return PEST[s];

  // template rules (try the whole string before splitting)
  for (const [re, build] of RULES) {
    const m = s.match(re);
    if (m) return build(m);
  }

  // multi-clause because-string? split at top-level "; " only
  const clauses = splitClauses(s);
  if (clauses.length > 1) {
    return clauses.map((part) => _loc(part)).join("; ");
  }

  return s; // safe fallback: original English
}

/** Translate one backend data string to Bangla, deterministically, then render
 *  its numerals in Bengali digits. Multi-clause strings (joined by "; ") are
 *  translated clause-by-clause. Unrecognized text falls back to English —
 *  never garbled. Numbers keep their value; only the script changes. */
export function localize(text, lang) {
  if (lang !== "bn" || text == null || text === "") return text;
  return toBnDigits(_loc(String(text)));
}
