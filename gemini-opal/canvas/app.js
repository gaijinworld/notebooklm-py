const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const defaultNegative = 'rear-only view, silhouette, hidden face, distorted face, blank facial features, text covering the face, defocused primary subject';

const state = {
  scenes: [],
  activeOutput: 'storyboard'
};

function project() {
  let duration = Number($('#duration').value);
  const resolution = $('#resolution').value;
  const references = Math.max(0, Math.min(3, Number($('#references').value || 0)));
  let person = $('#person').value;
  if (references > 0) person = 'allow_adult';
  if (references > 0 || resolution === '1080p' || resolution === '4k') duration = 8;
  $('#duration').value = String(duration);
  $('#person').value = person;
  $('#references').value = String(references);
  return {
    title: $('#title').value.trim() || 'Controlled Cinematic Overview',
    language: $('#language').value.trim() || 'en',
    topic: $('#topic').value.trim(),
    sources: $('#sources').value.trim(),
    minutes: Math.max(1, Number($('#minutes').value || 10)),
    sceneCount: Math.max(1, Math.min(60, Number($('#scene-count').value || 12))),
    aspect: $('#aspect').value,
    resolution,
    model: $('#model').value,
    duration,
    person,
    references,
    mode: $('#mode').value,
    maxClips: Math.max(1, Number($('#max-clips').value || 24)),
    notebookId: $('#notebook-id').value.trim() || 'YOUR_NOTEBOOK_ID',
    approved: $('#approval').checked
  };
}

function starterScene(index) {
  const p = project();
  const variants = [
    ['Opening context', 'Introduce the central source-supported question and why it matters.', 'A fictional adult presenter introduces the topic in a realistic Japanese office with subtle environmental movement.'],
    ['Background and chronology', 'Explain the source-supported background and chronology.', 'A face-visible presenter walks toward the camera through a relevant real-world location while contextual details move naturally in the environment.'],
    ['Evidence and explanation', 'Explain the strongest source-supported evidence.', 'Two fictional adult colleagues discuss source documents through a face-visible two-shot and reverse-angle coverage.'],
    ['Implications', 'Connect the evidence to practical implications from the sources.', 'A fictional adult presenter explains the implications beside relevant environmental B-roll and clean motion graphics.'],
    ['Conclusion', 'Summarize the source-grounded conclusion and next considerations.', 'The presenter concludes in an eye-level medium close-up with soft frontal lighting and a restrained dolly-out.']
  ];
  const v = variants[(index - 1) % variants.length];
  return {
    title: `${v[0]} ${index}`,
    narration: v[1],
    visual_prompt: v[2],
    composition: 'eye-level medium close-up or two-shot, unobstructed faces, both eyes visible',
    camera: 'slow cinematic movement while preserving front or natural three-quarter facial visibility',
    lens: '50mm natural perspective, primary faces in sharp focus',
    ambiance: 'soft balanced frontal lighting with natural skin tones',
    negative_prompt: defaultNegative,
    duration_seconds: p.duration
  };
}

function createStarter() {
  const count = project().sceneCount;
  state.scenes = Array.from({ length: count }, (_, i) => starterScene(i + 1));
  renderScenes();
  go('storyboard');
}

function storyboardPayload() {
  const p = project();
  return {
    schema_version: 1,
    title: p.title,
    summary: p.topic,
    scenes: state.scenes.map((scene) => ({ ...scene }))
  };
}

function renderScenes() {
  const list = $('#scene-list');
  list.innerHTML = '';
  state.scenes.forEach((scene, index) => {
    const card = document.createElement('article');
    card.className = 'scene-card';
    card.innerHTML = `
      <div class="scene-head">
        <div class="scene-index">Scene ${index + 1}</div>
        <div class="scene-actions">
          <button class="icon-btn duplicate">Duplicate</button>
          <button class="icon-btn remove">Delete</button>
        </div>
      </div>
      <div class="grid two">
        <label><span>Title</span><input data-key="title"></label>
        <label><span>Duration</span><select data-key="duration_seconds"><option value="4">4 seconds</option><option value="6">6 seconds</option><option value="8">8 seconds</option></select></label>
      </div>
      <label style="margin-top:12px"><span>Narration anchor</span><textarea data-key="narration"></textarea></label>
      <label style="margin-top:12px"><span>Visual prompt</span><textarea data-key="visual_prompt"></textarea></label>
      <div class="grid two" style="margin-top:12px">
        <label><span>Composition</span><textarea data-key="composition"></textarea></label>
        <label><span>Camera</span><textarea data-key="camera"></textarea></label>
        <label><span>Lens</span><textarea data-key="lens"></textarea></label>
        <label><span>Ambiance</span><textarea data-key="ambiance"></textarea></label>
      </div>
      <label style="margin-top:12px"><span>Negative prompt</span><textarea data-key="negative_prompt"></textarea></label>`;

    card.querySelectorAll('[data-key]').forEach((control) => {
      const key = control.dataset.key;
      control.value = scene[key];
      control.addEventListener('input', () => {
        scene[key] = key === 'duration_seconds' ? Number(control.value) : control.value;
        recalc();
      });
    });
    card.querySelector('.duplicate').addEventListener('click', () => {
      state.scenes.splice(index + 1, 0, JSON.parse(JSON.stringify(scene)));
      renderScenes();
    });
    card.querySelector('.remove').addEventListener('click', () => {
      if (state.scenes.length > 1) state.scenes.splice(index, 1);
      renderScenes();
    });
    list.appendChild(card);
  });
  $('#scene-badge').textContent = `${state.scenes.length} scene${state.scenes.length === 1 ? '' : 's'}`;
  $('#scene-count').value = String(state.scenes.length || project().sceneCount);
  recalc();
}

function estimate() {
  const p = project();
  const narrationSeconds = Math.round(p.minutes * 60);
  const fullClipCount = Math.max(1, Math.ceil(narrationSeconds / p.duration));
  let selected = 0;
  if (p.mode === 'one_clip_test') selected = 1;
  if (p.mode === 'budget_render') selected = Math.min(fullClipCount, p.maxClips);
  if (p.mode === 'full_render') selected = p.approved ? fullClipCount : 0;
  const renderedSeconds = selected * p.duration;
  const risk = selected === 0 ? 'Low' : selected <= 4 ? 'Low' : selected <= 24 ? 'Medium' : 'High';
  return { narrationSeconds, fullClipCount, selected, renderedSeconds, risk };
}

function validationMessages() {
  const p = project();
  const errors = [];
  const warnings = [];
  if (!p.topic) errors.push('Topic is required.');
  if (!state.scenes.length) errors.push('Create or import at least one storyboard scene.');
  state.scenes.forEach((scene, index) => {
    if (!scene.visual_prompt || !scene.visual_prompt.trim()) errors.push(`Scene ${index + 1} requires visual_prompt.`);
    if (![4, 6, 8].includes(Number(scene.duration_seconds))) errors.push(`Scene ${index + 1} duration must be 4, 6, or 8.`);
  });
  if (p.references > 3) errors.push('No more than three reference images are supported.');
  if ((p.references > 0 || p.resolution === '1080p' || p.resolution === '4k') && p.duration !== 8) errors.push('References, 1080p, and 4K require 8-second clips.');
  if (p.references > 0 && p.person !== 'allow_adult') errors.push('Reference images require allow_adult.');
  if (p.mode === 'full_render' && !p.approved) warnings.push('Full-render handoff is locked until approval is checked.');
  if (p.mode === 'one_clip_test') warnings.push('One-clip test is the only mode that should be connected to an Opal video node.');
  return { errors, warnings };
}

function recalc() {
  const e = estimate();
  $('#full-clips').textContent = e.fullClipCount;
  $('#selected-clips').textContent = e.selected;
  $('#rendered-seconds').textContent = e.renderedSeconds;
  $('#risk').textContent = e.risk;
  const v = validationMessages();
  $('#validation').innerHTML = v.errors.length
    ? `<strong style="color:var(--danger)">Fix before export:</strong><br>${v.errors.join('<br>')}`
    : v.warnings.length
      ? `<strong style="color:var(--warning)">Review:</strong><br>${v.warnings.join('<br>')}`
      : '<strong style="color:var(--success)">Valid configuration.</strong> No media request has been started.';
  const p = project();
  $('#status-title').textContent = p.mode.replaceAll('_', ' ').replace(/\b\w/g, (m) => m.toUpperCase());
  $('#status-detail').textContent = e.selected === 0
    ? 'No video clips are selected for generation.'
    : `${e.selected} clip${e.selected === 1 ? '' : 's'} selected in the handoff estimate. This browser still performs no generation.`;
  refreshOutput();
}

function renderManifest() {
  const p = project();
  const e = estimate();
  return {
    schema_version: 1,
    mode: p.mode,
    topic: p.topic,
    scene_count: state.scenes.length,
    storyboard_file: 'storyboard.json',
    settings: {
      model: p.model,
      aspect_ratio: p.aspect,
      resolution: p.resolution,
      duration_seconds: p.duration,
      person_generation: p.person,
      reference_image_count: p.references,
      language: p.language
    },
    cost_guard: {
      narration_seconds: e.narrationSeconds,
      full_clip_count: e.fullClipCount,
      selected_clip_count: e.selected,
      rendered_seconds: e.renderedSeconds,
      maximum_clips: p.maxClips,
      approved: p.approved
    },
    execution: {
      runs_in_gem: false,
      local_pipeline: 'scripts/controlled_cinematic_video_overview_pipeline.py',
      notebooklm_video_overview_requested: false,
      veo_render_requested: false
    }
  };
}

function videoInstructions() {
  const p = project();
  const outline = state.scenes.map((scene, i) => `${i + 1}. ${scene.title}: ${scene.narration}`).join('\n');
  return `# NotebookLM Cinematic Video Overview instructions\n\nCreate a source-grounded Cinematic Video Overview about: ${p.topic}\n\nUse a polished documentary narration. Follow the scene order below so the extracted narration and separately rendered Veo scenes remain thematically aligned. Cover only claims supported by the selected sources. Do not mention the storyboard, audio extraction, rendering process, or production tools.\n\n## Scene outline\n\n${outline}\n\n## Human framing guidance\n\nWhen people improve understanding, use fictional non-famous adults with front or natural three-quarter facial angles, visible eyes, unobstructed faces, and soft balanced frontal lighting. Avoid rear-only primary views, silhouettes, masks, extreme crops, distorted faces, or text covering faces.\n`;
}

function commandText() {
  const p = project();
  const modeComment = p.mode === 'plan_only' ? '# Plan-only mode: add --plan-only to stop before media generation.\n' : '';
  const approvalWarning = p.mode === 'full_render' && !p.approved ? '# LOCKED: check full-render approval before using this command.\n' : '';
  return `${approvalWarning}${modeComment}$env:GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"\n\nuv run python scripts/controlled_cinematic_video_overview_pipeline.py \`\n  --notebook "${p.notebookId}" \`\n  --topic "${p.topic.replaceAll('"', "'")}" \`\n  --profile "default" \`\n  --storyboard-file ".\\storyboard.json" \`\n  --video-overview-instructions-file ".\\video-overview-instructions.md" \`\n  --scene-count ${state.scenes.length} \`\n  --person-generation ${p.person} \`\n  --aspect-ratio ${p.aspect} \`\n  --duration ${p.duration} \`\n  --resolution ${p.resolution} \`\n  --model ${p.model} \`\n  --workspace ".\\controlled-video-overview-work" \`\n  --output ".\\controlled-video-overview.mp4"${p.mode === 'plan_only' ? ' `\n  --plan-only' : ''}\n`;
}

const outputs = {
  storyboard: () => JSON.stringify(storyboardPayload(), null, 2),
  manifest: () => JSON.stringify(renderManifest(), null, 2),
  instructions: videoInstructions,
  command: commandText
};

const filenames = {
  storyboard: 'storyboard.json',
  manifest: 'render-manifest.json',
  instructions: 'video-overview-instructions.md',
  command: 'run-controlled-cinematic.ps1'
};

function refreshOutput() {
  if ($('#output-preview')) $('#output-preview').textContent = outputs[state.activeOutput]();
}

function selectOutput(name) {
  state.activeOutput = name;
  refreshOutput();
  $$('.handoff-choice').forEach((button) => button.classList.toggle('primary', button.dataset.output === name));
}

function download(name, content) {
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function go(id) {
  $$('.panel').forEach((panel) => panel.classList.toggle('active', panel.id === id));
  $$('.tab').forEach((tab) => tab.setAttribute('aria-selected', String(tab.dataset.tab === id)));
  if (id === 'handoff') selectOutput(state.activeOutput);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

$$('.tab').forEach((button) => button.addEventListener('click', () => go(button.dataset.tab)));
$$('[data-go]').forEach((button) => button.addEventListener('click', () => go(button.dataset.go)));
$('#starter').addEventListener('click', createStarter);
$('#add-scene').addEventListener('click', () => { state.scenes.push(starterScene(state.scenes.length + 1)); renderScenes(); });
$('#export-storyboard').addEventListener('click', () => download('storyboard.json', outputs.storyboard()));

$('#import-json').addEventListener('change', async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  try {
    const payload = JSON.parse(await file.text());
    if (!Array.isArray(payload.scenes) || payload.scenes.length === 0) throw new Error('No scenes found.');
    state.scenes = payload.scenes.map((scene) => ({
      title: scene.title || 'Untitled scene',
      narration: scene.narration || '',
      visual_prompt: scene.visual_prompt || scene.prompt || '',
      composition: scene.composition || 'eye-level medium close-up',
      camera: scene.camera || 'slow cinematic movement',
      lens: scene.lens || '50mm natural perspective',
      ambiance: scene.ambiance || 'soft balanced frontal lighting',
      negative_prompt: scene.negative_prompt || defaultNegative,
      duration_seconds: [4,6,8].includes(Number(scene.duration_seconds)) ? Number(scene.duration_seconds) : project().duration
    }));
    $('#title').value = payload.title || $('#title').value;
    renderScenes();
  } catch (error) {
    alert(`Could not import storyboard: ${error.message}`);
  } finally {
    event.target.value = '';
  }
});

$$('.handoff-choice').forEach((button) => button.addEventListener('click', () => selectOutput(button.dataset.output)));
$('#download-output').addEventListener('click', () => {
  const v = validationMessages();
  if (v.errors.length) return alert('Fix validation errors before export.');
  if (project().mode === 'full_render' && !project().approved) return alert('Approve the full-render handoff first.');
  download(filenames[state.activeOutput], outputs[state.activeOutput]());
});
$('#copy-output').addEventListener('click', async () => {
  const text = outputs[state.activeOutput]();
  try {
    await navigator.clipboard.writeText(text);
    $('#copy-output').textContent = 'Copied';
    setTimeout(() => $('#copy-output').textContent = 'Copy current output', 1200);
  } catch {
    const range = document.createRange();
    range.selectNodeContents($('#output-preview'));
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
  }
});

['title','language','topic','sources','minutes','scene-count','aspect','resolution','model','duration','person','references','mode','max-clips','notebook-id','approval']
  .forEach((id) => $(`#${id}`).addEventListener('input', recalc));

createStarter();
go('project');
selectOutput('storyboard');
