(() => {
  "use strict";
  const params = new URLSearchParams(location.search);
  const manifestUrl = params.get("manifest");
  const status = document.getElementById("viewer-status");
  const number = document.getElementById("canvas-number");
  const total = document.getElementById("canvas-total");
  const sourceLink = document.getElementById("institutional-source");
  const manifestLink = document.getElementById("manifest-link");
  let manifest;
  let viewer;

  const text = (languageMap, fallback = "") => {
    if (!languageMap) return fallback;
    const values = languageMap.en || languageMap.none || Object.values(languageMap)[0];
    return Array.isArray(values) ? values[0] : values || fallback;
  };
  const requestedCanvas = () => {
    const match = location.hash.match(/^#canvas=(\d+)$/);
    return Math.max(1, Number(match ? match[1] : params.get("canvas")) || 1);
  };
  const tileSource = (canvas) => {
    const body = canvas.items[0].items[0].body;
    const service = body.service && body.service[0];
    return service ? `${service.id}/info.json` : { type: "image", url: body.id };
  };
  const show = (requested) => {
    const index = Math.min(Math.max(1, requested), manifest.items.length);
    number.value = index;
    location.hash = `canvas=${index}`;
    viewer.open(tileSource(manifest.items[index - 1]));
    status.textContent = `${text(manifest.items[index - 1].label, `Image ${index}`)} — alignment may be ${text(manifest.metadata?.[0]?.value, "approximate")}.`;
    if (window.parent !== window) window.parent.postMessage({ type: "tc:canvas", canvas: index }, window.location.origin);
  };

  if (!manifestUrl) {
    status.textContent = "No manifest was specified. Return to a work and choose View facsimile.";
    return;
  }
  manifestLink.href = manifestUrl;
  fetch(manifestUrl).then((response) => {
    if (!response.ok) throw new Error(`Manifest request returned ${response.status}`);
    return response.json();
  }).then((data) => {
    manifest = data;
    document.getElementById("manifest-title").textContent = text(data.label, "Facsimile viewer");
    document.title = `${text(data.label, "Facsimile")} — Trithemius Corpus`;
    document.getElementById("required-statement").textContent = text(data.requiredStatement?.value, "Source attribution unavailable.");
    const homepage = data.homepage && data.homepage[0];
    sourceLink.href = homepage?.id || data.provider?.[0]?.id || manifestUrl;
    total.textContent = `of ${data.items.length}`;
    number.max = data.items.length;
    viewer = OpenSeadragon({ id: "openseadragon", prefixUrl: "https://cdn.jsdelivr.net/npm/openseadragon@6.0.2/build/openseadragon/images/", showNavigator: true, sequenceMode: false });
    show(requestedCanvas());
  }).catch((error) => {
    status.textContent = `The image service is unavailable: ${error.message}. The readable text remains available in the corpus.`;
    sourceLink.hidden = false;
  });
  document.getElementById("previous-canvas").addEventListener("click", () => show(Number(number.value) - 1));
  document.getElementById("next-canvas").addEventListener("click", () => show(Number(number.value) + 1));
  number.addEventListener("change", () => show(Number(number.value)));
  window.addEventListener("hashchange", () => { if (manifest && Number(number.value) !== requestedCanvas()) show(requestedCanvas()); });
})();
