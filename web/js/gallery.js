import { listPuzzles } from "./puzzles.js";
import { puzzleThumb } from "./icons.js";

export async function renderGallery(view) {
  view.innerHTML = `<section class="gallery">
    <h1>Choose a case</h1>
    <p class="lead">A murder happened. Read each suspect's clue, place everyone on the grid
      (one per row, one per column), and the killer — alone with the victim — is revealed.</p>
    <div class="grid-cards" id="cards"><p style="color:#c7d2e6">Loading puzzles…</p></div>
  </section>`;

  const cards = view.querySelector("#cards");
  let puzzles;
  try {
    puzzles = await listPuzzles();
  } catch (e) {
    cards.innerHTML = `<p style="color:#f3c">Failed to load puzzles: ${e.message}</p>`;
    return;
  }
  if (!puzzles.length) {
    cards.innerHTML = `<p style="color:#c7d2e6">No puzzles yet. Run <code>murbo solve</code> on one.</p>`;
    return;
  }

  cards.innerHTML = "";
  for (const p of puzzles) {
    const diff = (p.difficulty || "medium").toLowerCase();
    const el = document.createElement("article");
    el.className = "pcard";
    el.innerHTML = `
      <div class="thumb" style="background:linear-gradient(135deg,#eef2fb,#dde6f6)">${puzzleThumb(p.theme)}</div>
      <div class="body">
        <p class="title">${p.title}</p>
        <div class="meta">
          <span class="chip ${diff}">${diff}</span>
          <span>${p.grid.cols}×${p.grid.rows}</span>
          <span>${p.suspectCount} suspects</span>
        </div>
      </div>`;
    el.addEventListener("click", () => {
      location.hash = `#/play/${p.id}`;
    });
    cards.appendChild(el);
  }
}
