#!/usr/bin/env python3
"""
EM Weekly — 每週急診文獻自動更新腳本
每週六凌晨 04:00（台灣時間）執行
搜尋 PubMed → 呼叫 Claude API 生成摘要 → 更新 data/latest.json
"""

import os
import json
import datetime
import urllib.request
import urllib.parse
import re
import time

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

TARGET_JOURNALS = [
    '"N Engl J Med"[Journal]',
    '"JAMA"[Journal]',
    '"Lancet"[Journal]',
    '"Ann Emerg Med"[Journal]',
    '"Resuscitation"[Journal]',
    '"Am J Emerg Med"[Journal]',
    '"Crit Care"[Journal]',
    '"Acad Emerg Med"[Journal]',
    '"Emerg Med J"[Journal]',
    '"BMJ"[Journal]',
]

EM_KEYWORDS = (
    "emergency OR resuscitation OR cardiac arrest OR sepsis OR trauma OR "
    "shock OR critical care OR ventilation OR hemorrhage OR stroke OR "
    "toxicology OR overdose OR anaphylaxis OR airway"
)


def get_date_range():
    today = datetime.date.today()
    start = today - datetime.timedelta(days=7)
    return start.strftime("%Y/%m/%d"), today.strftime("%Y/%m/%d"), \
           start.strftime("%Y/%m/%d"), today.strftime("%Y/%m/%d")


def fetch_url(url, timeout=30):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "EMWeekly/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8")
    except Exception as e:
        print(f"  Fetch error: {e}")
        return ""


def search_pubmed(journal_query, date_from, date_to, max_results=10):
    """Search PubMed for articles in specific journals within date range."""
    query = f"({journal_query}) AND ({EM_KEYWORDS})"
    encoded = urllib.parse.quote(query)
    date_range = f"{date_from}:{date_to}[edat]"
    url = (
        f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        f"?db=pubmed&term={encoded}+AND+{urllib.parse.quote(date_range)}"
        f"&retmax={max_results}&sort=pub_date&retmode=json"
    )
    html = fetch_url(url)
    if not html:
        return []
    try:
        data = json.loads(html)
        return data.get("esearchresult", {}).get("idlist", [])
    except:
        return []


def get_abstract(pmid):
    """Fetch article abstract from PubMed."""
    url = (
        f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        f"?db=pubmed&id={pmid}&retmode=text&rettype=abstract"
    )
    time.sleep(0.4)  # Rate limit
    return fetch_url(url)


def call_claude(prompt):
    """Call Claude API to generate article summary."""
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not set")

    payload = json.dumps({
        "model": "claude-opus-4-6",
        "max_tokens": 2000,
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        result = json.loads(r.read().decode("utf-8"))
    return result["content"][0]["text"]


def classify_study_type(abstract_text):
    text = abstract_text.lower()
    if any(k in text for k in ["randomized", "randomised", "rct", "randomly assigned"]):
        return "RCT"
    if any(k in text for k in ["meta-analysis", "systematic review", "systematic literature"]):
        return "Meta-Analysis"
    if any(k in text for k in ["cohort", "prospective", "retrospective", "registry", "observational"]):
        return "Cohort Study"
    return "Secondary Analysis"


def generate_article_summary(pmid, abstract_text, rank):
    """Use Claude to generate detailed Chinese summary."""
    prompt = f"""你是一位急診醫學論文研讀專家。請根據以下 PubMed 摘要，生成一個 JSON 格式的詳細中文文獻摘要。

PubMed 摘要：
{abstract_text[:3000]}

請直接輸出 JSON，格式如下（所有字段用繁體中文，不要有額外說明）：
{{
  "title": "論文英文標題",
  "authors": "第一作者 et al. (試驗名稱如有)",
  "journal": "期刊全名",
  "journal_abbr": "期刊縮寫",
  "pubdate": "YYYY-MM-DD",
  "pmid": "{pmid}",
  "doi": "DOI 如有，否則空字串",
  "category": "RCT 或 Meta-Analysis 或 Cohort Study 或 Secondary Analysis",
  "impact_factor": 0,
  "background": "詳細研究背景與臨床問題（150-200字）",
  "methods": "研究設計與方法，含樣本數、納排標準、介入、主要終點",
  "results": "詳細研究結果，含具體數字、OR/HR/RR值、p值、百分比",
  "discussion": "討論重點：機制解釋、與現有文獻比較（100-150字）",
  "limitations": "研究限制，條列式 3-5 點，以句號結尾，用換行分隔",
  "conclusion": "最重要結論（Claude 分析，50-80字）",
  "pros": ["優點1", "優點2", "優點3"],
  "cons": ["缺點1", "缺點2", "缺點3"]
}}"""

    try:
        text = call_claude(prompt)
        # Extract JSON from response
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            article = json.loads(match.group())
            article["id"] = rank
            article["rank"] = rank
            if "impact_factor" not in article:
                article["impact_factor"] = 0
            return article
    except Exception as e:
        print(f"  Claude error for PMID {pmid}: {e}")
    return None


def screen_articles_by_importance(candidates):
    """Use Claude to select clinically important articles from candidates (5-20)."""
    if not candidates:
        return []

    # Build a compact list of abstracts for screening
    items = []
    for i, (priority, pmid, abstract) in enumerate(candidates[:40], 1):
        # Truncate abstract to first 800 chars for screening efficiency
        items.append(f"[{i}] PMID:{pmid}\n{abstract[:800]}")

    prompt = f"""你是一位資深急診醫師，正在為每週急診文獻週報篩選文章。

以下是本週 PubMed 的候選文章摘要（共 {len(items)} 篇）。請以專業急診醫師的角度，選出真正值得急診科醫師閱讀的文章。

選文標準：
- 直接影響急診臨床決策（用藥、操作、診斷、處置）
- 研究族群與急診相關（急診病患、重症、院前、加護）
- 結果具實際意義（不只是統計顯著，要有臨床意義）
- 優先選 RCT、高品質 Cohort、重要 Meta-analysis
- 排除：純基礎研究、門診追蹤研究、與急診無關的亞族群分析

選取數量：5 至 20 篇，寧缺勿濫，沒有重要文章就少選。

候選文章：
{'='*60}
{chr(10).join(items)}
{'='*60}

請直接輸出被選中的 PMID 清單，格式如下（只輸出 JSON，不要其他說明）：
{{"selected_pmids": ["12345678", "23456789", ...]}}"""

    try:
        text = call_claude(prompt)
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            result = json.loads(match.group())
            pmids = result.get("selected_pmids", [])
            print(f"  Claude selected PMIDs: {pmids}")
            return set(str(p) for p in pmids)
    except Exception as e:
        print(f"  Screening error: {e}, falling back to top candidates")
        # Fallback: take top 12 by priority
        return set(pmid for (_, pmid, _) in candidates[:12])

    return set(pmid for (_, pmid, _) in candidates[:12])


def is_relevant_to_em(abstract_text):
    """Filter articles relevant to emergency medicine."""
    text = abstract_text.lower()
    em_terms = [
        "emergency", "resuscitat", "cardiac arrest", "sepsis", "trauma",
        "shock", "critical care", "mechanical ventilation", "hemorrhage",
        "stroke", "toxicolog", "overdose", "anaphylaxis", "airway",
        "icu", "intensive care", "intubat", "defibrillat", "cpr",
        "out-of-hospital", "prehospital", "myocardial infarction"
    ]
    return any(term in text for term in em_terms)


def main():
    date_from, date_to, df_fmt, dt_fmt = get_date_range()
    print(f"Searching PubMed: {date_from} to {date_to}")

    # Collect PMIDs from all target journals
    all_pmids = []
    journal_groups = [
        # High-impact general journals with EM filter
        ' OR '.join(['"N Engl J Med"[Journal]', '"JAMA"[Journal]', '"Lancet"[Journal]', '"BMJ"[Journal]']),
        # Dedicated EM journals (no keyword filter needed)
        '"Ann Emerg Med"[Journal] OR "Resuscitation"[Journal] OR "Am J Emerg Med"[Journal] OR "Acad Emerg Med"[Journal] OR "Emerg Med J"[Journal]',
        # Critical care
        '"Crit Care"[Journal] OR "Critical Care Medicine"[Journal]',
    ]

    for group in journal_groups:
        pmids = search_pubmed(group, date_from, date_to, max_results=15)
        print(f"  Found {len(pmids)} PMIDs")
        all_pmids.extend(pmids)
        time.sleep(0.5)

    # Deduplicate
    seen = set()
    unique_pmids = [p for p in all_pmids if not (p in seen or seen.add(p))]
    print(f"Total unique PMIDs: {len(unique_pmids)}")

    # Fetch abstracts and filter
    candidates = []
    for pmid in unique_pmids[:40]:
        abstract = get_abstract(pmid)
        if abstract and is_relevant_to_em(abstract):
            study_type = classify_study_type(abstract)
            priority = 0
            if "randomized" in abstract.lower() or "rct" in abstract.lower():
                priority = 3
            elif "meta-analysis" in abstract.lower():
                priority = 2
            elif "cohort" in abstract.lower() or "prospective" in abstract.lower():
                priority = 1
            candidates.append((priority, pmid, abstract))

    # Sort: RCTs first, then meta, then cohort
    candidates.sort(key=lambda x: -x[0])
    print(f"Total candidates: {len(candidates)}, running clinical importance screening...")

    # Ask Claude to screen which articles are truly important for EM physicians
    selected_pmids = screen_articles_by_importance(candidates)
    selected = [(p, pmid, ab) for (p, pmid, ab) in candidates if pmid in selected_pmids]
    print(f"Selected {len(selected)} articles after clinical screening")

    # Generate summaries with Claude
    articles = []
    for rank, (priority, pmid, abstract) in enumerate(selected, 1):
        print(f"  [{rank}/{len(selected)}] Generating summary for PMID {pmid}...")
        article = generate_article_summary(pmid, abstract, rank)
        if article:
            articles.append(article)
        time.sleep(1)

    if not articles:
        print("No articles generated. Keeping existing data.")
        return

    # Build output
    today = datetime.date.today()
    week_start = today - datetime.timedelta(days=7)
    output = {
        "week": f"{week_start.strftime('%Y/%m/%d')} – {today.strftime('%Y/%m/%d')}",
        "generated": today.strftime("%Y-%m-%d"),
        "articles": articles
    }

    # Write JSON
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    output_path = os.path.join(repo_root, "data", "latest.json")
    archive_dir = os.path.join(repo_root, "data", "archive")
    os.makedirs(archive_dir, exist_ok=True)

    # Archive previous week's data before overwriting
    if os.path.exists(output_path):
        try:
            with open(output_path, encoding="utf-8") as f:
                prev = json.load(f)
            prev_generated = prev.get("generated", "")
            prev_count = len(prev.get("articles", []))
            if prev_generated and prev_count > 0:
                archive_file = os.path.join(archive_dir, f"{prev_generated}.json")
                if not os.path.exists(archive_file):
                    with open(archive_file, "w", encoding="utf-8") as f:
                        json.dump(prev, f, ensure_ascii=False, indent=2)
                    print(f"Archived previous week to {prev_generated}.json")

                    # Update archive index
                    index_path = os.path.join(archive_dir, "index.json")
                    index = []
                    if os.path.exists(index_path):
                        with open(index_path, encoding="utf-8") as f:
                            index = json.load(f)
                    index.append({
                        "week": prev.get("week", ""),
                        "file": f"{prev_generated}.json",
                        "count": prev_count,
                        "generated": prev_generated
                    })
                    with open(index_path, "w", encoding="utf-8") as f:
                        json.dump(index, f, ensure_ascii=False, indent=2)
                    print(f"Updated archive index ({len(index)} entries)")
        except Exception as e:
            print(f"Archive warning: {e}")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(articles)} articles to {output_path}")


if __name__ == "__main__":
    main()
