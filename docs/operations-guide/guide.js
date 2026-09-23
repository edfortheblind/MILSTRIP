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
    const visual = figure.querySelector('svg, img').cloneNode(true);
    // Only one visual is open; the suffix keeps its identifiers out of the page.
    if (visual.tagName.toLowerCase() === 'svg') {
      const ids = new Map([...visual.querySelectorAll('[id]')].map(el => [el.id, `${el.id}-viewer`]));
      if (visual.id) ids.set(visual.id, `${visual.id}-viewer`);
      [visual, ...visual.querySelectorAll('*')].forEach(el => {
        if (el.id) el.id = ids.get(el.id);
        ['aria-labelledby', 'aria-describedby'].forEach(attribute => {
          if (el.hasAttribute(attribute)) {
            el.setAttribute(attribute, el.getAttribute(attribute).split(/\s+/).map(id => ids.get(id) || id).join(' '));
          }
        });
        [...el.attributes].forEach(attribute => {
          const value = attribute.value.replace(/url\(#([^)]*)\)/g, (match, id) => ids.has(id) ? `url(#${ids.get(id)})` : match);
          if (value !== attribute.value) el.setAttribute(attribute.name, value);
        });
      });
    } else {
      visual.removeAttribute('id');
      visual.removeAttribute('loading');
    }
    document.getElementById('viewer-title').textContent = figure.querySelector('figcaption').textContent;
    document.getElementById('viewer-content').replaceChildren(visual);
    viewer.showModal();
  });
});
document.getElementById('close-viewer').addEventListener('click', () => viewer.close());
