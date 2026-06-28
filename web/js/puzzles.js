// Puzzle data loading. Tries the live API (`murbo serve`), falls back to the static
// manifest (for `python -m http.server` or file hosting).

export async function listPuzzles() {
  try {
    const r = await fetch("api/puzzles", { cache: "no-store" });
    if (r.ok) return (await r.json()).puzzles;
  } catch {
    /* fall through to manifest */
  }
  const r = await fetch("puzzles/manifest.json", { cache: "no-store" });
  if (!r.ok) throw new Error("could not load puzzle list");
  return (await r.json()).puzzles;
}

export async function loadPuzzle(id) {
  const r = await fetch(`puzzles/${id}.json`, { cache: "no-store" });
  if (!r.ok) throw new Error(`puzzle ${id} not found`);
  return r.json();
}
