/* SVG-based 2D Cross-Section Renderer */

class CrossSectionView {
  constructor(containerEl) {
    this.container = containerEl;
    this.svg = null;
  }

  update(data) {
    this.container.innerHTML = '';
    if (!data || !data.outline || data.outline.length < 3) {
      this.container.innerHTML = '<div style="padding:12px;color:#999;font-size:12px;">No cross-section data</div>';
      return;
    }

    const outline = data.outline;
    const bars = data.bars || [];

    // Compute bounds
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    outline.forEach(([x, y]) => {
      minX = Math.min(minX, x); minY = Math.min(minY, y);
      maxX = Math.max(maxX, x); maxY = Math.max(maxY, y);
    });

    const padding = 20;
    const w = this.container.clientWidth || 400;
    const h = this.container.clientHeight || 140;
    const dataW = maxX - minX || 1;
    const dataH = maxY - minY || 1;
    const scaleX = (w - padding * 2) / dataW;
    const scaleY = (h - padding * 2) / dataH;
    const scale = Math.min(scaleX, scaleY);

    const offsetX = padding + (w - padding * 2 - dataW * scale) / 2 - minX * scale;
    const offsetY = padding + (h - padding * 2 - dataH * scale) / 2 - minY * scale;

    const tx = (x) => offsetX + x * scale;
    const ty = (y) => h - (offsetY + y * scale); // flip Y for SVG

    // Build SVG
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', w);
    svg.setAttribute('height', h);
    svg.style.display = 'block';

    // Concrete outline
    const points = outline.map(([x, y]) => `${tx(x)},${ty(y)}`).join(' ');
    const poly = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
    poly.setAttribute('points', points);
    poly.setAttribute('fill', '#d4d8dd');
    poly.setAttribute('stroke', '#555');
    poly.setAttribute('stroke-width', '2');
    svg.appendChild(poly);

    // Dimension labels
    this._addDimLabel(svg, tx(minX), ty(minY) + 14, tx(maxX), ty(minY) + 14, `${dataW}"`);
    this._addDimLabel(svg, tx(maxX) + 8, ty(maxY), tx(maxX) + 8, ty(minY), `${dataH}"`);

    // Rebar circles
    bars.forEach(bar => {
      const cx = tx(bar.x);
      const cy = ty(bar.y);
      const r = Math.max(bar.diameter * scale / 2, 3); // min 3px radius

      const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      circle.setAttribute('cx', cx);
      circle.setAttribute('cy', cy);
      circle.setAttribute('r', r);
      circle.setAttribute('fill', bar.color || '#e74c3c');
      circle.setAttribute('stroke', '#333');
      circle.setAttribute('stroke-width', '1');
      svg.appendChild(circle);

      // Label
      if (bar.label) {
        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', cx);
        text.setAttribute('y', cy - r - 3);
        text.setAttribute('text-anchor', 'middle');
        text.setAttribute('font-size', '9');
        text.setAttribute('fill', '#333');
        text.textContent = bar.label;
        svg.appendChild(text);
      }
    });

    this.container.appendChild(svg);
  }

  _addDimLabel(svg, x1, y1, x2, y2, label) {
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', x1); line.setAttribute('y1', y1);
    line.setAttribute('x2', x2); line.setAttribute('y2', y2);
    line.setAttribute('stroke', '#999'); line.setAttribute('stroke-width', '1');
    svg.appendChild(line);

    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    text.setAttribute('x', (x1 + x2) / 2);
    text.setAttribute('y', (y1 + y2) / 2 - 3);
    text.setAttribute('text-anchor', 'middle');
    text.setAttribute('font-size', '10');
    text.setAttribute('fill', '#666');
    text.textContent = label;
    svg.appendChild(text);
  }
}

window.CrossSectionView = CrossSectionView;
