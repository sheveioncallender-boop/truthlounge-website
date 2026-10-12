(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  let stages = [['new','New'],['acknowledged','Acknowledged'],['preparing','Preparing'],['ready','Ready'],['completed','Completed'],['cancelled','Dismissed']];
  const displayId = Number(document.body.dataset.displayId);
  const preferenceKey = `truthDisplay:${displayId}`;
  const next = {new:'Acknowledge', acknowledged:'Start preparing', preparing:'Mark ready', ready:'Complete'};
  const state = {tickets:[], seen:new Set(), station:localStorage.getItem(preferenceKey+':station') || 'all', sound:false, volume:60, settings:{refreshSeconds:5, lateMinutes:15, repeatSeconds:20, soundEnabled:true}, canCancel:false, started:false};
  let audio, busy = false, lastAlert = 0, requestId = 0;
  const escape = (v) => String(v ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  async function rpc(path, params={}) {
    const response = await fetch(path, {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json'}, body:JSON.stringify({jsonrpc:'2.0', method:'call', id:++requestId, params:{...params,display_id:displayId}})});
    if (!response.ok) throw new Error('Connection interrupted. Check that you are signed in.');
    const data = await response.json();
    if (data.error) throw new Error(data.error.data?.message || data.error.message || 'Request failed.');
    return data.result;
  }
  function message(text) { $('error').textContent=text; $('error').style.display='block'; }
  function beep() {
    if (!state.settings.soundEnabled || !state.sound || !audio || audio.state !== 'running') return;
    const t = audio.currentTime;
    [660,880].forEach((frequency,index) => {
      const o = audio.createOscillator(), g = audio.createGain();
      o.connect(g); g.connect(audio.destination); o.frequency.value=frequency;
      const start=t+index*.18;
      g.gain.setValueAtTime(0,start); g.gain.linearRampToValueAtTime(state.volume/500,start+.02); g.gain.exponentialRampToValueAtTime(.001,start+.16);
      o.start(start); o.stop(start+.18);
    });
    lastAlert=Date.now();
  }
  function relevant(ticket) { return state.station==='all' || state.station===ticket.station; }
  function age(ticket) { return Math.max(0, Math.floor((Date.now()-new Date(ticket.created.replace(' ','T')+'Z'))/60000)); }
  function card(t) {
    return `<article class="ticket ${age(t)>=state.settings.lateMinutes && next[t.stage]?'late':''} ${t.amended?'amended':''}">
      <div class="ref"><span>${escape(t.reference)}</span><span>${age(t)}m</span></div>
      <div class="meta">${escape(t.source)} · ${escape(t.table)}<br>${t.station==='bar'?'BAR':'KITCHEN'}</div>
      ${t.amended?'<div class="amend">UPDATED ORDER — CHECK CHANGES</div>':''}
      <div class="item">${$('images').checked && t.image?`<img src="${escape(t.image)}" alt="" loading="lazy">`:''}<h3>${escape(t.qty)} × ${escape(t.product)}</h3></div>
      ${t.note?`<p>${escape(t.note)}</p>`:''}${t.reason?`<p>${escape(t.reason)}</p>`:''}
      ${next[t.stage]?`<button data-ticket="${t.id}" data-revision="${t.revision}">${escape('→ ' + (stages[stages.findIndex(([code])=>code===t.stage)+1]?.[1] || 'Next'))}</button>`:''}
      ${state.canCancel && next[t.stage]?`<button class="dismiss" data-dismiss="${t.id}" data-revision="${t.revision}">Dismiss preparation item</button>`:''}</article>`;
  }
  function render() {
    const visible = stages.filter(([s]) => $('closed').checked || !['completed','cancelled'].includes(s));
    $('board').style.gridTemplateColumns=`repeat(${visible.length}, minmax(215px, 1fr))`;
    $('board').innerHTML = visible.map(([code,label])=>{
      const tickets=state.tickets.filter(t=>t.stage===code && relevant(t));
      return `<section class="kds-column"><h2>${escape(label)}<span>${tickets.length}</span></h2>${tickets.length?tickets.map(card).join(''):'<p class="empty">No items</p>'}</section>`;
    }).join('');
    document.querySelectorAll('[data-station]').forEach(b=>b.classList.toggle('active',b.dataset.station===state.station));
  }
  async function refresh() {
    if (busy) return;
    busy=true;
    try {
      const data=await rpc('/truth/kitchen/data');
      state.settings=data.settings; stages=data.settings.stages;
      $('display-name').textContent=data.settings.name;
      if (!state.started) {
        state.started=true;
        state.volume=Number(localStorage.getItem(preferenceKey+':volume') ?? data.settings.volume);
        $('volume').value=state.volume;
        $('images').checked=data.settings.showImages;
      }
      if (data.settings.station!=='all') state.station=data.settings.station;
      document.querySelector('.kds-tabs').hidden=data.settings.station!=='all';
      for (const id of ['sound-start','sound-test']) $(id).hidden=!data.settings.soundEnabled;
      $('volume').closest('label').hidden=!data.settings.soundEnabled;
      let fresh=false;
      for (const ticket of data.tickets) {
        const key=`${ticket.id}:${ticket.revision}`;
        if (ticket.stage==='new' && relevant(ticket) && !state.seen.has(key)) fresh=true;
        state.seen.add(key);
      }
      state.tickets=data.tickets; state.canCancel=data.canCancel;
      if (fresh || (state.settings.repeatSeconds>0 && Date.now()-lastAlert>state.settings.repeatSeconds*1000 && state.tickets.some(t=>t.stage==='new' && relevant(t)))) beep();
      $('status').textContent=data.syncErrors?'Some orders could not sync — contact your administrator':`Updated ${new Date().toLocaleTimeString()}`;
      if (!data.syncErrors) $('error').style.display='none';
      render();
    } catch(error) { $('status').textContent='Disconnected — showing last received orders'; message(error.message); }
    finally {busy=false;}
  }
  document.querySelectorAll('[data-station]').forEach(b=>b.addEventListener('click',()=>{state.station=b.dataset.station;localStorage.setItem(preferenceKey+':station',state.station);render();}));
  $('images').addEventListener('change',render); $('closed').addEventListener('change',render);
  $('volume').value=state.volume;
  $('volume').addEventListener('input',()=>{state.volume=Number($('volume').value);localStorage.setItem(preferenceKey+':volume',String(state.volume));});
  $('sound-start').addEventListener('click',async()=>{
    try {audio ||= new (window.AudioContext || window.webkitAudioContext)();await audio.resume();state.sound=!state.sound;$('sound-start').textContent=state.sound?'Mute sound':'Enable sound';if(state.sound)beep();}
    catch {message('This browser could not enable sound. Try another supported browser.');}
  });
  $('sound-test').addEventListener('click',()=>state.sound?beep():message('Click Enable sound first.'));
  $('fullscreen').addEventListener('click',async()=>{try {if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen();}catch{message('Full screen is unavailable in this browser.');}});
  $('board').addEventListener('click',async(event)=>{
    const button=event.target.closest('button[data-ticket],button[data-dismiss]'); if(!button)return;
    let reason=null;
    if(button.dataset.dismiss){reason=window.prompt('Reason for dismissing this preparation item? This does not cancel or refund the Odoo order.');if(!reason?.trim())return;}
    button.disabled=true;
    try {await rpc('/truth/kitchen/step',{ticket_id:Number(button.dataset.ticket||button.dataset.dismiss),revision:Number(button.dataset.revision),cancel_reason:reason});await refresh();}
    catch(error){message(error.message);button.disabled=false;}
  });
  async function poll() { await refresh(); setTimeout(poll,state.settings.refreshSeconds*1000); }
  poll();
})();
