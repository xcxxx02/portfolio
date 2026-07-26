const reduceMotion=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const revealItems=document.querySelectorAll('.reveal');
if(reduceMotion)revealItems.forEach(i=>i.classList.add('visible'));else{const observer=new IntersectionObserver(entries=>entries.forEach(e=>{if(e.isIntersecting){e.target.classList.add('visible');observer.unobserve(e.target)}}),{threshold:.14});revealItems.forEach(i=>observer.observe(i))}
document.querySelectorAll('.skill-row').forEach(row=>row.addEventListener('click',()=>{document.querySelectorAll('.skill-row').forEach(i=>i.classList.remove('active'));row.classList.add('active')}));
document.querySelectorAll('.project-trigger').forEach(trigger=>trigger.addEventListener('click',()=>{const row=trigger.closest('.project-row');const open=row.classList.toggle('expanded');trigger.setAttribute('aria-expanded',String(open));trigger.querySelector('b').textContent=open?'':'+'}));
const toast=document.querySelector('.toast');document.querySelector('#resume-button')?.addEventListener('click',()=>{toast.classList.add('show');window.setTimeout(()=>toast.classList.remove('show'),3200)});
document.querySelectorAll('a[href="#work"]').forEach(link=>link.addEventListener('click',event=>{const target=document.querySelector('#work');if(!target)return;event.preventDefault();target.scrollIntoView({behavior:reduceMotion?'auto':'smooth',block:'start'});history.replaceState(null,'' ,'#work')}));
const dot=document.querySelector('.cursor-dot'),ring=document.querySelector('.cursor-ring');
if(dot&&ring&&window.matchMedia('(pointer:fine)').matches&&!reduceMotion){window.addEventListener('pointermove',e=>{dot.style.opacity='1';ring.style.opacity='1';dot.style.left=e.clientX+'px';dot.style.top=e.clientY+'px';ring.animate({left:e.clientX+'px',top:e.clientY+'px'},{duration:160,fill:'forwards'})});document.querySelectorAll('a,button').forEach(i=>{i.addEventListener('pointerenter',()=>{ring.style.width='42px';ring.style.height='42px'});i.addEventListener('pointerleave',()=>{ring.style.width='28px';ring.style.height='28px'})})}

/* Context me builder */
(() => {
  const form = document.querySelector('#context-form');
  const dropzone = document.querySelector('#context-dropzone');
  const formFields = document.querySelector('#form-fields');
  const fieldStatus = document.querySelector('#field-status');
  const contextStatus = document.querySelector('#context-status');
  if (!form || !dropzone || !formFields) return;

  const definitions = {
    phone: { label: 'Phone number', type: 'tel', placeholder: '+60 12 345 6789' },
    company: { label: 'Company', type: 'text', placeholder: 'Your company' },
    subject: { label: 'Subject', type: 'text', placeholder: 'What can I help with?' },
    budget: { label: 'Budget range', type: 'select', options: ['Select a range', 'RM 1,000  RM 3,000', 'RM 3,000  RM 8,000', 'Let us discuss'] }
  };
  let draggedNode = null;

  function makeFieldNode(key) {
    const definition = definitions[key];
    const wrapper = document.createElement('div');
    wrapper.className = 'dynamic-field';
    wrapper.dataset.addedField = key;
    wrapper.draggable = false;
    const meta = document.createElement('div');
    meta.className = 'field-meta';
    const label = document.createElement('label');
    label.textContent = definition.label;
    const handle = document.createElement('span');
    handle.className = 'field-handle';
    handle.setAttribute('aria-hidden', 'true');
    handle.textContent = '';
    meta.append(label, handle);
    let input;
    if (definition.type === 'select') {
      input = document.createElement('select');
      definition.options.forEach((optionText, index) => {
        const option = document.createElement('option');
        option.value = index ? optionText : '';
        option.textContent = optionText;
        input.appendChild(option);
      });
    } else {
      input = document.createElement('input');
      input.type = definition.type;
      input.placeholder = definition.placeholder;
    }
    input.name = key;
    input.autocomplete = key === 'phone' ? 'tel' : 'organization';
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.className = 'remove-field';
    remove.setAttribute('aria-label', 'Remove ' + definition.label);
    remove.textContent = '';
    remove.addEventListener('click', () => {
      wrapper.remove();
      fieldStatus.textContent = 'Field removed  drag another field into the canvas';
    });
    wrapper.append(meta, input, remove);
    return wrapper;
  }

  function addField(key, target) {
    if (!definitions[key]) return;
    if (formFields.querySelector('[data-added-field="' + key + '"]')) {
      fieldStatus.textContent = definitions[key].label + ' is already in your form';
      return;
    }
    const wrapper = makeFieldNode(key);
    if (target && target.parentElement === formFields) formFields.insertBefore(wrapper, target);
    else formFields.appendChild(wrapper);
    fieldStatus.textContent = definitions[key].label + ' added  drag any field to reorder';
  }

  document.querySelectorAll('.field-chip').forEach((chip) => {
    chip.addEventListener('click', () => addField(chip.dataset.field));
    chip.addEventListener('dragstart', (event) => {
      event.dataTransfer.setData('text/plain', chip.dataset.field);
      chip.classList.add('dragging');
      draggedNode = null;
    });
    chip.addEventListener('dragend', () => chip.classList.remove('dragging'));
  });

  let pointerDrag = null;
  let pendingPointer = null;
  let pointerFrame = null;

  function animateReorder(previousPositions) {
    formFields.querySelectorAll('.form-field, .dynamic-field').forEach((item) => {
      if (item === pointerDrag?.node) return;
      const previous = previousPositions.get(item);
      if (!previous) return;
      const current = item.getBoundingClientRect();
      const delta = previous.top - current.top;
      if (Math.abs(delta) < 1) return;
      item.animate([{ transform: `translateY(${delta}px)` }, { transform: 'translateY(0)' }], {
        duration: 180,
        easing: 'cubic-bezier(.22,1,.36,1)'
      });
    });
  }

  function moveDropLine(clientY) {
    if (!pointerDrag?.line) return;
    const items = [...formFields.querySelectorAll('.form-field, .dynamic-field')].filter((item) => item !== pointerDrag.node);
    const target = items.find((item) => {
      const rect = item.getBoundingClientRect();
      return clientY < rect.top + rect.height / 2;
    });
    const anchor = target || null;
    if (anchor === pointerDrag.line || pointerDrag.line.nextSibling === anchor) return;
    const previousPositions = new Map(items.map((item) => [item, item.getBoundingClientRect()]));
    formFields.insertBefore(pointerDrag.line, anchor);
    animateReorder(previousPositions);
  }

  function beginPointerDrag(pending, event) {
    const { node, rect } = pending;
    const line = document.createElement('div');
    line.className = 'field-drop-line';
    line.style.setProperty('--drop-height', rect.height + 'px');
    formFields.insertBefore(line, node);
    pointerDrag = {
      node,
      line,
      pointerId: pending.pointerId,
      offsetY: event.clientY - rect.top,
      offsetX: event.clientX - rect.left
    };
    pendingPointer = null;
    node.classList.add('pointer-dragging');
    node.style.position = 'fixed';
    node.style.left = rect.left + 'px';
    node.style.top = rect.top + 'px';
    node.style.width = rect.width + 'px';
    node.style.zIndex = '8';
    node.style.pointerEvents = 'none';
    fieldStatus.textContent = 'Move the field to reorder';
  }

  function finishPointerDrag(cancelled = false) {
    if (!pointerDrag) return;
    const { node, line } = pointerDrag;
    if (cancelled) line.remove();
    else {
      formFields.insertBefore(node, line);
      line.remove();
    }
    node.style.position = '';
    node.style.left = '';
    node.style.top = '';
    node.style.width = '';
    node.style.zIndex = '';
    node.style.pointerEvents = '';
    node.classList.remove('pointer-dragging');
    fieldStatus.textContent = cancelled ? 'Drag cancelled' : 'Field order updated';
    pointerDrag = null;
  }

  formFields.addEventListener('pointerdown', (event) => {
    const node = event.target.closest('.form-field, .dynamic-field');
    const handle = event.target.closest('.field-handle');
    if (!node || (!handle && event.target.closest('input, textarea, select, button'))) return;
    if (event.button !== 0) return;
    event.preventDefault();
    pendingPointer = { node, pointerId: event.pointerId, startX: event.clientX, startY: event.clientY, rect: node.getBoundingClientRect() };
    node.setPointerCapture?.(event.pointerId);
  });

  formFields.addEventListener('pointermove', (event) => {
    if (pendingPointer && event.pointerId === pendingPointer.pointerId && !pointerDrag) {
      const moved = Math.hypot(event.clientX - pendingPointer.startX, event.clientY - pendingPointer.startY);
      if (moved < 6) return;
      beginPointerDrag(pendingPointer, event);
    }
    if (!pointerDrag || event.pointerId !== pointerDrag.pointerId) return;
    event.preventDefault();
    if (pointerFrame) cancelAnimationFrame(pointerFrame);
    pointerFrame = requestAnimationFrame(() => {
      pointerDrag.node.style.top = event.clientY - pointerDrag.offsetY + 'px';
      pointerDrag.node.style.left = event.clientX - pointerDrag.offsetX + 'px';
      moveDropLine(event.clientY);
    });
  });
  formFields.addEventListener('pointerup', (event) => {
    if (pendingPointer && event.pointerId === pendingPointer.pointerId) pendingPointer = null;
    if (pointerDrag && event.pointerId === pointerDrag.pointerId) finishPointerDrag();
  });
  formFields.addEventListener('pointercancel', () => {
    pendingPointer = null;
    finishPointerDrag(true);
  });
  dropzone.addEventListener('dragover', (event) => {
    event.preventDefault();
    dropzone.classList.add('dragover');
  });
  dropzone.addEventListener('dragleave', (event) => {
    if (!dropzone.contains(event.relatedTarget)) dropzone.classList.remove('dragover');
  });
  dropzone.addEventListener('drop', (event) => {
    event.preventDefault();
    dropzone.classList.remove('dragover');
    const key = event.dataTransfer.getData('text/plain');
    const target = event.target.closest('.form-field, .dynamic-field');
    if (definitions[key]) addField(key, target);
  });
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    contextStatus.className = 'context-status';
    if (!form.checkValidity()) {
      form.reportValidity();
      contextStatus.textContent = 'Please add your name, email and message.';
      contextStatus.classList.add('error');
      return;
    }
    const endpoint = form.dataset.endpoint.trim();
    const payload = Object.fromEntries(new FormData(form).entries());
    if (!endpoint) {
      contextStatus.textContent = 'Preview submitted  email delivery still needs to be connected.';
      contextStatus.classList.add('success');
      fieldStatus.textContent = 'Ready for an email endpoint';
      return;
    }
    const submitButton = form.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.textContent = 'Sending';
    try {
      const response = await fetch(endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, body: JSON.stringify(payload) });
      if (!response.ok) throw new Error('Request failed');
      form.reset();
      formFields.querySelectorAll('[data-added-field]').forEach((node) => node.remove());
      contextStatus.textContent = 'Message sent  thank you.';
      contextStatus.classList.add('success');
    } catch {
      contextStatus.textContent = 'Could not send right now. Please try again.';
      contextStatus.classList.add('error');
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = 'Send message ';
    }
  });
})();
// Scale the complete Malaysia Now page as one fixed-size group on compact screens.
(() => {
  const frame = document.querySelector('.project-row[data-project="malaysia-now"] iframe');
  const screen = frame?.closest('.macbook-screen');
  const compact = window.matchMedia('(max-width: 800px)').matches || navigator.maxTouchPoints > 0;
  if (!frame || !screen || !compact) return;

  const url = new URL(frame.getAttribute('src'), window.location.href);
  url.searchParams.set('mobile', '1');
  url.searchParams.set('mode', 'group');
  frame.setAttribute('src', url.pathname + url.search + url.hash);
  frame.classList.add('group-preview-frame');

  const fitGroup = () => {
    const artboardWidth = 1728;
    const availableWidth = Math.max(1, screen.clientWidth - 16);
    const scale = Math.min(1, availableWidth / artboardWidth) * 0.84;
    frame.style.width = artboardWidth + 'px';
    frame.style.height = '1177px';
    frame.style.transformOrigin = 'top left';
    frame.style.transform = 'scale(' + scale + ')';
    frame.style.marginLeft = Math.max(0, (screen.clientWidth - 16 - artboardWidth * scale) / 2) + 'px';
    screen.style.overflow = 'hidden';
  };
  fitGroup();
  if (window.ResizeObserver) new ResizeObserver(fitGroup).observe(screen);
})();