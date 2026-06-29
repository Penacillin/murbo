import { renderGallery } from "./gallery.js";
import { renderGame } from "./game.js";
import { loadIconAssets } from "./icons.js";

const view = document.getElementById("view");

async function route() {
  const hash = location.hash || "#/";
  const m = hash.match(/^#\/play\/([a-z0-9-]+)/i);
  document.getElementById("modal-root").innerHTML = "";
  if (m) {
    await renderGame(view, m[1]);
  } else {
    await renderGallery(view);
  }
}

window.addEventListener("hashchange", route);
loadIconAssets().then(route);
