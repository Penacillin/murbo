import { loadPuzzle } from "./puzzles.js";
import { avatarSVG, suspectColor } from "./avatar.js";
import { boardIcon, legendIcon } from "./icons.js";

const OCCUPIABLE_TYPES = ["chair", "car", "oil_slick"];

// ---- module state for the active game ----
let P = null; // puzzle
let state = null; // { placements: {id:[r,c]}, xs: Set "r,c", notes: {"r,c":initial} }
let selected = null; // suspect id
let tool = "place"; // place | x | erase
let history = [];
let cellPx = 56;

function key(r, c) {
  return `${r},${c}`;
}
function storeKey() {
  return `murbo:progress:${P.id}`;
}

function save() {
  const data = {
    placements: state.placements,
    xs: [...state.xs],
    notes: state.notes,
  };
  localStorage.setItem(storeKey(), JSON.stringify(data));
}
function load() {
  try {
    const d = JSON.parse(localStorage.getItem(storeKey()));
    if (d)
      return {
        placements: d.placements || {},
        xs: new Set(d.xs || []),
        notes: d.notes || {},
      };
  } catch {
    /* ignore */
  }
  return { placements: {}, xs: new Set(), notes: {} };
}

function pushHistory() {
  history.push(JSON.stringify({ placements: state.placements, xs: [...state.xs], notes: state.notes }));
  if (history.length > 100) history.shift();
}
function undo() {
  const prev = history.pop();
  if (!prev) return;
  const d = JSON.parse(prev);
  state.placements = d.placements;
  state.xs = new Set(d.xs);
  state.notes = d.notes;
  save();
  rerender();
}

// ---- geometry helpers ----
function roomOf() {
  const m = {};
  for (const room of P.rooms) for (const [r, c] of room.cells) m[key(r, c)] = room.name;
  return m;
}
function roomColor() {
  const m = {};
  for (const room of P.rooms) m[room.name] = room.color || "#cdd6e6";
  return m;
}
function objectsAt() {
  const m = {};
  for (const o of P.objects) (m[key(...o.cell)] ||= []).push(o);
  return m;
}
function blockedSet() {
  const s = new Set();
  for (const o of P.objects) if (o.occupiable === false) s.add(key(...o.cell));
  return s;
}
function oobSet() {
  return new Set((P.outOfBounds || []).map((c) => key(c[0], c[1])));
}

// ---- auto-X derived from Sudoku rule (row + column of every placement) ----
function autoXset() {
  const s = new Set();
  for (const [, [r, c]] of Object.entries(state.placements)) {
    for (let cc = 0; cc < P.grid.cols; cc++) s.add(key(r, cc));
    for (let rr = 0; rr < P.grid.rows; rr++) s.add(key(rr, c));
  }
  return s;
}

function suspectById(id) {
  return P.suspects.find((s) => s.id === id);
}
function placedSuspectAt(r, c) {
  for (const [id, [pr, pc]] of Object.entries(state.placements)) if (pr === r && pc === c) return id;
  return null;
}

// ---- rendering ----
export async function renderGame(view, id) {
  view.innerHTML = `<a class="back-link" href="#/">← all puzzles</a><div class="game" id="game"></div>`;
  const root = view.querySelector("#game");
  try {
    P = await loadPuzzle(id);
  } catch (e) {
    root.innerHTML = `<p style="color:#fff">Could not load puzzle: ${e.message}</p>`;
    return;
  }
  state = load();
  selected = null;
  tool = "place";
  history = [];
  computeCellPx();
  root.innerHTML = `
    <div class="game-body${P.grid.cols >= 13 ? " compact" : ""}">
      <div class="panel" id="suspects"></div>
      <div class="board-wrap"><h2 class="board-title">${P.title} · ${P.grid.cols}×${P.grid.rows}</h2><div class="board" id="board"></div></div>
      <div class="tools" id="tools"></div>
    </div>`;
  bindBoardPointer(root.querySelector("#board"));
  rerender();
  window.addEventListener("resize", onResize);
}

function onResize() {
  if (!P) return;
  computeCellPx();
  drawBoard();
}
function computeCellPx() {
  // Board fills the available viewport: bounded by the board column's width and by
  // the full height (only the top bar + back-link + title are reserved). Like
  // Murdoku, even large grids stay fully visible with no page scroll.
  const panel = P.grid.cols >= 13 ? 318 : 358; // left panel; tools ~104; gaps ~52
  const byW = (window.innerWidth - panel - 104 - 52) / P.grid.cols;
  const byH = (window.innerHeight - 142) / P.grid.rows; // top bar + back-link + title + padding
  cellPx = Math.max(20, Math.min(104, Math.floor(Math.min(byW, byH))));
}

function legendHTML() {
  const present = new Set(P.objects.map((o) => o.type));
  const occ = OCCUPIABLE_TYPES.filter((t) => present.has(t));
  const blocked = [...present].filter((t) => !OCCUPIABLE_TYPES.includes(t));
  const li = (t) => `<div class="li">${legendIcon(t)}<span>${labelFor(t)}</span></div>`;
  return `<div class="legend">
    ${occ.length ? `<div class="group"><h4>Can occupy</h4><div class="items">${occ.map(li).join("")}</div></div>` : ""}
    ${blocked.length ? `<div class="group"><h4>Blocked</h4><div class="items">${blocked.map(li).join("")}</div></div>` : ""}
  </div>`;
}
function labelFor(t) {
  return { oil_slick: "Oil Slick", tv: "TV" }[t] || t[0].toUpperCase() + t.slice(1);
}

function rerender() {
  drawSuspects();
  drawBoard();
  drawTools();
}

function drawSuspects() {
  const el = document.getElementById("suspects");
  const gc = (P.generalClues || []).filter((c) => c.raw);
  const cols = P.suspects.length <= 6 ? 3 : 4;
  el.innerHTML = `
    ${legendHTML()}
    ${
      gc.length
        ? `<div class="general-clues"><h4>General Clues</h4>${gc
            .map((c) => `<div class="gc">①&nbsp;<span>${clueHTML(c.raw)}</span></div>`)
            .join("")}</div>`
        : ""
    }
    <h3>Suspects <small>· click, then tap the grid</small></h3>
    <div class="suspects-grid" style="grid-template-columns:repeat(${cols},1fr)">${P.suspects.map(suspectCard).join("")}</div>`;
  el.querySelectorAll(".suspect").forEach((node) => {
    node.addEventListener("click", () => {
      selected = selected === node.dataset.id ? null : node.dataset.id;
      tool = "place";
      rerender();
    });
  });
}

function suspectCard(s) {
  const isSel = selected === s.id;
  const placed = !!state.placements[s.id];
  let raw = s.clueRaw || "";
  if (s.isVictim) raw = raw.replace(/^The Victim\.?/i, "**The Victim.**");
  return `<div class="suspect ${isSel ? "selected" : ""} ${placed ? "placed" : ""}" data-id="${s.id}">
    ${avatarSVG(s)}
    <div class="name ${s.isVictim ? "victim" : ""}">${s.name}</div>
    <div class="clue ${s.isVictim ? "victim-clue" : ""}">${clueHTML(raw)}</div>
  </div>`;
}

// Hoverable definitions for spatial/logic terms used in clues (per the guide).
const TERM_DEFS = {
  beside: "to the left, right, above or below something — and in the same area (walls block it)",
  above: "directly above, in the same column",
  below: "directly below, in the same column",
  north: "directly above (same column); “N rows north” counts that many rows up",
  south: "directly below (same column)",
  east: "directly to the right, in the same row",
  west: "directly to the left, in the same row",
  alone: "the only person in that area",
  corner: "a cell tucked into a corner of the area (walls on two sides)",
  column: "the vertical line of cells — one person per column",
  row: "the horizontal line of cells — one person per row",
};
const TERM_RE = new RegExp(`\\b(${Object.keys(TERM_DEFS).join("|")})\\b`, "gi");

function annotateTerms(text) {
  // single pass so inserted title="…" attributes are never re-scanned
  return text.replace(
    TERM_RE,
    (m) => `<span class="term" title="${TERM_DEFS[m.toLowerCase()]}">${m}</span>`,
  );
}

function clueHTML(raw) {
  return bold(annotateTerms(raw));
}

function bold(text) {
  return (text || "").replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
}

function drawBoard() {
  const board = document.getElementById("board");
  const ro = roomOf();
  const rc = roomColor();
  const objs = objectsAt();
  const blocked = blockedSet();
  const oob = oobSet();
  const autoX = autoXset();
  const labelCells = roomLabelCells();
  board.style.gridTemplateColumns = `repeat(${P.grid.cols}, ${cellPx}px)`;
  let html = "";
  for (let r = 0; r < P.grid.rows; r++) {
    for (let c = 0; c < P.grid.cols; c++) {
      const k = key(r, c);
      if (oob.has(k)) {
        html += `<div class="cell oob" style="width:${cellPx}px;height:${cellPx}px"></div>`;
        continue;
      }
      const room = ro[k];
      const color = room ? rc[room] : "#aeb6c4";
      const wt = room !== ro[key(r - 1, c)] ? "wall-t" : "";
      const wb = room !== ro[key(r + 1, c)] ? "wall-b" : "";
      const wl = room !== ro[key(r, c - 1)] ? "wall-l" : "";
      const wr = room !== ro[key(r, c + 1)] ? "wall-r" : "";
      const isBlocked = blocked.has(k);
      const cellObjs = objs[k] || [];
      const objSvg = cellObjs.length ? `<span class="obj">${boardIcon(cellObjs[0].type)}</span>` : "";
      const placedId = placedSuspectAt(r, c);
      let token = "";
      if (placedId) {
        const s = suspectById(placedId);
        token = `<span class="token ${s.isVictim ? "victim" : ""}" style="background:${s.isVictim ? "" : suspectColor(s)}">${s.isVictim ? "V" : s.initial}</span>`;
      }
      const userX = state.xs.has(k);
      const showX = (userX || (autoX.has(k) && !placedId)) ? `<span class="xmark">✕</span>` : "";
      const note = state.notes[k] ? `<span class="note">${state.notes[k]}</span>` : "";
      const lab = labelCells[k];
      const label = lab ? `<span class="roomlabel ${lab.side}">${lab.name}</span>` : "";
      html += `<div class="cell ${wt} ${wb} ${wl} ${wr} ${isBlocked ? "blocked" : ""}"
        data-r="${r}" data-c="${c}" style="background:${color};width:${cellPx}px;height:${cellPx}px">
        ${objSvg}${label}${showX}${note}${token}</div>`;
    }
  }
  board.innerHTML = html;
}

function roomLabelCells() {
  // Tuck each room label into the room's bottom edge (Murdoku-style) so it hugs a
  // wall instead of covering the center. Anchor toward the near horizontal side and
  // prefer an empty cell so the label doesn't sit on top of an object.
  const objCells = new Set(P.objects.map((o) => key(...o.cell)));
  const mid = P.grid.cols / 2;
  const out = {};
  for (const room of P.rooms) {
    if (!room.cells.length) continue;
    const centroidCol = room.cells.reduce((a, [, c]) => a + c, 0) / room.cells.length;
    const side = centroidCol >= mid ? "right" : "left";
    const maxRow = Math.max(...room.cells.map(([r]) => r));
    const rowCells = room.cells
      .filter(([r]) => r === maxRow)
      .sort((a, b) => (side === "right" ? b[1] - a[1] : a[1] - b[1]));
    const pick = rowCells.find(([r, c]) => !objCells.has(key(r, c))) || rowCells[0];
    out[key(pick[0], pick[1])] = { name: room.name, side };
  }
  return out;
}

function drawTools() {
  const allPlaced = P.suspects.every((s) => state.placements[s.id]);
  const el = document.getElementById("tools");
  el.innerHTML = `
    <button class="tool ${tool === "x" ? "active" : ""}" data-act="x" title="X-mark tool">✕<small>mark</small></button>
    <button class="tool ${tool === "erase" ? "active" : ""}" data-act="erase" title="Eraser (hold to clear all)">⌫<small>erase</small></button>
    <button class="tool" data-act="undo" title="Undo">↶<small>undo</small></button>
    <button class="tool" data-act="hint" title="Reveal one correct placement">💡<small>hint</small></button>
    <button class="tool submit" data-act="submit" ${allPlaced ? "" : "disabled"} title="Check your answer">✓<small>submit</small></button>
    <button class="tool" data-act="how" title="How to play">?<small>help</small></button>`;
  el.querySelectorAll(".tool").forEach((b) => {
    const act = b.dataset.act;
    b.addEventListener("click", () => onTool(act));
    if (act === "erase") {
      let t;
      b.addEventListener("pointerdown", () => {
        t = setTimeout(() => {
          clearAll();
        }, 600);
      });
      const cancel = () => clearTimeout(t);
      b.addEventListener("pointerup", cancel);
      b.addEventListener("pointerleave", cancel);
    }
  });
}

function onTool(act) {
  if (act === "x") {
    tool = tool === "x" ? "place" : "x";
    selected = null;
  } else if (act === "erase") {
    tool = tool === "erase" ? "place" : "erase";
    selected = null;
  } else if (act === "undo") {
    undo();
    return;
  } else if (act === "hint") {
    giveHint();
    return;
  } else if (act === "submit") {
    submit();
    return;
  } else if (act === "how") {
    showHowTo();
    return;
  }
  rerender();
}

// ---- board interaction ----
function bindBoardPointer(board) {
  let dragging = false;
  board.addEventListener("contextmenu", (e) => {
    const cell = e.target.closest(".cell");
    if (!cell) return;
    e.preventDefault();
    toggleX(+cell.dataset.r, +cell.dataset.c);
  });
  board.addEventListener("pointerdown", (e) => {
    const cell = e.target.closest(".cell");
    if (!cell) return;
    const r = +cell.dataset.r,
      c = +cell.dataset.c;
    if (tool === "x" || tool === "erase") {
      dragging = true;
      applyMark(r, c);
    } else {
      onCellPlace(r, c);
    }
  });
  board.addEventListener("pointerover", (e) => {
    if (!dragging) return;
    const cell = e.target.closest(".cell");
    if (cell) applyMark(+cell.dataset.r, +cell.dataset.c);
  });
  window.addEventListener("pointerup", () => {
    dragging = false;
  });
}

function applyMark(r, c) {
  if (tool === "x") setX(r, c, true);
  else if (tool === "erase") {
    setX(r, c, false);
    delete state.notes[key(r, c)];
    const id = placedSuspectAt(r, c);
    if (id) delete state.placements[id];
    save();
    drawBoard();
    drawSuspects();
    drawTools();
  }
}

function onCellPlace(r, c) {
  const k = key(r, c);
  if (blockedSet().has(k) || oobSet().has(k)) return;
  pushHistory();
  const existing = placedSuspectAt(r, c);
  if (existing) {
    // clicking a token removes it
    delete state.placements[existing];
    save();
    rerender();
    return;
  }
  if (!selected) return;
  // remove any prior placement of this suspect, then place
  state.placements[selected] = [r, c];
  delete state.notes[k];
  save();
  rerender();
}

function toggleX(r, c) {
  pushHistory();
  setX(r, c, !state.xs.has(key(r, c)));
}
function setX(r, c, on) {
  if (placedSuspectAt(r, c)) return;
  const k = key(r, c);
  if (on) state.xs.add(k);
  else state.xs.delete(k);
  save();
  drawBoard();
}
function clearAll() {
  pushHistory();
  state.placements = {};
  state.xs = new Set();
  state.notes = {};
  save();
  rerender();
  toast("Board cleared");
}

function giveHint() {
  if (!P.solution) {
    toast("No solution available for hints");
    return;
  }
  // find a suspect not yet correctly placed; place them at their solution cell
  const wrong = P.suspects.filter((s) => {
    const sol = P.solution[s.id];
    const cur = state.placements[s.id];
    return !cur || cur[0] !== sol[0] || cur[1] !== sol[1];
  });
  if (!wrong.length) {
    toast("Everything is already correct!");
    return;
  }
  pushHistory();
  const s = wrong[0];
  const [r, c] = P.solution[s.id];
  // clear whoever is wrongly there
  const occ = placedSuspectAt(r, c);
  if (occ) delete state.placements[occ];
  state.placements[s.id] = [r, c];
  state.xs.delete(key(r, c));
  save();
  rerender();
  toast(`Hint: ${s.name} goes here`);
}

function submit() {
  if (!P.solution) {
    toast("This puzzle has no baked solution");
    return;
  }
  let correct = 0;
  for (const s of P.suspects) {
    const sol = P.solution[s.id];
    const cur = state.placements[s.id];
    if (cur && cur[0] === sol[0] && cur[1] === sol[1]) correct++;
  }
  const total = P.suspects.length;
  if (correct === total) {
    revealMurderer();
  } else {
    toast(`${correct} of ${total} placements correct — keep going!`);
  }
}

// ---- modals ----
function modal(html) {
  const root = document.getElementById("modal-root");
  root.innerHTML = `<div class="modal-bg"><div class="modal">${html}</div></div>`;
  root.querySelector(".modal-bg").addEventListener("click", (e) => {
    if (e.target.classList.contains("modal-bg")) root.innerHTML = "";
  });
  root.querySelectorAll("[data-close]").forEach((b) => b.addEventListener("click", () => (root.innerHTML = "")));
}

function revealMurderer() {
  const m = suspectById(P.murdererId);
  modal(`
    <div class="reveal-portrait">${avatarSVG(m)}</div>
    <div class="reveal-name">${m.name}</div>
    <p style="text-align:center">was alone with the victim. <b>Case solved!</b></p>
    <div style="display:flex;gap:10px;justify-content:center;margin-top:16px">
      <a class="btn" href="#/">More puzzles</a>
      <button class="btn ghost" data-close>Close</button>
    </div>`);
}

function showHowTo() {
  modal(`<h2>How to play</h2>
    <ul>
      <li><b>Select</b> a suspect (click their card), then <b>click a grid cell</b> to place them.</li>
      <li>Click a placed token again to remove it.</li>
      <li>Every placement <b>blocks its whole row and column</b> (shown with ✕).</li>
      <li><b>Right-click</b> a cell, or use the <b>✕ tool</b>, to mark cells you've ruled out. Drag to mark many.</li>
      <li>The <b>eraser</b> clears marks; <b>hold</b> it to wipe the whole board.</li>
      <li><b>💡 Hint</b> reveals one correct placement. <b>✓ Submit</b> checks your answer once everyone is placed.</li>
      <li>The killer is the one suspect <b>alone with the victim</b> in the same area.</li>
    </ul>
    <div style="text-align:right"><button class="btn" data-close>Got it</button></div>`);
}

let toastTimer;
function toast(msg) {
  let t = document.querySelector(".toast");
  if (!t) {
    t = document.createElement("div");
    t.className = "toast";
    document.body.appendChild(t);
  }
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("show"), 2200);
}
