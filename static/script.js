/* ─── Via point builder ────────────────────────────────────────── */

let viaCounter = 0;

function addVia(existingValue = "") {
  viaCounter++;
  const container = document.getElementById("via-container");
  const row = document.createElement("div");
  row.className = "via-row";
  row.id = `via-row-${viaCounter}`;

  const input = document.createElement("input");
  input.type        = "text";
  input.name        = "via[]";
  input.placeholder = `Via point ${viaCounter}  (e.g. Gangapur Chauraha)`;
  input.value       = existingValue;
  input.addEventListener("input", updatePreview);

  const btn = document.createElement("button");
  btn.type      = "button";
  btn.className = "remove-via";
  btn.title     = "Remove";
  btn.textContent = "✕";
  btn.onclick = () => { row.remove(); updatePreview(); };

  row.appendChild(input);
  row.appendChild(btn);
  container.appendChild(row);
  input.focus();
  updatePreview();
}

/* ─── Route preview ────────────────────────────────────────────── */

function updatePreview() {
  const startEl   = document.querySelector('[name="start_location"]');
  const previewEl = document.getElementById("route-preview-box");
  if (!startEl || !previewEl) return;

  const start = startEl.value.trim();
  if (!start) { previewEl.style.display = "none"; return; }

  const vias = [...document.querySelectorAll('[name="via[]"]')]
    .map(i => i.value.trim()).filter(Boolean);

  const parts = [start, ...vias, "College"];
  previewEl.textContent = parts.join(" → ");
  previewEl.style.display = "block";
}

/* ─── Update-ride option cards ──────────────────────────────────── */

function selectOption(choice) {
  document.querySelectorAll(".option-card").forEach(c => c.classList.remove("selected"));
  const card = document.getElementById("opt-" + choice);
  if (card) card.classList.add("selected");

  document.getElementById("edit-form").style.display =
    (choice === "update") ? "block" : "none";
}

/* ─── Init ──────────────────────────────────────────────────────── */

document.addEventListener("DOMContentLoaded", () => {
  // Hook up start-location input for live preview
  const startInput = document.querySelector('[name="start_location"]');
  if (startInput) startInput.addEventListener("input", updatePreview);

  // Pre-fill existing via points (used on update_ride page)
  const prefill = window.__VIA_PREFILL__ || [];
  prefill.forEach(val => addVia(val));
});
