// EM Biweekly — app.js

const JOURNAL_TAGS = {
  'NEJM': 'tag-nejm',
  'JAMA': 'tag-jama',
  'Lancet': 'tag-lancet',
  'Annals of Emergency Medicine': 'tag-annals',
  'Resuscitation': 'tag-resus',
  'American Journal of Emergency Medicine': 'tag-ajem',
  'Critical Care': 'tag-critcare',
};

const STUDY_TYPES = {
  'RCT': 'type-rct',
  'Meta-Analysis': 'type-meta',
  'Cohort Study': 'type-cohort',
  'Secondary Analysis': 'type-secondary',
};

function getJournalClass(journal) {
  if (journal.includes('N Engl J Med') || journal === 'NEJM') return 'tag-nejm';
  if (journal.includes('JAMA') && !journal.includes('Intern')) return 'tag-jama';
  if (journal.includes('Lancet')) return 'tag-lancet';
  if (journal.includes('Annals')) return 'tag-annals';
  if (journal.includes('Resuscitation')) return 'tag-resus';
  if (journal.includes('Am J Emerg') || journal.includes('American Journal of Emergency')) return 'tag-ajem';
  if (journal.includes('Crit Care') || journal.includes('Critical Care')) return 'tag-critcare';
  return 'tag-other';
}

function getTypeClass(type) {
  if (type === 'RCT') return 'type-rct';
  if (type === 'Meta-Analysis') return 'type-meta';
  if (type === 'Cohort Study') return 'type-cohort';
  return 'type-secondary';
}

function renderArticle(a) {
  const journalClass = getJournalClass(a.journal);
  const typeClass = getTypeClass(a.category);

  const prosHTML = a.pros.map(p => `<li><span>${p}</span></li>`).join('');
  const consHTML = a.cons.map(c => `<li><span>${c}</span></li>`).join('');

  return `
    <div class="article-card" data-type="${a.category}" data-journal="${a.journal_abbr || a.journal}">
      <div class="card-header">
        <div class="rank-badge">${a.rank}</div>
        <div class="card-meta">
          <div class="journal-row">
            <span class="journal-tag ${journalClass}">${a.journal_abbr || a.journal}</span>
            <span class="study-type ${typeClass}">${a.category}</span>
            <span class="pub-date">${a.pubdate}</span>
          </div>
          <div class="article-title">${a.title}</div>
          <div class="article-authors">${a.authors}</div>
          <a class="pmid-link" href="https://pubmed.ncbi.nlm.nih.gov/${a.pmid}/" target="_blank" rel="noopener">
            📎 PMID: ${a.pmid} ${a.doi ? '| DOI: ' + a.doi : ''}
          </a>
        </div>
      </div>
      <div class="card-sections">
        ${renderSection('📋', '研究背景', a.background)}
        ${renderSection('🔬', '研究設計與方法', a.methods)}
        ${renderSection('📊', '詳細研究結果', a.results, true)}
        ${renderEbmStats(a)}
        ${renderSection('💬', '討論', a.discussion)}
        ${renderSection('⚠️', '研究限制', a.limitations)}
        <div class="section">
          <div class="section-header">
            <span class="section-icon">🏆</span><span class="section-title">最重要結論</span>
          </div>
          <div class="section-body">
            <div class="conclusion-box">
              <h4>Claude 分析結論</h4>
              <p>${a.conclusion}</p>
            </div>
            <div class="pros-cons" style="margin-top:16px;">
              <div class="pros">
                <h4>✅ 本研究優點</h4>
                <ul>${prosHTML}</ul>
              </div>
              <div class="cons">
                <h4>❌ 本研究缺點</h4>
                <ul>${consHTML}</ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
}

function renderSection(icon, title, content) {
  return `
    <div class="section">
      <div class="section-header">
        <span class="section-icon">${icon}</span><span class="section-title">${title}</span>
      </div>
      <div class="section-body"><p>${content}</p></div>
    </div>
  `;
}

function renderEbmStats(a) {
  if (!a.ebm_stats || !a.study_design || a.study_design === 'other') return '';

  const stats = a.ebm_stats;
  let fields = [];

  if (a.study_design === 'treatment') {
    fields = [
      { key: 'arr', label: 'ARR',  desc: '絕對風險差' },
      { key: 'rrr', label: 'RRR',  desc: '相對風險降低' },
      { key: 'nnt', label: 'NNT',  desc: '需治療人數' },
      { key: 'hr',  label: 'HR',   desc: '危險比' },
      { key: 'or',  label: 'OR',   desc: '勝算比' },
      { key: 'nnh', label: 'NNH',  desc: '傷害需治人數' },
    ];
  } else if (a.study_design === 'diagnostic') {
    fields = [
      { key: 'sensitivity', label: 'Sensitivity', desc: '敏感度' },
      { key: 'specificity', label: 'Specificity', desc: '特異度' },
      { key: 'lr_pos',      label: 'LR+',         desc: '陽性似然比' },
      { key: 'lr_neg',      label: 'LR−',         desc: '陰性似然比' },
      { key: 'ppv',         label: 'PPV',         desc: '陽性預測值' },
      { key: 'npv',         label: 'NPV',         desc: '陰性預測值' },
      { key: 'auc',         label: 'AUC',         desc: 'ROC 曲線下面積' },
    ];
  }

  const visible = fields.filter(f => stats[f.key] != null);
  if (visible.length === 0) return '';

  const cells = visible.map(f => `
    <div style="background:#f0f4f8; border-radius:8px; padding:10px 12px; text-align:center; min-width:90px;">
      <div style="font-size:11px; color:#636e72; margin-bottom:3px; font-weight:600; letter-spacing:0.5px;">${f.label}</div>
      <div style="font-size:15px; font-weight:700; color:#2c3e50; word-break:break-word;">${stats[f.key]}</div>
      <div style="font-size:10px; color:#95a5a6; margin-top:2px;">${f.desc}</div>
    </div>
  `).join('');

  const noteHTML = stats.note
    ? `<p style="margin:10px 0 0; font-size:12px; color:#7f8c8d; line-height:1.5;">📝 ${stats.note}</p>`
    : '';

  return `
    <div class="section">
      <div class="section-header">
        <span class="section-icon">📐</span><span class="section-title">EBM 關鍵數值</span>
      </div>
      <div class="section-body">
        <div style="display:flex; flex-wrap:wrap; gap:8px;">
          ${cells}
        </div>
        ${noteHTML}
      </div>
    </div>
  `;
}

function filterArticles(type) {
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');

  document.querySelectorAll('.article-card').forEach(card => {
    if (type === 'all') {
      card.style.display = '';
    } else {
      card.style.display = card.dataset.type === type ? '' : 'none';
    }
  });
}

// Load and render
async function init() {
  const res = await fetch('data/latest.json');
  const data = await res.json();

  document.getElementById('week-range').textContent = data.week;
  document.getElementById('article-count').textContent = data.articles.length;

  const rctCount = data.articles.filter(a => a.category === 'RCT').length;
  const metaCount = data.articles.filter(a => a.category === 'Meta-Analysis').length;
  document.getElementById('rct-count').textContent = rctCount;
  document.getElementById('meta-count').textContent = metaCount;

  const container = document.getElementById('articles');
  container.innerHTML = data.articles.map(renderArticle).join('');
}

init().catch(console.error);
