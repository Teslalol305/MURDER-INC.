// Small DOM helpers shared by the HUD and the menus, and the two brand components: the IPX mark and the
// route bullet.

const SVG_NS = 'http://www.w3.org/2000/svg';

/** el('div', 'card', 'text') or el('button', {class, type, 'aria-label': …}, child, child…). */
export function el(tag, props, ...children) {
  const node = document.createElement(tag);
  if (typeof props === 'string') node.className = props;
  else if (props) {
    for (const key in props) {
      const value = props[key];
      if (value === undefined || value === null || value === false) continue;
      if (key === 'class') node.className = value;
      else if (key === 'text') node.textContent = value;
      else node.setAttribute(key, value === true ? '' : value);
    }
  }
  for (const child of children) {
    if (child === undefined || child === null || child === false) continue;
    node.append(child);
  }
  return node;
}

/** svg('svg', {viewBox: '0 0 10 10'}, svg('path', {d: …})) */
export function svg(tag, attrs, ...children) {
  const node = document.createElementNS(SVG_NS, tag);
  if (attrs) for (const key in attrs) node.setAttribute(key, attrs[key]);
  for (const child of children) if (child) node.append(child);
  return node;
}

/** Writes text only when it changed. Returns true when it did. */
export function setText(node, text) {
  if (node.__text === text) return false;
  node.__text = text;
  node.textContent = text;
  return true;
}

/** Toggles a class only when the state changed (keyed per node and class). */
export function setClass(node, name, on) {
  const key = `__c_${name}`;
  on = !!on;
  if (node[key] === on) return;
  node[key] = on;
  node.classList.toggle(name, on);
}

/** Sets an inline style property only when the value changed. */
export function setStyle(node, prop, value) {
  const key = `__s_${prop}`;
  if (node[key] === value) return;
  node[key] = value;
  if (prop.startsWith('--')) node.style.setProperty(prop, value);
  else node.style[prop] = value;
}

/**
 * The IPX mark: one component for every place the presenter appears. Typeset until the real logo
 * arrives (see `.ipx-mark` in base.css); `extra` adds size classes.
 */
export function ipxMark(brand, extra = '') {
  return el('span', { class: `ipx-mark${extra ? ` ${extra}` : ''}`, role: 'img', 'aria-label': brand.ipx.wordmark }, brand.ipx.wordmark);
}

/**
 * A route bullet: the reels are lines 1, 2 and 3, the truck is "IPX". `data-line` picks the colour,
 * the class `is-done` fills it.
 */
export function bullet(code, extra = '') {
  const wide = String(code).length > 1;
  return el('span', { class: `rb${wide ? ' rb-wide' : ''}${extra ? ` ${extra}` : ''}`, 'data-line': String(code).toLowerCase() }, String(code));
}

const kebab = (s) => s.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`);

/**
 * Feeds the brand tokens of src/config/brand.js to the page as CSS custom properties (`colors.plateEdge`
 * → `--c-plate-edge`, `fonts.ui` → `--font-ui`), so a new palette only has to be dropped into that file.
 */
export function applyBrand(brand, root = document.documentElement) {
  if (!brand || !root || !root.style) return;
  for (const [name, value] of Object.entries(brand.colors || {})) root.style.setProperty(`--c-${kebab(name)}`, value);
  for (const [name, value] of Object.entries(brand.fonts || {})) root.style.setProperty(`--font-${kebab(name)}`, value);
}

/** True when the user asked the system for less motion. */
export function reducedMotion() {
  try {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  } catch {
    return false;
  }
}
