const $ = (q) => document.querySelector(q);
const $$ = (q) => [...document.querySelectorAll(q)];
const state = { documents: [], portals: [], chats: [], currentChatId: null, selectedVehicles: [], questionBank: [], predefinedQuestion: null };
const FALLBACK = 'Sorry, I have no information about it.';
const CHAT_STORAGE_KEY = 'autosaarthi.chat-history.v1';

function escapeHtml(s='') { return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function knownValue(value) {
  const text = String(value ?? '').trim();
  return /^(?:not stated|not specified|unknown|n\/?a|none|not confirmed|)$/i.test(text) ? '' : text;
}
function knownTags(d) {
  const fields = [['Variant', d.variant], ['Body type', d.body_type], ['Fuel', d.fuel_type], ['Market', d.market]];
  const tags = fields.filter(([, value]) => knownValue(value)).map(([label, value]) => `${label}: ${knownValue(value)}`);
  if (d.active_in_india === 'yes') tags.push('Current in India');
  else if (d.active_in_india === 'archive') tags.push('Archive');
  return tags;
}

function saveChatHistory() {
  try {
    state.chats = state.chats.slice(0, 30).map(chat => ({ ...chat, messages: (chat.messages || []).slice(-80) }));
    localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify({ currentChatId: state.currentChatId, chats: state.chats }));
  } catch { /* Browser storage can be disabled or full; the current chat still works in memory. */ }
}

function renderChatHistory() {
  const list = $('#chat-history');
  if (!state.chats.length) {
    list.innerHTML = '<div class="history-empty">Your conversations will appear here.</div>';
    return;
  }
  list.replaceChildren();
  state.chats.forEach(chat => {
    const row = document.createElement('div'); row.className = `history-row${chat.id === state.currentChatId ? ' active' : ''}`;
    const select = document.createElement('button'); select.type = 'button'; select.className = 'history-select'; select.textContent = chat.title || 'New chat'; select.title = chat.title || 'New chat';
    select.addEventListener('click', () => openChat(chat.id));
    const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'history-remove'; remove.textContent = '×'; remove.title = 'Delete this chat'; remove.setAttribute('aria-label', `Delete ${chat.title || 'chat'}`);
    remove.addEventListener('click', () => deleteChat(chat.id));
    row.append(select, remove); list.append(row);
  });
}

function showWelcome() {
  $('#messages').replaceChildren();
  appendMessage('assistant', 'Hello! Welcome to AutoSaarthi.');
}

function openChat(id) {
  const chat = state.chats.find(item => item.id === id);
  if (!chat) return;
  state.currentChatId = id; saveChatHistory(); renderChatHistory();
  $('#messages').replaceChildren();
  if (chat.messages?.length) chat.messages.forEach(message => appendMessage(message.role, message.text, message.sources || []));
  else showWelcome();
}

function startNewChat() {
  const id = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  state.chats.unshift({ id, title: 'New chat', updatedAt: Date.now(), messages: [] });
  state.currentChatId = id; saveChatHistory(); renderChatHistory(); showWelcome(); $('#question').focus();
}

function deleteChat(id) {
  state.chats = state.chats.filter(chat => chat.id !== id);
  if (state.currentChatId === id) {
    state.currentChatId = state.chats[0]?.id || null;
    if (state.currentChatId) openChat(state.currentChatId);
    else startNewChat();
  }
  saveChatHistory(); renderChatHistory();
}

function recordMessage(role, text, sources = [], chatId = state.currentChatId) {
  const chat = state.chats.find(item => item.id === chatId);
  if (!chat) return;
  state.chats = [chat, ...state.chats.filter(item => item.id !== chatId)];
  chat.messages.push({ role, text, sources }); chat.updatedAt = Date.now();
  if (role === 'user' && chat.title === 'New chat') chat.title = text.trim().replace(/\s+/g, ' ').slice(0, 42) || 'New chat';
  saveChatHistory(); renderChatHistory();
  if (chatId === state.currentChatId) appendMessage(role, text, sources);
}

function initializeChatHistory() {
  try {
    const saved = JSON.parse(localStorage.getItem(CHAT_STORAGE_KEY) || '{}');
    if (Array.isArray(saved.chats)) state.chats = saved.chats.filter(chat => chat && typeof chat.id === 'string' && Array.isArray(chat.messages));
    if (state.chats.some(chat => chat.id === saved.currentChatId)) state.currentChatId = saved.currentChatId;
  } catch { state.chats = []; }
  renderChatHistory();
  if (state.currentChatId) openChat(state.currentChatId);
  else startNewChat();
}
$('#new-chat').addEventListener('click', startNewChat);
$('#mini-library').addEventListener('click', event => {
  const button = event.target.closest('.mini-car-name');
  if (!button) return;
  const key = button.dataset.key;
  const selected = state.selectedVehicles.find(vehicle => vehicle.key === key);
  if (selected) state.selectedVehicles = state.selectedVehicles.filter(vehicle => vehicle.key !== key);
  else {
    const docs = state.documents.filter(doc => `${doc.brand}|${doc.model}` === key);
    if (docs.length) state.selectedVehicles.push({key, brand:docs[0].brand, model:docs[0].model, docIds:docs.map(doc=>doc.doc_id)});
  }
  renderLibrary($('#library-search').value);
  renderSelectedBrochures();
  renderQuestionBank();
});
$('#selected-brochures').addEventListener('click', event => {
  const remove = event.target.closest('[data-remove-brochure]');
  if (!remove) return;
  state.selectedVehicles = state.selectedVehicles.filter(vehicle => vehicle.key !== remove.dataset.removeBrochure);
  renderLibrary($('#library-search').value);
  renderSelectedBrochures();
  renderQuestionBank();
});

function renderQuestionBank() {
  const list = $('#question-bank-list');
  if (!list) return;
  const term = ($('#question-bank-search')?.value || '').trim().toLowerCase();
  const category = $('#question-bank-category')?.value || '';
  const cars = state.selectedVehicles
    .filter(vehicle => state.documents.some(doc => doc.built_in && doc.brand === vehicle.brand && doc.model === vehicle.model))
    .map(vehicle => `${vehicle.brand} ${vehicle.model}`);
  const questions = state.questionBank.flatMap(group => (group.questions || []).map(question => ({...question, category:group.category})))
    .filter(question => (!category || question.category === category) && (!term || `${question.category} ${question.prompt}`.toLowerCase().includes(term)));
  list.replaceChildren();
  if (!questions.length) {
    const empty = document.createElement('div'); empty.className = 'question-bank-empty';
    empty.textContent = state.questionBank.length ? 'No question starters match that search.' : 'Question starters are loading…'; list.append(empty); return;
  }
  questions.forEach(question => {
    const button = document.createElement('button'); button.type = 'button'; button.className = 'question-bank-item'; button.setAttribute('role','listitem');
    const preview = question.prompt.replace('{car1}', cars[0] || 'first car').replace('{car2}', cars[1] || 'second car').replace('{car}', cars[0] || 'your selected car');
    const enoughCars = cars.length >= question.vehicles;
    button.disabled = !enoughCars;
    button.title = enoughCars ? 'Use this question' : `Select ${question.vehicles} ${question.vehicles === 1 ? 'car' : 'cars'} in Vehicle Coverage first`;
    const label = document.createElement('span'); label.className = 'question-bank-category-label'; label.textContent = question.category;
    const text = document.createElement('span'); text.className = 'question-bank-prompt'; text.textContent = preview;
    button.append(label,text);
    button.addEventListener('click', () => {
      if (!enoughCars) {
        $('#question-bank-help').textContent = `Select ${question.vehicles} ${question.vehicles === 1 ? 'car' : 'cars'} from Vehicle Coverage, then choose this question.`;
        return;
      }
      const prompt = question.prompt.replace('{car1}', cars[0] || '').replace('{car2}', cars[1] || '').replace('{car}', cars[0] || '');
      const field = $('#question'); field.value = prompt; field.focus();
      state.predefinedQuestion = {id:question.id,text:prompt};
      $('#question-bank-help').textContent = 'Ready. This question will search matching brochures from the built-in library.';
      $('#question-library').open = false;
      $('#chat-form').requestSubmit();
    });
    list.append(button);
  });
}

async function loadQuestionBank() {
  const help = $('#question-bank-help');
  try {
    const response = await fetch('/api/question-bank');
    if (!response.ok) throw new Error('Could not load the question starters.');
    state.questionBank = await response.json();
    const categorySelect = $('#question-bank-category');
    state.questionBank.forEach(group => {
      const option = document.createElement('option'); option.value = group.category; option.textContent = group.category; categorySelect.append(option);
    });
    const count = state.questionBank.reduce((total, group) => total + (group.questions || []).length, 0);
    $('#question-bank-count').textContent = `${count} ready-made questions`;
    $('#question-bank-search').placeholder = `Search ${count} question starters`;
    help.textContent = 'Select one car in Vehicle Coverage first, or select two cars for a comparison. These questions search the built-in brochure library.';
    renderQuestionBank();
  } catch (error) {
    help.textContent = error.message;
  }
}

function setTab(name) {
  $$('.tab').forEach(b => b.classList.toggle('active', b.dataset.tab === name));
  $$('.view').forEach(v => v.classList.toggle('active', v.id === `view-${name}`));
}
$$('.tab').forEach(b => b.addEventListener('click', () => setTab(b.dataset.tab)));
$$('[data-tab-link]').forEach(b => b.addEventListener('click', () => setTab(b.dataset.tabLink)));

function coverageText(status) { return status === 'yes' ? 'current in India' : status === 'archive' ? 'user-marked archive' : 'India status unconfirmed'; }
function renderLibrary(filter='') {
  const term = filter.toLowerCase();
  const docs = state.documents.filter(d => `${d.brand} ${d.model} ${d.model_year} ${d.variant}`.toLowerCase().includes(term));
  const unique = new Map();
  docs.forEach(d => {
    const key = `${d.brand}|${d.model}`;
    if (!unique.has(key)) unique.set(key, {key, brand:d.brand, model:d.model, docs:[]});
    unique.get(key).docs.push(d);
  });
  const cars = [...unique.values()];
  const totalCars = new Set(state.documents.map(d=>`${d.brand}|${d.model}`)).size;
  $('#car-count').textContent = `${totalCars} cars`;
  $('#mini-library').innerHTML = cars.length ? cars.map(car => {
    const selected = state.selectedVehicles.some(vehicle => vehicle.key === car.key);
    return `<div class="mini-car"><button type="button" class="mini-car-name${selected?' selected':''}" data-key="${escapeHtml(car.key)}" aria-pressed="${selected}" title="${selected?'Remove brochure from chat':'Attach brochure to chat'}"><strong>${escapeHtml(car.brand)} ${escapeHtml(car.model)}</strong><span class="mini-car-check" aria-hidden="true">${selected?'✓':'+'}</span></button></div>`;
  }).join('') : '<div class="empty-state compact">No brochures are available in the index.</div>';
}

function renderSelectedBrochures() {
  const box = $('#selected-brochures');
  if (!state.selectedVehicles.length) { box.hidden = true; box.replaceChildren(); return; }
  box.hidden = false;
  box.innerHTML = `<span class="selected-label">BROCHURES ATTACHED TO THIS CHAT</span>${state.selectedVehicles.map(vehicle=>`<button type="button" class="selected-brochure" data-remove-brochure="${escapeHtml(vehicle.key)}" title="Remove ${escapeHtml(vehicle.brand)} ${escapeHtml(vehicle.model)}">${escapeHtml(vehicle.brand)} ${escapeHtml(vehicle.model)} <span>×</span></button>`).join('')}`;
}

function renderKnowledge() {
  const docs = state.documents;
  $('#kb-document-count').textContent = `${docs.length} brochures`;
  $('#document-grid').innerHTML = docs.length ? docs.map(d => {
    const title = [d.model, knownValue(d.model_year)].filter(Boolean).join(' ');
    const edition = knownValue(d.brochure_edition);
    const subtitle = [d.filename, edition ? `Brochure ${edition}` : '', `${d.chunks} indexed passages`].filter(Boolean).join(' · ');
    const tags = knownTags(d);
    return `<article class="document-card"><div class="doc-top"><span class="doc-brand">${escapeHtml(d.brand)}</span><span class="doc-type">${escapeHtml((d.file_type || 'document').toUpperCase())} · indexed</span></div><h3>${escapeHtml(title)}</h3><p>${escapeHtml(subtitle)}</p>${tags.length ? `<div class="tag-row">${tags.map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join('')}</div>` : ''}<span class="kb-indexed-label">Searchable text available in this index</span></article>`;
  }).join('') : '<div class="empty-state">The preloaded brochure index is not available.</div>';
}

async function searchKnowledgeBase(event) {
  event.preventDefault();
  const query = $('#kb-search').value.trim();
  const status = $('#kb-search-status');
  const results = $('#kb-results');
  if (!query) return;
  status.textContent = 'Searching indexed brochure passages…';
  results.replaceChildren();
  $('#kb-search-button').disabled = true;
  try {
    const response = await fetch('/api/search', {
      method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({query}),
      signal: AbortSignal.timeout(60000),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Passage search failed.');
    const matches = data.results || [];
    if (!matches.length) {
      status.textContent = 'No matching passages were found in the preloaded index.';
      return;
    }
    status.textContent = `${matches.length} matching passages from the preloaded brochure index.`;
    results.innerHTML = matches.map(match => {
      const title = [match.brand, match.model, knownValue(match.year)].filter(Boolean).join(' ');
      const locator = [match.filename, match.locator, knownValue(match.market) ? `Market: ${match.market}` : ''].filter(Boolean).join(' · ');
      return `<article class="kb-result-card"><strong>${escapeHtml(title || 'Indexed brochure passage')}</strong><div class="kb-result-source">${escapeHtml(locator)}</div><p>${escapeHtml(match.excerpt || '')}</p></article>`;
    }).join('');
  } catch (error) {
    status.textContent = error.name === 'TimeoutError' ? 'Passage search is taking longer than expected. Please try again.' : error.message;
  } finally {
    $('#kb-search-button').disabled = false;
  }
}

function renderPortals() {
  const brandLogo = name => {
    const logos = [
      [/hyundai/i, 'hyundai'], [/tata/i, 'tata'], [/maruti/i, 'suzuki'],
      [/mahindra/i, 'mahindra'], [/toyota/i, 'toyota'], [/honda/i, 'honda'],
      [/volkswagen/i, 'volkswagen'], [/škoda|skoda/i, 'skoda'], [/jeep/i, 'jeep'],
      [/kia/i, 'kia'], [/renault/i, 'renault'], [/mg motor/i, 'mg'],
    ];
    return logos.find(([pattern]) => pattern.test(name))?.[1] || '';
  };
  const card = p => {
    const logo = p.group === 'Manufacturer' ? brandLogo(p.name) : '';
    const logoHtml = logo ? `<img class="portal-logo" src="https://cdn.simpleicons.org/${logo}" alt="" aria-hidden="true" loading="lazy" decoding="async" onerror="this.hidden=true">` : '';
    return `<article class="portal-card"><span class="portal-label">${escapeHtml(p.group)}</span><div class="portal-title-row">${logoHtml}<h3>${escapeHtml(p.name)}</h3></div><p>${escapeHtml(p.description)}</p><a class="portal-link" href="${escapeHtml(p.url)}" target="_blank" rel="noopener noreferrer">Visit official page ↗</a></article>`;
  };
  $('#manufacturer-portals').innerHTML = state.portals.filter(p=>p.group==='Manufacturer').map(card).join('');
  $('#government-portals').innerHTML = state.portals.filter(p=>p.group!=='Manufacturer').map(card).join('');
}

async function refreshOverview() {
  try { const r = await fetch('/api/overview'); const data = await r.json(); state.documents = data.documents || []; state.portals = data.portals || []; renderLibrary($('#library-search').value); renderKnowledge(); renderPortals(); }
  catch { console.error('Could not refresh the brochure library.'); }
}

function appendMessage(role, text, sources=[]) {
  const article = document.createElement('article'); article.className = `message ${role === 'user' ? 'user-message' : 'assistant-message'}`;
  const avatar = document.createElement('div'); avatar.className=`avatar ${role === 'user' ? 'you-avatar' : 'gemini-avatar'}`;
  if (role === 'user') { avatar.textContent='You'; avatar.setAttribute('aria-label','You'); }
  else { avatar.innerHTML='<svg viewBox="0 0 48 48" aria-label="Gemini"><defs><linearGradient id="gemini-gradient" x1="5" y1="40" x2="42" y2="7" gradientUnits="userSpaceOnUse"><stop stop-color="#4285F4"/><stop offset=".48" stop-color="#9B72CB"/><stop offset="1" stop-color="#D96570"/></linearGradient></defs><path fill="url(#gemini-gradient)" d="M24 3C27.2 14.4 33.6 20.8 45 24C33.6 27.2 27.2 33.6 24 45C20.8 33.6 14.4 27.2 3 24C14.4 20.8 20.8 14.4 24 3Z"/></svg>'; avatar.setAttribute('aria-label','Gemini AI'); }
  const bubble = document.createElement('div'); bubble.className='bubble';
  if (role !== 'user') { const meta=document.createElement('div'); meta.className='message-meta'; meta.textContent='GEMINI AI · brochure-grounded'; bubble.append(meta); }
  const body=document.createElement('div'); body.className='answer-body';
  if (role === 'user') body.textContent=text; else renderAnswer(body,text);
  bubble.append(body);
  article.append(avatar,bubble); $('#messages').append(article); $('#messages').scrollTop=$('#messages').scrollHeight;
}

function inlineText(parent, text) {
  const parts = String(text).split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  parts.forEach(part => {
    if (part.startsWith('**') && part.endsWith('**')) { const strong=document.createElement('strong');strong.textContent=part.slice(2,-2);parent.append(strong); }
    else if (part.startsWith('`') && part.endsWith('`')) { const code=document.createElement('code');code.textContent=part.slice(1,-1);parent.append(code); }
    else parent.append(document.createTextNode(part));
  });
}
function tableCells(line) { return line.trim().replace(/^\|/,'').replace(/\|$/,'').split('|').map(s=>s.trim()); }
function isTableLine(line) { return /^\s*\|.*\|\s*$/.test(line); }
function isTableRule(line) { return isTableLine(line) && tableCells(line).every(c=>/^:?-{3,}:?$/.test(c)); }
function renderAnswer(target, text) {
  const lines=String(text).split(/\r?\n/); let i=0;
  while(i<lines.length){
    if(!lines[i].trim()){i++;continue;}
    if(isTableLine(lines[i]) && i+1<lines.length && isTableRule(lines[i+1])){
      const table=document.createElement('table');table.className='answer-table';const head=document.createElement('thead');const hrow=document.createElement('tr');
      tableCells(lines[i]).forEach(cell=>{const th=document.createElement('th');inlineText(th,cell);hrow.append(th)});head.append(hrow);table.append(head);i+=2;
      const body=document.createElement('tbody');while(i<lines.length && isTableLine(lines[i])){const row=document.createElement('tr');tableCells(lines[i]).forEach(cell=>{const td=document.createElement('td');inlineText(td,cell);row.append(td)});body.append(row);i++}table.append(body);target.append(table);continue;
    }
    if(/^\s*[-*]\s+/.test(lines[i])){const ul=document.createElement('ul');while(i<lines.length && /^\s*[-*]\s+/.test(lines[i])){const li=document.createElement('li');inlineText(li,lines[i].replace(/^\s*[-*]\s+/,''));ul.append(li);i++}target.append(ul);continue;}
    if(/^\s*\d+[.)]\s+/.test(lines[i])){const ol=document.createElement('ol');while(i<lines.length && /^\s*\d+[.)]\s+/.test(lines[i])){const li=document.createElement('li');inlineText(li,lines[i].replace(/^\s*\d+[.)]\s+/,''));ol.append(li);i++}target.append(ol);continue;}
    const p=document.createElement(/^#{1,3}\s/.test(lines[i])?'h4':'p');inlineText(p,lines[i].replace(/^#{1,3}\s*/,''));target.append(p);i++;
  }
}

$('#chat-form').addEventListener('submit', async e=>{
  e.preventDefault(); const field=$('#question'); const message=field.value.trim(); if(!message)return;
  if (!state.currentChatId) startNewChat();
  const chatId = state.currentChatId;
  const activeChat = state.chats.find(chat => chat.id === chatId);
  const history = (activeChat?.messages || []).slice(-8).map(item => ({role:item.role,content:item.text}));
  const predefinedQuestionId = state.predefinedQuestion?.text === message ? state.predefinedQuestion.id : '';
  state.predefinedQuestion = null;
  recordMessage('user',message,[],chatId); field.value=''; const send=$('.send-button');send.disabled=true;
  const pending=document.createElement('article');pending.className='message assistant-message';const avatar=document.createElement('div');avatar.className='avatar gemini-avatar';avatar.innerHTML='<svg viewBox="0 0 48 48" aria-label="Gemini"><defs><linearGradient id="gemini-loading-gradient" x1="5" y1="40" x2="42" y2="7" gradientUnits="userSpaceOnUse"><stop stop-color="#4285F4"/><stop offset=".48" stop-color="#9B72CB"/><stop offset="1" stop-color="#D96570"/></linearGradient></defs><path fill="url(#gemini-loading-gradient)" d="M24 3C27.2 14.4 33.6 20.8 45 24C33.6 27.2 27.2 33.6 24 45C20.8 33.6 14.4 27.2 3 24C14.4 20.8 20.8 14.4 24 3Z"/></svg>';const b=document.createElement('div');b.className='bubble pending-bubble';b.textContent='Understanding your question and searching the brochures…';pending.append(avatar,b);$('#messages').append(pending);$('#messages').scrollTop=$('#messages').scrollHeight;
  try {const res=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message,history,document_ids:state.selectedVehicles.flatMap(vehicle=>vehicle.docIds),predefined_question_id:predefinedQuestionId}),signal:AbortSignal.timeout(90000)});const data=await res.json();pending.remove();recordMessage('assistant',data.answer||data.error||FALLBACK,data.sources||[],chatId)}
  catch (error) {pending.remove();recordMessage('assistant',error.name==='TimeoutError'?'This is taking longer than expected. Please try once more; the answer service may be busy.':'I could not reach the answer service. Please check that AutoSaarthi is running and try again.',[],chatId)}
  finally {send.disabled=false;field.focus()}
});

$('#question').addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    $('#chat-form').requestSubmit();
  }
});

$('#question').addEventListener('input', () => {
  if (state.predefinedQuestion && state.predefinedQuestion.text !== $('#question').value.trim()) state.predefinedQuestion = null;
});

$$('.suggestion').forEach(b=>b.addEventListener('click',()=>{$('#question').value=b.dataset.prompt;$('#question').focus()}));
$('#question-bank-search').addEventListener('input',renderQuestionBank);
$('#question-bank-category').addEventListener('change',renderQuestionBank);
$('#library-search').addEventListener('input',e=>renderLibrary(e.target.value));
$('#kb-search-form').addEventListener('submit',searchKnowledgeBase);

const dialog=$('#upload-dialog');
if (dialog) {
  function openUpload(){dialog.showModal()}
  $('#open-upload').addEventListener('click',openUpload);$('#composer-upload').addEventListener('click',openUpload);
  ['close-upload','cancel-upload'].forEach(id=>$('#'+id).addEventListener('click',()=>dialog.close()));
  $('#brochure-file').addEventListener('change',e=>$('#file-label').textContent=e.target.files[0]?.name||'Choose a PDF or DOCX');
  $('#upload-form').addEventListener('submit',async e=>{
    e.preventDefault();const uploadForm=e.currentTarget;const status=$('#upload-status');status.className='upload-status';status.textContent='Reading the document and attaching its searchable passages to this chat…';
    const form=new FormData(uploadForm);
    try{const res=await fetch('/api/upload',{method:'POST',body:form});const data=await res.json();if(!res.ok)throw new Error(data.error||'Upload failed');const record=data.document,key=`${record.brand}|${record.model}`;status.textContent=data.already_indexed?`${record.brand} ${record.model} is already available and has been attached to this chat.`:`Attached the ${record.brand} ${record.model} brochure to this chat.`;await refreshOverview();if(!state.selectedVehicles.some(vehicle=>vehicle.key===key)){const docs=state.documents.filter(doc=>`${doc.brand}|${doc.model}`===key);const docIds=[...new Set([...docs.map(doc=>doc.doc_id),record.doc_id].filter(Boolean))];state.selectedVehicles.push({key,brand:record.brand,model:record.model,docIds});}renderLibrary($('#library-search').value);renderSelectedBrochures();uploadForm.reset();$('#file-label').textContent='Choose a PDF or DOCX';setTimeout(()=>dialog.close(),1600)}catch(err){status.className='upload-status error';status.textContent=err.message}
  });
}

initializeChatHistory();refreshOverview();loadQuestionBank();

