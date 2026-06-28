// Procedural flat-vector portrait from a suspect's `appearance` attributes.
// Murdoku-style: a coloured background unique to the suspect, a simple face,
// hair, and optional accessories (cap, glasses, beard). Never uses the source image.

const HAIR = {
  blonde: "#e6c86a",
  black: "#2c2a30",
  brown: "#6b4a2c",
  auburn: "#b3582c",
  grey: "#b9bcc4",
  gray: "#b9bcc4",
  white: "#e7e9ee",
  red: "#c0552c",
  default: "#5a4a38",
};

const BG_PALETTE = [
  "#8e87b8", "#6f93b0", "#7fae8c", "#b08aa6", "#c8a06a",
  "#7d9fb8", "#9c84ad", "#6fae9f", "#b58c7a", "#84a0c8",
  "#a7bd84", "#c9929f",
];

function hashStr(s) {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return h;
}

function skinFor(id) {
  const tones = ["#f0c9a8", "#e8b48d", "#d59c73", "#b87a4f", "#8a5a38"];
  return tones[hashStr(id + "skin") % tones.length];
}

export function suspectColor(suspect) {
  const a = suspect.appearance || {};
  if (a.bg) return a.bg;
  return BG_PALETTE[hashStr(suspect.id || suspect.name || "x") % BG_PALETTE.length];
}

export function avatarSVG(suspect) {
  const a = suspect.appearance || {};
  const id = suspect.id || suspect.name || "x";
  const bg = a.bg || BG_PALETTE[hashStr(id) % BG_PALETTE.length];
  const skin = skinFor(id);
  const hair = HAIR[a.hair] || HAIR.default;
  const cap = !!a.cap;
  const glasses = !!a.glasses;
  const beard = !!a.beard;
  const isV = suspect.isVictim;

  const capColor = a.capColor || ["#7e6fb0", "#5f93c0", "#3a3f4c", "#c98aa0"][hashStr(id + "cap") % 4];

  return `<svg class="portrait" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="${suspect.name}">
    <rect width="100" height="100" fill="${bg}"/>
    <!-- shoulders -->
    <path d="M16 100 q4-26 34-30 q30 4 34 30 z" fill="${isV ? "#5a4452" : "#37414f"}"/>
    <!-- neck -->
    <rect x="42" y="58" width="16" height="18" rx="4" fill="${skin}"/>
    <!-- head -->
    <ellipse cx="50" cy="44" rx="20" ry="23" fill="${skin}"/>
    ${
      beard
        ? `<path d="M30 46 q2 26 20 28 q18-2 20-28 q-8 12-20 12 q-12 0-20-12z" fill="${hair}"/>`
        : ""
    }
    <!-- hair -->
    ${
      cap
        ? `<path d="M27 40 q1-22 23-22 q22 0 23 22 q-23-9-46 0z" fill="${capColor}"/>
           <path d="M27 40 q23-9 46 0 l6 2 q-29-7-58 0z" fill="${capColor}" opacity="0.8"/>
           <ellipse cx="50" cy="40" rx="23" ry="4" fill="${capColor}"/>`
        : `<path d="M28 42 q-2-26 22-26 q24 0 22 26 q-4-12-22-12 q-18 0-22 12z" fill="${hair}"/>`
    }
    <!-- eyes / glasses -->
    ${
      glasses
        ? `<g fill="none" stroke="#22262e" stroke-width="3">
             <circle cx="41" cy="44" r="6"/><circle cx="59" cy="44" r="6"/>
             <line x1="47" y1="44" x2="53" y2="44"/></g>`
        : `<circle cx="41" cy="45" r="2.4" fill="#2a2a30"/><circle cx="59" cy="45" r="2.4" fill="#2a2a30"/>`
    }
  </svg>`;
}
