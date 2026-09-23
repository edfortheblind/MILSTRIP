const panels = [...document.querySelectorAll('details')];
let printState = [];
function expandForPrint() {
  if (printState.length) return;
  printState = panels.map(panel => panel.open);
  panels.forEach(panel => { panel.open = true; });
}
function restoreAfterPrint() {
  panels.forEach((panel, index) => { panel.open = printState[index] ?? false; });
  printState = [];
}
window.addEventListener('beforeprint', expandForPrint);
window.addEventListener('afterprint', restoreAfterPrint);
document.getElementById('print-guide').addEventListener('click', () => window.print());
const viewer = document.getElementById('diagram-viewer');
document.querySelectorAll('[data-view-chart]').forEach(button => {
  button.addEventListener('click', () => {
    const figure = button.closest('figure');
    const svg = figure.querySelector('svg').cloneNode(true);
    // The modal is named by its heading; avoid duplicate inline SVG identifiers.
    svg.querySelectorAll('[id]').forEach(el => { el.id += '-viewer'; });
    svg.setAttribute('aria-labelledby', svg.getAttribute('aria-labelledby').split(' ').map(id => id + '-viewer').join(' '));
    svg.querySelectorAll('[marker-end]').forEach(el => {
      el.setAttribute('marker-end', el.getAttribute('marker-end').replace(')', '-viewer)'));
    });
    document.getElementById('viewer-title').textContent = figure.querySelector('figcaption').textContent;
    document.getElementById('viewer-content').replaceChildren(svg);
    viewer.showModal();
  });
});
document.getElementById('close-viewer').addEventListener('click', () => viewer.close());
