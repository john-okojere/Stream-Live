(function(){
  const $ = (sel, ctx=document) => ctx.querySelector(sel);
  const audio = $('#lot-audio');
  if(!audio) return;

  // DOM
  const root     = $('#lot-player');
  const titleEl  = $('#lot-title');
  const artistEl = $('#lot-artist');
  const coverEl  = $('#lot-cover');
  const seekEl   = $('#lot-seek');
  const curEl    = $('#lot-cur');
  const durEl    = $('#lot-dur');
  const toggleEl = $('#lot-toggle');
  const prevEl   = $('#lot-prev');
  const nextEl   = $('#lot-next');
  const speedSel = $('#lot-speed');
  const shuffleEl= $('#lot-shuffle');
  const repeatEl = $('#lot-repeat');
  const queueList= $('#queueList');
  const queueCount=$('#queueCount');
  const queueClear=$('#queueClear');
  const queueShuffle=$('#queueShuffle');

  // State
  let queue = JSON.parse(localStorage.getItem('lot_queue_v1')||'[]');
  let idx   = parseInt(localStorage.getItem('lot_idx_v1')||'-1',10);
  let wasPlaying = localStorage.getItem('lot_was_playing') === '1';
  let shuffle = (localStorage.getItem('lot_shuffle')||'0') === '1';
  let repeatMode = localStorage.getItem('lot_repeat') || 'none'; // none | all | one

  const fmt = s=>{ s=Math.max(0, Math.floor(s)); const m=Math.floor(s/60), r=s%60; return `${m}:${r.toString().padStart(2,'0')}` };
  const save = ()=>{
    localStorage.setItem('lot_queue_v1', JSON.stringify(queue));
    localStorage.setItem('lot_idx_v1', String(idx));
  };
  const setWasPlaying = (flag)=> localStorage.setItem('lot_was_playing', flag ? '1' : '0');

  // Initialize UI states
  const applyShuffleUI = ()=>{
    shuffleEl.setAttribute('aria-pressed', shuffle ? 'true':'false');
    shuffleEl.classList.toggle('active', shuffle);
  };
  const applyRepeatUI = ()=>{
    // cycle: none -> all -> one
    repeatEl.dataset.mode = repeatMode;
    repeatEl.title = `Repeat: ${repeatMode}`;
    repeatEl.classList.toggle('active', repeatMode !== 'none');
    // icon hint: repeat-1 if supported, else keep repeat icon
    try{
      if(repeatMode === 'one'){
        repeatEl.innerHTML = '<i class="bi bi-repeat-1"></i>';
      } else {
        repeatEl.innerHTML = '<i class="bi bi-repeat"></i>';
      }
    }catch(e){}
  };
  applyShuffleUI(); applyRepeatUI();

  // Playback speed
  const savedSpeed = localStorage.getItem('lot_speed') || '1×';
  speedSel.value = savedSpeed;
  audio.playbackRate = parseFloat(savedSpeed.replace('×','')) || 1.0;
  speedSel.addEventListener('change', ()=>{
    const v=parseFloat(speedSel.value.replace('×',''))||1;
    audio.playbackRate=v; localStorage.setItem('lot_speed', speedSel.value);
  });

  async function fetchSermon(slug){
    const res = await fetch(`/api/sermons/${slug}.json`, {credentials:'same-origin'});
    if(!res.ok) throw new Error(`Failed to load ${slug}`);
    return await res.json();
  }

  function renderQueue(){
    // Counter
    if(queueCount) queueCount.textContent = String(queue.length);

    if(!queueList) return;
    queueList.innerHTML = '';

    if(queue.length === 0){
      const empty = document.createElement('li');
      empty.className = 'list-group-item text-light';
      empty.textContent = 'Queue is empty. Add items from Past Streams.';
      queueList.appendChild(empty);
      return;
    }

    queue.forEach((item, i)=>{
      const li = document.createElement('li');
      li.className = 'list-group-item d-flex align-items-center gap-3';
      if(i === idx) li.classList.add('active');

      li.innerHTML = `
        <img src="${item.cover || ''}" alt="" style="width:34px;height:34px;object-fit:cover;background:#111" class="rounded">
        <div class="flex-grow-1" style="max-width:185px;">
          <div class="text-truncate">${item.title}</div>
          <div class="text-light text-truncate">${item.speaker || ''}</div>
        </div>
        <button class="btn btn-sm btn-outline-light me-1" data-action="jump" data-i="${i}" title="Play"><i class="bi bi-play-fill"></i></button>
        <button class="btn btn-sm btn-outline-danger" data-action="remove" data-i="${i}" title="Remove"><i class="bi bi-x-lg"></i></button>
      `;
      queueList.appendChild(li);
    });
  }

  async function playSlug(slug, pushToQueue=true){
    try{
      const meta = await fetchSermon(slug);
      if(pushToQueue){ queue.push(meta); idx = queue.length-1; save(); }
      loadCurrent(true);
    }catch(e){
      console.error(e);
      // tiny toast
      if(root){
        root.classList.add('shake');
        setTimeout(()=>root.classList.remove('shake'), 400);
      }
      alert('Could not load this audio item.');
    }
  }

  function loadCurrent(autoPlay){
    const cur = queue[idx]; if(!cur){ renderQueue(); return; }

    titleEl.textContent = cur.title;
    artistEl.textContent= cur.speaker || '—';
    coverEl.src = cur.cover || '';
    // set glass background from cover
    if(cur.cover){
        root.style.setProperty('--cover-img', `url("${cur.cover}")`);
    } else {
        root.style.removeProperty('--cover-img');
    }

    audio.src = cur.audio;

    // Restore position
    const key = `lot_prog_${cur.slug}`;
    const last = parseFloat(localStorage.getItem(key)||'0');
    if(last && last < (cur.duration_s||1)-5) audio.currentTime = last;

    document.title = `${cur.title} — LOT`;
    renderQueue();

    // Media Session
    if('mediaSession' in navigator){
      navigator.mediaSession.metadata = new MediaMetadata({
        title: cur.title, artist: cur.speaker||'',
        artwork: cur.cover? [{src:cur.cover,sizes:'512x512'}]:[]
      });
      navigator.mediaSession.setActionHandler('previoustrack', prev);
      navigator.mediaSession.setActionHandler('nexttrack', next);
      navigator.mediaSession.setActionHandler('play', ()=>audio.play());
      navigator.mediaSession.setActionHandler('pause', ()=>audio.pause());
      navigator.mediaSession.setActionHandler('seekbackward', ()=>{ audio.currentTime=Math.max(0,audio.currentTime-15); });
      navigator.mediaSession.setActionHandler('seekforward',  ()=>{ audio.currentTime=Math.min(audio.duration||0,audio.currentTime+15); });
    }

    if(autoPlay || wasPlaying){
      const onCanPlay = ()=>{ audio.removeEventListener('canplay', onCanPlay); audio.play().catch(()=>{}); };
      audio.addEventListener('canplay', onCanPlay);
    }
  }

  function pickRandomNext(){
    if(queue.length <= 1) return idx;
    let nextIdx = idx;
    while(nextIdx === idx){
      nextIdx = Math.floor(Math.random()*queue.length);
    }
    return nextIdx;
  }

  function next(){
    if(queue.length === 0){ return; }
    if(shuffle){
      idx = pickRandomNext();
    }else{
      if(idx < queue.length-1){ idx++; }
      else if(repeatMode === 'all'){ idx = 0; }
      else { audio.pause(); setWasPlaying(false); return; }
    }
    save(); loadCurrent(true);
  }

  function prev(){
    if(queue.length === 0){ return; }
    if(shuffle){
      idx = pickRandomNext();
    }else{
      if(idx > 0){ idx--; }
      else if(repeatMode === 'all'){ idx = queue.length-1; }
      else { audio.currentTime = 0; return; }
    }
    save(); loadCurrent(true);
  }

  // Main controls
  toggleEl.addEventListener('click', ()=>{ if(audio.paused){ audio.play(); } else { audio.pause(); } });
  nextEl.addEventListener('click', next);
  prevEl.addEventListener('click', prev);

  shuffleEl.addEventListener('click', ()=>{
    shuffle = !shuffle;
    localStorage.setItem('lot_shuffle', shuffle ? '1':'0');
    applyShuffleUI();
  });

  repeatEl.addEventListener('click', ()=>{
    repeatMode = (repeatMode === 'none') ? 'all' : (repeatMode === 'all') ? 'one' : 'none';
    localStorage.setItem('lot_repeat', repeatMode);
    applyRepeatUI();
  });

  // Seek
  seekEl.addEventListener('input', ()=>{
    if(!isFinite(audio.duration)) return;
    audio.currentTime = (seekEl.value/100)*(audio.duration||0);
  });

  // Events
  audio.addEventListener('timeupdate', ()=>{
    if(!isFinite(audio.duration)) return;
    const pct = (audio.currentTime/(audio.duration||1))*100;
    seekEl.value = pct;
    curEl.textContent = fmt(audio.currentTime);
    durEl.textContent = fmt(audio.duration||0);

    const cur = queue[idx];
    if(cur){
      const key = `lot_prog_${cur.slug}`;
      if(Math.floor(audio.currentTime)%5===0){
        localStorage.setItem(key, String(Math.floor(audio.currentTime)));
      }
      if(Math.floor(audio.currentTime)%15===0 && navigator.sendBeacon){
        const data = new URLSearchParams({slug: cur.slug, progress_s: String(Math.floor(audio.currentTime))});
        navigator.sendBeacon('/api/progress/', data);
      }
    }
  });

  audio.addEventListener('ended', ()=>{
    if(repeatMode === 'one'){
      audio.currentTime = 0;
      audio.play().catch(()=>{});
      return;
    }
    next();
  });

  audio.addEventListener('play',  ()=>{ setWasPlaying(true);  toggleEl.innerHTML = '<i class="bi bi-pause-fill"></i>'; root?.classList.add('is-playing'); });
  audio.addEventListener('pause', ()=>{ setWasPlaying(false); toggleEl.innerHTML = '<i class="bi bi-play-fill"></i>';  root?.classList.remove('is-playing'); });

  // Drawer actions
  if(queueList){
    queueList.addEventListener('click', (e)=>{
      const btn = e.target.closest('button[data-action]');
      if(!btn) return;
      const i = parseInt(btn.dataset.i, 10);
      if(btn.dataset.action === 'remove'){
        if(i < idx) idx -= 1;
        queue.splice(i,1);
        if(queue.length === 0){ idx = -1; audio.pause(); }
        idx = Math.max(-1, Math.min(idx, queue.length-1));
        save(); renderQueue();
      } else if(btn.dataset.action === 'jump'){
        if(i >=0 && i < queue.length){ idx = i; save(); loadCurrent(true); }
      }
    });
  }
  if(queueClear){
    queueClear.addEventListener('click', ()=>{
      queue = []; idx = -1; save(); renderQueue(); audio.pause();
    });
  }
  if(queueShuffle){
    queueShuffle.addEventListener('click', ()=>{
      // Fisher–Yates; keep current at front if selected
      if(idx>=0){
        const current = queue.splice(idx,1)[0];
        for(let i = queue.length-1; i>0; i--){
          const j = Math.floor(Math.random()*(i+1));
          [queue[i], queue[j]] = [queue[j], queue[i]];
        }
        queue.unshift(current);
        idx = 0;
      }else{
        for(let i = queue.length-1; i>0; i--){
          const j = Math.floor(Math.random()*(i+1));
          [queue[i], queue[j]] = [queue[j], queue[i]];
        }
      }
      save(); renderQueue();
    });
  }

  // Global click hooks
  document.addEventListener('click', (e)=>{
    const playBtn = e.target.closest('.js-play-now');
    if(playBtn){ e.preventDefault(); playSlug(playBtn.dataset.slug, true); }

    const addBtn = e.target.closest('.js-add-queue');
    if(addBtn){
      e.preventDefault();
      fetchSermon(addBtn.dataset.slug).then(meta=>{
        queue.push(meta);
        if(idx===-1) idx=0;
        save(); renderQueue();
        // small visual toast on card
        const card = addBtn.closest('[data-slug]'); if(card){
          const burst = document.createElement('div');
          burst.className='queued-burst';
          burst.textContent='Queued ✓';
          card.appendChild(burst);
          setTimeout(()=>burst.remove(), 1100);
        }
      }).catch(()=>{ alert('Could not add to queue.'); });
    }
  });

  // Persist "was playing" on navigation
  window.addEventListener('beforeunload', ()=>{ setWasPlaying(!audio.paused); });

  // Hydrate
  if(idx>=0 && queue[idx]){ loadCurrent(false); } else { renderQueue(); }
})();
