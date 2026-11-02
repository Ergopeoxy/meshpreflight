// The browser side of the interface. It holds no mesh logic: it collects input, calls the
// JSON routes in app.py, and draws the responses. Text from uploaded files, such as tag
// names, is only ever inserted through textContent so a crafted file can't inject a script.
"use strict";

const $ = (id) => document.getElementById(id);
let catalog = null;
let qualityPlots = {};
let qualityInfo = {};

/** Create an element with text and optional class. */
function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined && text !== null) node.textContent = text;
  if (className) node.className = className;
  return node;
}

/** Format a number compactly, keeping very large and small values readable. */
function fmt(value) {
  if (value === null || value === undefined) return "n/a";
  if (value === 0) return "0";
  const size = Math.abs(value);
  return size >= 1e6 || size < 1e-3 ? value.toExponential(3) : String(Number(value.toPrecision(6)));
}

function setStatus(message, isError = false) {
  $("status").textContent = message;
  $("status").className = isError ? "status error" : "status";
}

/** Plotly should use the page's theme colours, so charts work in light and dark mode. */
function drawPlot(id, figure) {
  const style = getComputedStyle(document.documentElement);
  const text = style.getPropertyValue("--text").trim();
  const line = style.getPropertyValue("--line").trim();
  const axis = { color: text, gridcolor: line, zerolinecolor: line };
  const layout = {
    ...figure.layout,
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { color: text },
  };
  ["xaxis", "yaxis", "xaxis2", "yaxis2", "xaxis3", "yaxis3"].forEach((key) => {
    if (layout[key]) layout[key] = { ...layout[key], ...axis };
  });
  if (layout.scene) {
    layout.scene = { ...layout.scene };
    ["xaxis", "yaxis", "zaxis"].forEach((key) => {
      layout.scene[key] = { ...(layout.scene[key] || {}), ...axis, showbackground: false };
    });
  }
  // Only the 3D view needs its toolbar; on the flat charts it would cover the legend.
  const config = { responsive: true, displaylogo: false, displayModeBar: id === "mesh-plot" };
  return Plotly.react($(id), figure.data, layout, config);
}

const VERDICTS = {
  errors: ["Problems found", "Don't trust results from this mesh until these are resolved."],
  warnings: ["Worth a look", "Nothing is definitely broken, but review the warnings below."],
  no_problems_found: ["No problems found by the checks that ran", "This doesn't prove the mesh is correct. See Coverage below for what was checked."],
};

function renderFindings(findings) {
  const box = $("findings");
  box.replaceChildren();
  if (!findings.length) {
    box.append(el("p", "No findings.", "muted"));
    return;
  }
  findings.forEach((finding) => {
    const item = el("div", null, `finding ${finding.severity}`);
    const head = el("div");
    head.append(el("span", finding.severity, `badge ${finding.severity}`), el("span", finding.code, "code"));
    item.append(head, el("p", finding.message));
    if (finding.hint) item.append(el("p", `What to do: ${finding.hint}`, "muted"));
    box.append(item);
  });
}

function renderStats(data) {
  const m = data.measurements;
  const box = $("stats");
  box.replaceChildren();
  const cells = Object.entries(m.n_cells).map(([kind, count]) => `${count} ${kind}`).join(", ");
  const add = (value, label, warning) => {
    const stat = el("div", null, "stat");
    stat.append(el("b", value), el("span", label));
    if (warning) stat.append(el("em", `Not trusted: ${warning}`));
    box.append(stat);
  };
  add(m.domain, "Mesh type");
  add(fmt(m.n_points), "Points");
  add(cells || "none", "Cells");
  if (m.volume.value !== null) add(fmt(m.volume.value), "Volume", m.volume.trusted ? "" : m.volume.reason);
  if (m.area.value !== null) add(fmt(m.area.value), "Area", m.area.trusted ? "" : m.area.reason);
  add(fmt(m.extent), "Largest extent");
}

function renderTagTable(data) {
  const table = $("tag-table");
  table.replaceChildren();
  const rows = data.measurements.tags;
  const expected = data.expected ? data.expected.tags : {};
  const showExpected = Object.keys(expected).length > 0;
  if (!rows.length) {
    table.append(el("caption", "This mesh has no tags.", "muted"));
    $("tag-plot").style.display = "none";
    return;
  }
  $("tag-plot").style.display = "";
  const head = document.createElement("tr");
  const titles = ["Name", "Dim", "Tag number", "Cells", "Measured size"].concat(showExpected ? ["Exact size"] : []);
  titles.forEach((title, i) => head.append(el("th", title, i > 0 ? "num" : "")));
  const thead = document.createElement("thead");
  thead.append(head);
  const tbody = document.createElement("tbody");
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    tr.append(el("td", row.name || "(no name)"), el("td", row.dim, "num"), el("td", row.id, "num"),
      el("td", row.cells, "num"), el("td", fmt(row.measure), "num"));
    if (showExpected) tr.append(el("td", row.name && expected[row.name] ? fmt(expected[row.name].measure) : "n/a", "num"));
    tbody.append(tr);
  });
  table.append(thead, tbody);
}

function renderQuality(data) {
  qualityPlots = data.plots.quality;
  qualityInfo = data.quality;
  const select = $("quality-metric");
  select.replaceChildren();
  Object.entries(qualityInfo).forEach(([key, info]) => {
    const option = el("option", info.label);
    option.value = key;
    select.append(option);
  });
  showQualityMetric();
}

function showQualityMetric() {
  const key = $("quality-metric").value;
  if (!key) return;
  const info = qualityInfo[key];
  $("quality-meaning").textContent =
    `${info.meaning} Lowest here: ${fmt(info.min)}, average: ${fmt(info.mean)}. These scores flag broken cells, but passing doesn't guarantee accuracy.`;
  drawPlot("quality-plot", qualityPlots[key]);
}

function renderCoverage(data) {
  $("coverage").textContent = `${data.checks_run.length} checks ran. ${Object.keys(data.checks_skipped).length} did not apply to this mesh or had nothing to compare against:`;
  const list = $("skipped");
  list.replaceChildren();
  Object.entries(data.checks_skipped).forEach(([id, reason]) => list.append(el("li", `${id}: ${reason}`)));
  data.notes.forEach((note) => list.append(el("li", `Reader note: ${note}`)));
}

function renderResults(data) {
  const verdict = $("verdict");
  const [title, detail] = VERDICTS[data.status];
  verdict.className = `verdict ${data.status}`;
  verdict.replaceChildren(document.createTextNode(`${title}: ${data.source}`), el("small", detail));
  $("results").hidden = false;
  renderStats(data);
  renderFindings(data.findings);
  renderTagTable(data);
  renderQuality(data);
  renderCoverage(data);
  drawPlot("mesh-plot", data.plots.mesh);
  if (data.measurements.tags.length) drawPlot("tag-plot", data.plots.tags);
}

/** Call a JSON route, showing progress and turning failures into a readable message. */
async function callApi(url, options, button) {
  setStatus("Working...");
  if (button) button.disabled = true;
  try {
    const response = await fetch(url, options);
    const data = await response.json().catch(() => ({ error: `The server returned an error (${response.status}).` }));
    if (!response.ok) throw new Error(data.error || `Request failed (${response.status}).`);
    setStatus("");
    return data;
  } catch (error) {
    setStatus(error.message, true);
    return null;
  } finally {
    if (button) button.disabled = false;
  }
}

function fillDefects() {
  const shape = catalog.shapes.find((s) => s.name === $("demo-shape").value);
  const select = $("demo-defect");
  const previous = select.value;
  select.replaceChildren();
  const none = el("option", "None: a clean mesh");
  none.value = "";
  select.append(none);
  shape.defects.forEach((name) => {
    const option = el("option", name.replaceAll("_", " "));
    option.value = name;
    select.append(option);
  });
  if (shape.defects.includes(previous)) select.value = previous;
  describeDefect();
  updateDownloadLink();
}

function describeDefect() {
  const defect = catalog.defects.find((d) => d.name === $("demo-defect").value);
  const shape = catalog.shapes.find((s) => s.name === $("demo-shape").value);
  $("demo-defect-label").textContent = defect ? defect.label : shape.label;
}

function updateDownloadLink() {
  const query = new URLSearchParams({ shape: $("demo-shape").value, level: $("demo-level").value });
  $("demo-download").href = `/api/demo/download?${query}`;
}

async function runDemo(event) {
  if (event) event.preventDefault();
  const defect = $("demo-defect").value;
  const body = { shape: $("demo-shape").value, level: Number($("demo-level").value), defects: defect ? [defect] : [] };
  const data = await callApi("/api/demo", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }, event ? event.submitter : null);
  if (data) renderResults(data);
}

function addTagRow(name = "", dim = "2", size = "") {
  const tr = document.createElement("tr");
  const nameInput = Object.assign(el("input"), { value: name, placeholder: "inlet", className: "tag-name" });
  nameInput.setAttribute("aria-label", "Tag name");
  const dimSelect = el("select", null, "tag-dim");
  dimSelect.setAttribute("aria-label", "Dimension");
  [["1", "1: curve"], ["2", "2: surface"], ["3", "3: solid"]].forEach(([value, label]) => {
    const option = el("option", label);
    option.value = value;
    dimSelect.append(option);
  });
  dimSelect.value = dim;
  const sizeInput = Object.assign(el("input"), { type: "number", step: "any", min: "0", value: size, className: "tag-size" });
  sizeInput.setAttribute("aria-label", "Expected size");
  const remove = el("button", "Remove", "remove");
  remove.type = "button";
  remove.addEventListener("click", () => tr.remove());
  [nameInput, dimSelect, sizeInput, remove].forEach((node) => {
    const td = document.createElement("td");
    td.append(node);
    tr.append(td);
  });
  $("tag-rows").append(tr);
}

async function runFile(event) {
  event.preventDefault();
  const file = $("file-input").files[0];
  if (!file) return setStatus("Choose a file first.", true);
  const form = new FormData();
  form.append("file", file);
  const tags = [...document.querySelectorAll("#tag-rows tr")].map((row) => ({
    name: row.querySelector(".tag-name").value,
    dim: Number(row.querySelector(".tag-dim").value),
    measure: row.querySelector(".tag-size").value,
  }));
  form.append("tags", JSON.stringify(tags));
  form.append("volume", $("exp-volume").value);
  form.append("area", $("exp-area").value);
  form.append("size", $("exp-size").value);
  form.append("rel_tol", $("exp-tol").value);
  const data = await callApi("/api/analyze", { method: "POST", body: form }, event.submitter);
  if (data) renderResults(data);
}

async function runValidation() {
  const button = $("run-validation");
  const output = $("validation-output");
  const data = await callApi("/api/validation", {}, button);
  if (!data) return;
  output.replaceChildren();
  const allPassed = data.passed === data.total;
  const banner = el("div", `${data.passed} of ${data.total} tests passed`, `verdict ${allPassed ? "no_problems_found" : "errors"}`);
  banner.style.marginTop = "14px";
  output.append(banner);
  Object.entries(data.categories).forEach(([name, totals]) => {
    const row = el("div", null, "category");
    row.append(el("span", name), el("b", `${totals.passed} / ${totals.total}`));
    output.append(row);
  });
  const demo = data.lost_tag;
  const callout = el("div", null, "callout");
  callout.append(
    el("b", "Why tags matter"),
    el("p", `Solving a heat problem with one boundary tag missing raises no error, but the answer is ${demo.times_worse.toFixed(0)} times less accurate (error ${fmt(demo.error_without_top_tag)} instead of ${fmt(demo.error_with_all_tags)}). This tool reports it as: ${demo.preflight_codes.join(", ")}.`)
  );
  output.append(callout);
  output.append(el("h3", "Do errors shrink at the rate theory predicts?"));
  output.append(el("p", "Each dotted line has the slope theory predicts, so a solid line running parallel to it is a pass.", "muted"));
  const plot = el("div", null, "plot");
  plot.id = "convergence-plot";
  output.append(plot);
  drawPlot("convergence-plot", data.convergence_plot);

  const details = document.createElement("details");
  details.append(el("summary", "Every test"));
  const scroll = el("div", null, "scroll");
  const table = document.createElement("table");
  const head = document.createElement("tr");
  ["Result", "Test", "Expected", "Actual", "Source of truth"].forEach((title) => head.append(el("th", title)));
  table.append(head);
  data.cases.forEach((item) => {
    const tr = document.createElement("tr");
    const result = document.createElement("td");
    result.append(el("span", item.passed ? "pass" : "fail", `badge ${item.passed ? "ok" : "error"}`));
    tr.append(result, el("td", item.name), el("td", item.expected), el("td", item.actual), el("td", item.source));
    table.append(tr);
  });
  scroll.append(table);
  details.append(scroll);
  output.append(details);
}

function renderChecks() {
  const box = $("check-list");
  box.replaceChildren();
  catalog.checks.forEach((check) => {
    const item = el("div", null, "check-item");
    item.append(el("b", check.title), document.createTextNode(" "), el("code", check.id), el("p", check.description));
    box.append(item);
  });
}

function switchTab(button) {
  document.querySelectorAll(".tab").forEach((tab) => {
    const active = tab === button;
    tab.classList.toggle("active", active);
    tab.setAttribute("aria-selected", String(active));
    $(`tab-${tab.dataset.tab}`).hidden = !active;
  });
  const name = button.dataset.tab;
  // Results belong to the demo and file tabs; the other tabs have their own content.
  $("results").hidden = name === "validation" || name === "checks" || !$("verdict").textContent;
  if (name !== "demo" && name !== "file") setStatus("");
}

async function init() {
  document.querySelectorAll(".tab").forEach((tab) => tab.addEventListener("click", () => switchTab(tab)));
  $("demo-form").addEventListener("submit", runDemo);
  $("demo-shape").addEventListener("change", fillDefects);
  $("demo-defect").addEventListener("change", describeDefect);
  $("demo-level").addEventListener("input", updateDownloadLink);
  $("file-form").addEventListener("submit", runFile);
  $("add-tag").addEventListener("click", () => addTagRow());
  $("run-validation").addEventListener("click", runValidation);
  $("quality-metric").addEventListener("change", showQualityMetric);

  catalog = await callApi("/api/catalog");
  if (!catalog) return;
  catalog.shapes.forEach((shape) => {
    const option = el("option", shape.name);
    option.value = shape.name;
    $("demo-shape").append(option);
  });
  $("demo-shape").value = "cylinder";
  fillDefects();
  $("demo-defect").value = "drop_tag";
  describeDefect();
  addTagRow();
  renderChecks();
  runDemo();
}

init();
