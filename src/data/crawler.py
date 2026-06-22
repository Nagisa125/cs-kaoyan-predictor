"""Auto-crawler for postgraduate exam score data.

Given a school name and major code, attempts to auto-discover:
1. 复试线 from known aggregator URLs
2. 拟录取名单 data from school announcements
3. Structured extraction using keyword matching + regex patterns

Strategy: maintain a registry of known-good data source URLs per school,
falling back to search-based discovery for new schools.

Usage:
    # Crawl a single school
    python3 -m src.data.crawler "同济大学" --year 2026

    # Crawl all known schools for 2026
    python3 -m src.data.crawler --all --year 2026 --output data.json
"""

import json
import os
import re
import time
import urllib.parse
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

CACHE_DIR = Path(__file__).parent / ".cache"

# ═══ Known-good data source URLs ═══
# These are manually verified pages that contain structured score data.
# New schools should be added here as they are discovered.
KNOWN_SOURCES: dict[str, dict[str, str]] = {
    "同济大学": {
        "2026": "https://www.vipkaoyan.net/news/content_14316.shtml",
        "2025": "https://yz.chsi.com.cn/kyzx/fsfsx34/202503/20250315/2256789.html",
        "aggregator": "https://www.vipkaoyan.net/news/?s=同济大学+计算机+408",
    },
    "武汉大学": {
        "2026": "https://cs.whu.edu.cn/info/1055/59451.htm",
        "aggregator": "https://www.vipkaoyan.net/news/?s=武汉大学+计算机+408",
    },
    "华中科技大学": {
        "aggregator": "https://m.koolearn.com/kaoyan/20251114/1901844.html",
        "2025": "https://m.gaodun.com/kaoyan/1363963.html",
    },
    "南京大学": {
        "aggregator": "https://m-jixun.iqihang.com/zixun/changshi/2025697282.html",
    },
    "中山大学": {
        "aggregator": "https://m-jixun.iqihang.com/index.php?m=content&c=index&a=show&catid=183&id=696134",
    },
    "上海交通大学": {
        "aggregator": "https://m.koolearn.com/kaoyan/20260520/1945250.html",
    },
    "浙江大学": {
        "aggregator": "https://m-jixun.iqihang.com/zixun/changshi/2025697458.html",
        "2026": "http://www.cst.zju.edu.cn/2026/0317/c32178a3141657/page.htm",
    },
    "电子科技大学": {
        "aggregator": "https://m-jixun.iqihang.com/zixun/changshi/2025695303.html",
        "2026": "https://zhuanlan.zhihu.com/p/2025885166158062810",
    },
    "哈尔滨工业大学": {
        "aggregator": "https://m-jixun.iqihang.com/index.php?m=content&c=index&a=show&catid=1723&id=706025",
    },
}


@dataclass
class CrawledData:
    """Extracted score data for one school + major + year."""

    school: str
    major_code: str
    year: int

    # Score lines
    national_line: Optional[int] = None  # 国家线 (工学)
    school_line: Optional[int] = None  # 校线
    college_line: Optional[int] = None  # 院线/复试线

    # Admission stats
    admitted_count: Optional[int] = None
    lowest_score: Optional[int] = None
    avg_score: Optional[float] = None
    highest_score: Optional[int] = None

    # Exam subjects
    exam_subjects: Optional[str] = None  # e.g. "11408"

    # Metadata
    source_urls: list[str] = field(default_factory=list)
    confidence: str = "low"  # high / medium / low

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}


def _smart_extract(html: str, school: str = "") -> dict:
    """Extract score data from HTML using keyword patterns.

    Returns dict with keys: college_line, lowest_score, avg_score,
    highest_score, admitted_count, exam_subjects.
    """
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(separator=" ", strip=True)
    # Also preserve table structure
    for table in soup.find_all("table"):
        rows = []
        for tr in table.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if cells:
                rows.append(" | ".join(cells))
        text += "\n" + "\n".join(rows)

    result = {}

    # ── 复试线 ──
    # Match narrative format: "计院计科375、软工357" or "电子信息347"
    narrative_matches = re.findall(
        r'(?:复试线|分数线)[：:\s]*([^。；;]+)',
        text
    )
    for nm in narrative_matches:
        # Extract "keyword+number" pairs
        pairs = re.findall(
            r'(?:计院|软院|网安|电子信息|计算机|软件|人工智能|AI|智科)'
            r'(?:计[科学硕]*|专硕|软[工学]*|网安)?'
            r'[：:\s]*(\d{3})',
            nm
        )
        if pairs and "college_line" not in result:
            result["college_line"] = int(pairs[0])
        # Also try "25年复试线：计院计科375、软工357"
        for p in pairs:
            val = int(p)
            if 250 <= val <= 450:
                if "college_line" not in result:
                    result["college_line"] = val
                break

    score_patterns = [
        # Pattern: "复试线" or "复试分数线" followed by a number
        (r'复试[总分线]*[：:\s]*(\d{3})', "college_line"),
        (r'复试分数线[：:\s]*(\d{3})', "college_line"),
        (r'进入复试.*?(\d{3})\s*分', "college_line"),
        (r'院线[：:\s]*(\d{3})', "college_line"),
        # Year in table format: "2026 | 340" etc
        (r'2026.*?\|\s*(\d{3})\s*\|', "college_line"),
    ]
    for pattern, key in score_patterns:
        matches = re.findall(pattern, text)
        if matches and key not in result:
            val = int(matches[0])
            if 250 <= val <= 450:
                result[key] = val

    # ── 录取最低分 ──
    low_patterns = [
        (r'录取最低分[：:\s]*(\d{3})', "lowest_score"),
        (r'最低分[：:\s]*(\d{3})', "lowest_score"),
        (r'拟录取最低分[：:\s]*(\d{3})', "lowest_score"),
    ]
    for pattern, key in low_patterns:
        matches = re.findall(pattern, text)
        if matches and "lowest_score" not in result:
            val = int(matches[0])
            if 250 <= val <= 450:
                result["lowest_score"] = val

    # ── 录取平均分 ──
    avg_patterns = [
        (r'录取平均分[：:\s]*(\d{3}\.*\d*)', "avg_score"),
        (r'平均分[：:\s]*(\d{3}\.*\d*)', "avg_score"),
        (r'拟录取均分[：:\s]*(\d{3}\.*\d*)', "avg_score"),
        (r'录取均分[：:\s]*(\d{3}\.*\d*)', "avg_score"),
    ]
    for pattern, key in avg_patterns:
        matches = re.findall(pattern, text)
        if matches and "avg_score" not in result:
            try:
                result["avg_score"] = float(matches[0])
            except ValueError:
                pass

    # ── 录取最高分 ──
    high_patterns = [
        (r'录取最高分[：:\s]*(\d{3})', "highest_score"),
        (r'最高分[：:\s]*(\d{3})', "highest_score"),
    ]
    for pattern, key in high_patterns:
        matches = re.findall(pattern, text)
        if matches and "highest_score" not in result:
            val = int(matches[0])
            if 250 <= val <= 500:
                result["highest_score"] = val

    # ── 录取人数 ──
    admit_patterns = [
        (r'统考录取[人数]*[：:\s]*(\d+)\s*人', "admitted_count"),
        (r'录取[人数]*[：:\s]*(\d+)\s*人', "admitted_count"),
        (r'拟录取[人数]*[：:\s]*(\d+)\s*人', "admitted_count"),
        (r'招生[人数]*[：:\s]*(\d+)\s*人', "admitted_count"),
    ]
    for pattern, key in admit_patterns:
        matches = re.findall(pattern, text)
        if matches and "admitted_count" not in result:
            val = int(matches[0])
            if 1 <= val <= 500:
                result["admitted_count"] = val

    # ── 考试科目 ──
    if "408" in text:
        if "英语一" in text or "英语（一）" in text or "201" in text:
            if "数学一" in text or "数学（一）" in text or "301" in text:
                result["exam_subjects"] = "11408"
            elif "数学二" in text or "数学（二）" in text or "302" in text:
                result["exam_subjects"] = "22408"

    return result


class ScoreCrawler:
    """Crawler for postgraduate exam score data."""

    def __init__(self, cache: bool = True):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.cache = cache
        if cache:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _fetch(self, url: str, timeout: int = 20) -> Optional[str]:
        """Fetch a URL with caching."""
        cache_key = urllib.parse.quote(url, safe="")[:100]
        cache_file = CACHE_DIR / cache_key

        if self.cache and cache_file.exists():
            # Return cached content if less than 1 hour old
            if time.time() - cache_file.stat().st_mtime < 3600:
                return cache_file.read_text(encoding="utf-8", errors="ignore")

        try:
            resp = self.session.get(url, timeout=timeout)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
            text = resp.text
            if self.cache:
                cache_file.write_text(text, encoding="utf-8", errors="ignore")
            return text
        except Exception as e:
            print(f"  [WARN] Failed to fetch {url}: {e}")
            return None

    def _extract_numbers(self, text: str) -> list[int]:
        """Extract all 3-digit+ numbers from text."""
        return [int(m) for m in re.findall(r'\b(\d{3,4})\b', text)]

    def _search_score_context(self, text: str, keywords: list[str],
                              window: int = 200) -> list[dict]:
        """Find score-related numbers near keywords."""
        results = []
        for kw in keywords:
            for m in re.finditer(re.escape(kw), text):
                ctx_start = max(0, m.start() - window)
                ctx_end = min(len(text), m.end() + window)
                ctx = text[ctx_start:ctx_end]
                nums = self._extract_numbers(ctx)
                if nums:
                    results.append({
                        "keyword": kw,
                        "context": ctx[:300],
                        "numbers": nums,
                    })
        return results

    # ── Batch crawl ──
    def crawl_all(self, year: int = 2026) -> dict[str, CrawledData]:
        """Crawl all known schools."""
        results = {}
        for school in KNOWN_SOURCES:
            results[school] = self.crawl(school, year=year)
        return results

    # ── Main entry point ──
    def crawl(self, school: str, major_code: str = "085404",
              year: int = 2026) -> CrawledData:
        """Main crawl method.

        Priority: known source URLs → web search → manual prompt.
        """
        print(f"\n🔍 {school} {major_code} ({year}年)")

        data = CrawledData(school=school, major_code=major_code, year=year)
        sources = KNOWN_SOURCES.get(school, {})

        # Step 1: Try known aggregator URL (richest data)
        agg_url = sources.get("aggregator")
        if agg_url:
            print(f"  → 聚合站: {agg_url[:60]}...")
            html = self._fetch(agg_url)
            if html:
                extracted = _smart_extract(html, school)
                self._merge(data, extracted)
                data.source_urls.append(agg_url)
                print(f"    提取到: {list(extracted.keys())}")

        # Step 2: Try year-specific URL
        year_url = sources.get(str(year))
        if year_url:
            print(f"  → 年度页: {year_url[:60]}...")
            html = self._fetch(year_url)
            if html:
                extracted = _smart_extract(html, school)
                self._merge(data, extracted)
                data.source_urls.append(year_url)
                print(f"    提取到: {list(extracted.keys())}")

        # Step 3: Search-based discovery for unknown schools
        if not data.source_urls:
            print(f"  → 搜索发现...")
            for query in [
                f"{school} {year} 计算机 408 复试线",
                f"{school} {year}年 考研 复试分数线",
            ]:
                search_url = (
                    f"https://www.baidu.com/s?wd={urllib.parse.quote(query)}"
                )
                html = self._fetch(search_url)
                if html:
                    # Extract score hints from snippet text
                    nums = [int(m) for m in re.findall(
                        r'(?:复试线|分数线).*?(\d{3})', html
                    )]
                    nums = [n for n in nums if 250 <= n <= 450]
                    if nums and not data.college_line:
                        from collections import Counter
                        data.college_line = Counter(nums).most_common(1)[0][0]
                        data.confidence = "low"

        # Confidence assessment
        found = sum(1 for v in [
            data.college_line, data.lowest_score,
            data.avg_score, data.admitted_count
        ] if v is not None)
        if found >= 3:
            data.confidence = "high"
        elif found >= 2:
            data.confidence = "medium"

        print(f"  ✅ {found} 项数据 (置信度: {data.confidence})")
        if data.source_urls:
            print(f"  来源: {data.source_urls[0]}")
        return data

    def _merge(self, data: CrawledData, extracted: dict):
        """Merge extracted data, not overwriting existing values."""
        field_map = {
            "college_line": "college_line",
            "school_line": "school_line",
            "lowest_score": "lowest_score",
            "avg_score": "avg_score",
            "highest_score": "highest_score",
            "admitted_count": "admitted_count",
            "exam_subjects": "exam_subjects",
        }
        for src, dst in field_map.items():
            if src in extracted and getattr(data, dst) is None:
                setattr(data, dst, extracted[src])

    def crawl_to_school_program(
        self, school: str,
        major: str = "计算机技术(085404)",
        major_type: str = "专硕",
        college: str = "计算机学院",
        exam_code: str = "11408",
        years: list[int] = None,
        peers: list[str] = None,
        **kwargs,
    ) -> dict:
        """Crawl multiple years and output SchoolProgram-compatible dict."""
        if years is None:
            years = list(range(2022, 2027))

        program = {
            "school": school, "major": major,
            "major_type": major_type, "college": college,
            "exam_code": exam_code,
            "scores": {}, "admitted": {},
            "avg_scores": {}, "min_scores": {}, "max_scores": {},
            "ratios": {}, "peers": peers or [], "peer_scores": {},
            **kwargs,
        }

        for year in years:
            data = self.crawl(school, year=year)
            line = data.college_line or data.school_line
            if line:
                program["scores"][year] = line
            if data.admitted_count:
                program["admitted"][year] = data.admitted_count
            if data.avg_score:
                program["avg_scores"][year] = data.avg_score
            if data.lowest_score:
                program["min_scores"][year] = data.lowest_score
            if data.highest_score:
                program["max_scores"][year] = data.highest_score

        return program


# ── CLI ──
if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="408 考研数据自动爬取")
    p.add_argument("school", nargs="?", help="学校名称，如 同济大学。不指定则爬取全部已知院校")
    p.add_argument("--major-code", "-m", default="085404")
    p.add_argument("--year", "-y", type=int, default=2026)
    p.add_argument("--all", action="store_true", help="爬取全部已知院校")
    p.add_argument("--output", "-o", help="输出 JSON 文件路径")
    p.add_argument("--no-cache", action="store_true")

    args = p.parse_args()
    crawler = ScoreCrawler(cache=not args.no_cache)

    if args.all or args.school is None:
        results = crawler.crawl_all(year=args.year)
        output = {s: d.to_dict() for s, d in results.items()}
    else:
        data = crawler.crawl(args.school, major_code=args.major_code,
                             year=args.year)
        output = data.to_dict()

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\n已保存到: {args.output}")
    else:
        print("\n" + json.dumps(output, ensure_ascii=False, indent=2))
