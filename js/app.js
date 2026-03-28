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
