// Crisp flat-vector SVG icons for board objects. Stylised (Murdoku-like), never
// cropped from the source image. Each returns an inner-SVG markup string drawn in a
// 0..100 viewBox; `boardIcon` wraps it with a viewBox.

const RAW = {
  chair: `<rect x="22" y="30" width="56" height="44" rx="9" fill="#eef1f7" stroke="#9aa6bd" stroke-width="3"/>
    <rect x="30" y="58" width="40" height="20" rx="6" fill="#dfe4ee" stroke="#9aa6bd" stroke-width="3"/>
    <rect x="28" y="74" width="8" height="12" fill="#9aa6bd"/><rect x="64" y="74" width="8" height="12" fill="#9aa6bd"/>`,
  car: `<path d="M14 60 q4-18 16-20 h40 q12 2 16 20 v10 h-72 z" fill="#9fb0e8" stroke="#41506e" stroke-width="3"/>
    <path d="M34 42 h32 q8 1 10 16 h-52 q2-15 10-16z" fill="#cfd9f5" stroke="#41506e" stroke-width="2"/>
    <circle cx="30" cy="72" r="9" fill="#2c3142" stroke="#11161f" stroke-width="2"/>
    <circle cx="70" cy="72" r="9" fill="#2c3142" stroke="#11161f" stroke-width="2"/>`,
  oil_slick: `<path d="M28 56 q-12-2-12 10 q0 12 16 12 q6 8 22 6 q22 0 22-14 q0-12-16-12 q-6-10-22-8 q-8 1-10 8z" fill="#26282d" stroke="#0c0d10" stroke-width="2"/>
    <ellipse cx="40" cy="62" rx="6" ry="3" fill="#3c4350" opacity="0.7"/>`,
  shelf: `<rect x="24" y="20" width="52" height="62" rx="4" fill="#5b6a86" stroke="#222c3e" stroke-width="3"/>
    <line x1="24" y1="40" x2="76" y2="40" stroke="#222c3e" stroke-width="3"/>
    <line x1="24" y1="60" x2="76" y2="60" stroke="#222c3e" stroke-width="3"/>
    <rect x="30" y="26" width="8" height="10" fill="#aab4ca"/><rect x="42" y="24" width="6" height="12" fill="#c9d1e2"/>
    <rect x="30" y="44" width="14" height="12" fill="#9aa6bd"/><rect x="50" y="46" width="8" height="10" fill="#c9d1e2"/>`,
  tv: `<rect x="20" y="28" width="60" height="38" rx="5" fill="#1c2230" stroke="#0c0f16" stroke-width="3"/>
    <rect x="26" y="34" width="48" height="26" rx="3" fill="#5fa8d8"/>
    <rect x="40" y="66" width="20" height="8" fill="#3a4256"/><rect x="34" y="74" width="32" height="5" rx="2" fill="#2a3142"/>
    <text x="50" y="52" font-size="16" text-anchor="middle" fill="#fff">&#9834;</text>`,
  table: `<rect x="20" y="40" width="60" height="14" rx="3" fill="#7c5a3c" stroke="#3e2c1c" stroke-width="3"/>
    <rect x="24" y="54" width="6" height="22" fill="#5a4026"/><rect x="70" y="54" width="6" height="22" fill="#5a4026"/>`,
  plant: `<rect x="38" y="58" width="24" height="22" rx="3" fill="#7a4a3a" stroke="#3e2418" stroke-width="2"/>
    <path d="M50 58 q-22-6-26-30 q16 2 26 22 q10-22 28-24 q-4 26-28 32z" fill="#4f9e54" stroke="#2c5e30" stroke-width="2"/>`,
  couch: `<rect x="16" y="46" width="68" height="28" rx="8" fill="#6d7488" stroke="#2c3142" stroke-width="3"/>
    <rect x="16" y="38" width="14" height="36" rx="6" fill="#7d8499" stroke="#2c3142" stroke-width="3"/>
    <rect x="70" y="38" width="14" height="36" rx="6" fill="#7d8499" stroke="#2c3142" stroke-width="3"/>`,
  tree: `<path d="M50 16 L66 44 H58 L72 70 H28 L42 44 H34 Z" fill="#3c7d44" stroke="#234a28" stroke-width="3"/>
    <rect x="45" y="70" width="10" height="14" fill="#6b4a2c"/>`,
  shrub: `<path d="M30 70 q-14 0-12-14 q-6-12 8-16 q2-12 18-10 q10-8 22 2 q14 0 12 14 q6 10-6 16 q-2 10-18 8 q-12 6-24-0z"
    fill="#4f8a4a" stroke="#2c5e30" stroke-width="3"/>`,
  boulder: `<path d="M22 72 q-6-18 12-26 q10-14 28-6 q18-2 18 16 q6 14-8 18 z" fill="#aeb6bf" stroke="#5c636e" stroke-width="3"/>
    <path d="M30 66 q8-12 20-12" fill="none" stroke="#7d858f" stroke-width="2"/>`,
  bear: `<ellipse cx="52" cy="60" rx="30" ry="18" fill="#b08a5a" stroke="#6e4f2c" stroke-width="3"/>
    <circle cx="26" cy="50" r="11" fill="#b08a5a" stroke="#6e4f2c" stroke-width="3"/>
    <circle cx="22" cy="44" r="4" fill="#8a6a3e"/><circle cx="31" cy="44" r="4" fill="#8a6a3e"/>
    <rect x="36" y="74" width="8" height="10" fill="#8a6a3e"/><rect x="60" y="74" width="8" height="10" fill="#8a6a3e"/>`,
};

export function boardIcon(type) {
  const inner = RAW[type];
  if (!inner) return "";
  return `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">${inner}</svg>`;
}

export function legendIcon(type) {
  return boardIcon(type);
}

export function puzzleThumb(theme) {
  // small decorative magnifier-over-grid thumbnail for the gallery card
  const accent =
    theme && theme.includes("hik")
      ? "#4f8a4a"
      : theme && theme.includes("auto")
        ? "#5b6a86"
        : "#3d7bf0";
  return `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <rect x="14" y="14" width="58" height="58" rx="6" fill="#eef1f7" stroke="${accent}" stroke-width="3"/>
    ${[26, 38, 50, 62]
      .map((p) => `<line x1="${p}" y1="14" x2="${p}" y2="72" stroke="${accent}" stroke-width="1" opacity="0.4"/>
        <line x1="14" y1="${p}" x2="72" y2="${p}" stroke="${accent}" stroke-width="1" opacity="0.4"/>`)
      .join("")}
    <circle cx="64" cy="64" r="16" fill="none" stroke="#1c2436" stroke-width="5"/>
    <line x1="76" y1="76" x2="90" y2="90" stroke="#1c2436" stroke-width="6" stroke-linecap="round"/>
  </svg>`;
}
