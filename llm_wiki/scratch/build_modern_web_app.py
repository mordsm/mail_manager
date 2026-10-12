import json
import re
from pathlib import Path

def generate_web_app():
    root_dir = Path(".")
    book_dir = root_dir / "wiki" / "research" / "books" / "inner_gate"
    site_dir = root_dir / "site" / "inner_gate"
    site_dir.mkdir(parents=True, exist_ok=True)

    # Distinct Key Concepts per Chapter
    chapter_concepts = {
        1: ["מערכת העיכול", "פה וושט", "הקיבה", "המעי הדק", "המעי הגס"],
        2: ["מיקרוביום", "מחסום המעי", "חומצות שומן קצרות שרשרת", "בוטיראט", "מזונות מותססים"],
        3: ["פרה־ביוטיקה", "סיבים תזונתיים", "תזונה ים־תיכונית ירוקה", "מנקאי", "אנטיביוטיקה"],
        4: ["צלחת מאוזנת", "דגנים וקטניות", "תוויות מזון", "Meal Prep"],
        5: ["נפיחות וגזים", "עצירות", "שלשול", "IBS - מעי רגיז", "FODMAP", "צליאק", "צרבת"],
        6: ["בדיקות דם", "בדיקות צואה", "קלפרוטקטין", "בדיקות נשיפה", "אנדוסקופיה"],
        7: ["תרופות", "PPI", "NSAIDs", "מטפורמין", "ברזל ומגנזיום"],
        8: ["גיל מבוגר", "הריון וילדים", "סוכרת", "מחלת כליות"],
        9: ["ציר המעי–מוח", "סרוטונין", "דופמין", "GABA", "עייפות כרונית"],
        10: ["כרונו־תזונה", "השעון הצירקדי", "כרונוטיפ", "מלטונין", "אכילה מוגבלת בזמן 16:8"],
        11: ["תזמון רכיבים", "קפאין", "החלון האנאבולי", "גליקוגן"],
        12: ["שינה", "לחץ", "שגרת ערב", "CBT-I"],
        13: ["תנועה", "הליכה", "Pacing", "PEM"],
        14: ["הרגלים אטומיים", "Tiny Habits", "Habit Stacking", "תוכנית אם-אז"],
        15: ["רווח משני", "יומן טריגרים", "עיגון", "סוויש", "מסגור מחדש", "NLP"],
        16: ["תוכנית 7 הימים", "גיוון צמחי", "מתכוני בסיס"],
        17: ["יומן 14 ימים", "CEO Code", "סולם בריסטול"],
        18: ["מיתוסים", "בדיקות מסחריות", "דיטוקס", "שיווק"],
        19: ["תוחלת בריאות", "התאוששות ממעידה", "מפת העוגנים"]
    }

    chapters = []
    for num in range(1, 20):
        ch_file = book_dir / f"chapter_{num:02d}.md"
        if ch_file.exists():
            content = ch_file.read_text(encoding="utf-8")
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    content = parts[2].strip()

            title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            title = title_match.group(1) if title_match else f"פרק {num}"

            concepts = chapter_concepts.get(num, ["מיקרוביום", "מערכת העיכול"])

            chapters.append({
                "number": num,
                "title": title,
                "concepts": concepts,
                "content": content
            })

    # Generate custom MOC markdown with exact distinct concepts
    moc_rows = []
    for ch in chapters:
        concepts_str = ", ".join([f"[[{c}]]" for c in ch["concepts"]])
        moc_rows.append(f"| **פרק {ch['number']}** | {ch['title']} | {concepts_str} | [[chapter_{ch['number']:02d}]] |")

    moc_content = f"""# 🧠 שער פנימי — מפת הידע והרשת (Master Knowledge Graph MOC)

ברוכים הבאים לפורטל הידע האינטראקטיבי של הספר **"שער פנימי: המעי, האנרגיה והבריאות"**.
כל 19 הפרקים מעוגנים ברזולוציית בלוקים (`^block-id`), מקושרים לרשת המושגים המרכזית, וניתנים לקריאה ולניווט מלא.

---

## 🗺️ מפת הפרקים והרשת המקושרת

| פרק | נושא מרכזי | מושגי מפתח מקושרים | קובץ אובסידיאן |
| :--- | :--- | :--- | :--- |
""" + "\n".join(moc_rows) + """

---

## 🔗 רשת מושגי הידע המרכזיים (Core Concept Nodes)

- **מערכת העיכול והאנטומיה:** [[מערכת העיכול]], [[מיקרוביום]], [[סרוטונין]], [[ציר המעי–מוח]]
- **מטבוליזם ותזונה:** [[בוטיראט]], [[חומצות שומן קצרות שרשרת]], [[פרה־ביוטיקה]], [[פרוביוטיקה]], [[FODMAP]]
- **אבחון ורפואה:** [[IBS]], [[צליאק]], [[סולם בריסטול]]
- **אורח חיים והרגלים:** [[כרונו־תזונה]], [[אכילה מוגבלת בזמן 16:8]], [[קפאין]], [[הרגלים אטומיים]], [[Tiny Habits]], [[NLP]]
"""

    chapters_json = json.dumps(chapters, ensure_ascii=False)
    moc_json = json.dumps(moc_content, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>שער פנימי — אפליקציית ידע ומידע אינטראקטיבית | OCKA Web App</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            margin: 0;
            padding: 0;
            background: #090d16;
            color: #f8fafc;
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}

        /* TOP APP BAR */
        .top-app-bar {{
            height: 60px;
            background: #0f172a;
            border-bottom: 1px solid #1e293b;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 1.5rem;
            flex-shrink: 0;
            z-index: 100;
        }}

        .brand {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .brand-logo {{
            background: linear-gradient(135deg, #0284c7, #22c55e);
            color: #fff;
            font-weight: bold;
            font-size: 1.2rem;
            width: 38px;
            height: 38px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 12px rgba(2, 132, 199, 0.4);
        }}

        .brand-title {{
            font-size: 1.15rem;
            font-weight: bold;
            color: #38bdf8;
        }}

        .brand-subtitle {{
            font-size: 0.8rem;
            color: #64748b;
            margin-right: 8px;
        }}

        .top-actions {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .app-btn {{
            background: #1e293b;
            color: #38bdf8;
            border: 1px solid #334155;
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 0.88rem;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s;
        }}

        .app-btn:hover {{
            background: #0284c7;
            color: #fff;
            border-color: #38bdf8;
        }}

        .app-btn.primary {{
            background: linear-gradient(135deg, #0284c7, #0369a1);
            color: #fff;
            border: none;
        }}

        .app-btn.primary:hover {{
            background: linear-gradient(135deg, #0369a1, #075985);
            box-shadow: 0 0 10px rgba(2, 132, 199, 0.5);
        }}

        /* FULL WORKSPACE GRID - NO EMPTY MARGINS */
        .workspace {{
            display: grid;
            grid-template-columns: 320px 1fr 340px;
            flex: 1;
            overflow: hidden;
            background: #090d16;
        }}

        /* COLUMN 1: NAVIGATION PANEL */
        .nav-panel {{
            background: #0f172a;
            border-left: 1px solid #1e293b;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}

        .search-box {{
            padding: 1rem;
            border-bottom: 1px solid #1e293b;
            background: #0b1329;
        }}

        .search-box input {{
            width: 100%;
            padding: 0.75rem 1rem;
            border-radius: 8px;
            border: 1px solid #334155;
            background: #0f172a;
            color: #fff;
            font-size: 0.95rem;
            outline: none;
        }}

        .search-box input:focus {{
            border-color: #38bdf8;
            box-shadow: 0 0 8px rgba(56, 189, 248, 0.3);
        }}

        .nav-list {{
            list-style: none;
            padding: 0.5rem;
            margin: 0;
            overflow-y: auto;
            flex: 1;
        }}

        .nav-item {{
            padding: 0.75rem 1rem;
            border-radius: 8px;
            margin-bottom: 4px;
            cursor: pointer;
            transition: all 0.15s ease;
            display: flex;
            align-items: center;
            gap: 10px;
            color: #cbd5e1;
            font-size: 0.92rem;
            border: 1px solid transparent;
        }}

        .nav-item:hover {{
            background: #1e293b;
            color: #38bdf8;
            border-color: #334155;
        }}

        .nav-item.active {{
            background: linear-gradient(90deg, #1e293b, #0f172a);
            color: #38bdf8;
            border-right: 4px solid #38bdf8;
            font-weight: bold;
        }}

        /* COLUMN 2: CENTER INTERACTIVE CONTENT WORKSPACE */
        .main-workspace {{
            display: flex;
            flex-direction: column;
            overflow: hidden;
            background: #090d16;
        }}

        .article-header {{
            padding: 1.25rem 2rem;
            background: #0f172a;
            border-bottom: 1px solid #1e293b;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}

        .article-header h1 {{
            margin: 0;
            font-size: 1.35rem;
            color: #38bdf8;
        }}

        .badge-tag {{
            background: rgba(56, 189, 248, 0.12);
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.3);
            padding: 4px 10px;
            border-radius: 16px;
            font-size: 0.8rem;
            font-weight: 600;
        }}

        .reader-body {{
            flex: 1;
            overflow-y: auto;
            padding: 2rem 3rem;
            line-height: 1.8;
            font-size: 1.05rem;
            color: #e2e8f0;
        }}

        .reader-body h1 {{ color: #38bdf8; font-size: 1.8rem; margin-top: 0; border-bottom: 2px solid #1e293b; padding-bottom: 0.5rem; }}
        .reader-body h2 {{ color: #7dd3fc; font-size: 1.4rem; margin-top: 2rem; }}
        .reader-body h3 {{ color: #a7f3d0; font-size: 1.2rem; }}
        .reader-body p {{ margin-bottom: 1.2rem; }}

        .block-anchor {{
            font-size: 0.75rem;
            color: #64748b;
            background: #1e293b;
            padding: 2px 6px;
            border-radius: 4px;
            margin-right: 6px;
            font-family: monospace;
            display: inline-block;
        }}

        .wikilink-btn {{
            color: #22c55e;
            text-decoration: none;
            border: 1px solid rgba(34, 197, 94, 0.4);
            font-weight: 600;
            padding: 3px 8px;
            background: rgba(34, 197, 94, 0.12);
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            margin: 2px;
        }}

        .wikilink-btn:hover {{
            background: #064e3b;
            color: #a7f3d0;
            border-color: #22c55e;
            box-shadow: 0 0 8px rgba(34, 197, 94, 0.4);
        }}

        .chapter-btn {{
            background: #38bdf8;
            color: #0f172a;
            font-weight: bold;
            border: none;
            padding: 4px 10px;
            border-radius: 6px;
            cursor: pointer;
            transition: 0.2s;
            font-size: 0.9rem;
        }}

        .chapter-btn:hover {{
            background: #7dd3fc;
            box-shadow: 0 0 10px rgba(56, 189, 248, 0.5);
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1.5rem 0;
            background: #0f172a;
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid #1e293b;
        }}

        th, td {{
            padding: 0.85rem 1rem;
            border: 1px solid #1e293b;
            text-align: right;
        }}

        th {{
            background: #1e293b;
            color: #38bdf8;
        }}

        /* FIGURE CARDS */
        .figure-card {{
            background: #0f172a;
            border: 2px solid #0284c7;
            border-radius: 12px;
            padding: 1.5rem;
            margin: 2rem 0;
            box-shadow: 0 8px 25px rgba(0,0,0,0.5);
        }}

        .figure-header {{
            color: #38bdf8;
            font-weight: bold;
            font-size: 1.15rem;
            margin-bottom: 0.75rem;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .figure-body {{
            color: #cbd5e1;
            font-size: 1rem;
            margin-bottom: 1rem;
        }}

        .figure-img {{
            width: 100%;
            max-height: 420px;
            object-fit: cover;
            border-radius: 8px;
            border: 1px solid #334155;
            cursor: pointer;
            transition: transform 0.2s ease;
        }}

        .figure-img:hover {{
            transform: scale(1.01);
            border-color: #38bdf8;
        }}

        /* COLUMN 3: RIGHT KNOWLEDGE & MEDIA DASHBOARD */
        .dashboard-panel {{
            background: #0f172a;
            border-right: 1px solid #1e293b;
            display: flex;
            flex-direction: column;
            overflow-y: auto;
            padding: 1.25rem;
            gap: 1.5rem;
        }}

        .panel-widget {{
            background: #090d16;
            border: 1px solid #1e293b;
            border-radius: 10px;
            padding: 1.25rem;
        }}

        .widget-title {{
            color: #38bdf8;
            font-size: 1.05rem;
            font-weight: bold;
            margin-top: 0;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .gallery-grid {{
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }}

        .gallery-thumb-card {{
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .gallery-thumb-card:hover {{
            border-color: #38bdf8;
            box-shadow: 0 0 10px rgba(56, 189, 248, 0.3);
        }}

        .gallery-thumb-img {{
            width: 100%;
            height: 130px;
            object-fit: cover;
            border-radius: 6px;
        }}

        .gallery-thumb-title {{
            font-size: 0.85rem;
            font-weight: bold;
            color: #e2e8f0;
            margin-top: 6px;
        }}

        .concept-cloud {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }}

        .concept-pill {{
            background: #1e293b;
            color: #22c55e;
            border: 1px solid rgba(34, 197, 94, 0.4);
            padding: 4px 10px;
            border-radius: 14px;
            font-size: 0.82rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .concept-pill:hover {{
            background: #064e3b;
            color: #a7f3d0;
            border-color: #22c55e;
        }}

        /* MODAL FULLSCREEN IMAGE VIEWER */
        .modal-backdrop {{
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.85);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            padding: 2rem;
        }}

        .modal-backdrop.open {{
            display: flex;
        }}

        .modal-img {{
            max-width: 90vw;
            max-height: 85vh;
            border-radius: 10px;
            border: 2px solid #38bdf8;
            box-shadow: 0 0 30px rgba(56, 189, 248, 0.5);
        }}
    </style>
</head>
<body>
    <!-- TOP APP BAR -->
    <div class="top-app-bar">
        <div class="brand">
            <div class="brand-logo">📖</div>
            <div>
                <span class="brand-title">שער פנימי</span>
                <span class="brand-subtitle">המעי, האנרגיה והבריאות | OCKA Knowledge App</span>
            </div>
        </div>
        <div class="top-actions">
            <a href="/" class="app-btn">🔍 חיפוש היברידי (RAG Portal)</a>
            <a href="/data/books/inner_gate_clean.docx" download class="app-btn primary">📥 הורד ספר DOCX</a>
        </div>
    </div>

    <!-- 3-COLUMN WORKSPACE -->
    <div class="workspace">
        <!-- COLUMN 1: NAVIGATION PANEL -->
        <div class="nav-panel">
            <div class="search-box">
                <input type="text" id="searchInput" placeholder="🔍 חפש בספר ובמושגים..." oninput="filterNav()">
            </div>
            <ul class="nav-list" id="navList">
                <li class="nav-item active" onclick="loadMOC()">🧠 מפת הידע והרשת (MOC)</li>
            </ul>
        </div>

        <!-- COLUMN 2: CENTER INTERACTIVE CONTENT WORKSPACE -->
        <div class="main-workspace">
            <div class="article-header">
                <h1 id="chapterTitle">שער פנימי — מפת הידע והרשת (MOC)</h1>
                <span class="badge-tag">OCKA Knowledge Spine</span>
            </div>
            <div class="reader-body" id="readerContent">
                <!-- Content Loads Here -->
            </div>
        </div>

        <!-- COLUMN 3: RIGHT KNOWLEDGE & MEDIA DASHBOARD -->
        <div class="dashboard-panel">
            <!-- WIDGET 1: VISUAL FIGURES GALLERY -->
            <div class="panel-widget">
                <h3 class="widget-title">🖼️ גלריית איורים ותמונות</h3>
                <div class="gallery-grid">
                    <div class="gallery-thumb-card" onclick="openModal('/assets/gut_barrier.jpg')">
                        <img src="/assets/gut_barrier.jpg" class="gallery-thumb-img" alt="מחסום המעי והמיקרוביום">
                        <div class="gallery-thumb-title">איור 2.2: מחסום המעי והמיקרוביום</div>
                    </div>
                    <div class="gallery-thumb-card" onclick="openModal('/assets/fermented_foods.jpg')">
                        <img src="/assets/fermented_foods.jpg" class="gallery-thumb-img" alt="מזונות מותססים">
                        <div class="gallery-thumb-title">איור 2.4: מזונות מותססים נפוצים</div>
                    </div>
                    <div class="gallery-thumb-card" onclick="openModal('/assets/bristol_chart.jpg')">
                        <img src="/assets/bristol_chart.jpg" class="gallery-thumb-img" alt="סולם בריסטול">
                        <div class="gallery-thumb-title">איור 17.2: סולם בריסטול למרקם יציאות</div>
                    </div>
                </div>
            </div>

            <!-- WIDGET 2: CORE CONCEPT CLOUD -->
            <div class="panel-widget">
                <h3 class="widget-title">🔗 עננן מושגי מפתח</h3>
                <div class="concept-cloud">
                    <span class="concept-pill" onclick="handleConceptClick('מיקרוביום')">מיקרוביום</span>
                    <span class="concept-pill" onclick="handleConceptClick('בוטיראט')">בוטיראט</span>
                    <span class="concept-pill" onclick="handleConceptClick('FODMAP')">FODMAP</span>
                    <span class="concept-pill" onclick="handleConceptClick('צליאק')">צליאק</span>
                    <span class="concept-pill" onclick="handleConceptClick('כרונו־תזונה')">כרונו־תזונה</span>
                    <span class="concept-pill" onclick="handleConceptClick('ציר המעי–מוח')">ציר המעי–מוח</span>
                    <span class="concept-pill" onclick="handleConceptClick('סולם בריסטול')">סולם בריסטול</span>
                    <span class="concept-pill" onclick="handleConceptClick('סרוטונין')">סרוטונין</span>
                    <span class="concept-pill" onclick="handleConceptClick('אכילה מוגבלת בזמן 16:8')">16:8 TRE</span>
                    <span class="concept-pill" onclick="handleConceptClick('IBS - מעי רגיז')">IBS</span>
                </div>
            </div>
        </div>
    </div>

    <!-- MODAL FULLSCREEN IMAGE VIEWER -->
    <div class="modal-backdrop" id="imgModal" onclick="closeModal()">
        <img src="" id="modalImg" class="modal-img" alt="High Resolution Image">
    </div>

    <script>
        const chaptersData = {chapters_json};
        const mocContent = {moc_json};

        function initNav() {{
            const list = document.getElementById('navList');
            chaptersData.forEach((ch, idx) => {{
                const li = document.createElement('li');
                li.className = 'nav-item';
                li.innerHTML = `<span>📖</span> <span>${{ch.title}}</span>`;
                li.onclick = () => loadChapter(idx);
                list.appendChild(li);
            }});
            loadMOC();
        }}

        function loadMOC() {{
            setActiveNav(0);
            document.getElementById('chapterTitle').textContent = 'שער פנימי — מפת הידע והרשת (Master MOC)';
            document.getElementById('readerContent').innerHTML = renderMarkdown(mocContent, 0);
        }}

        function loadChapter(index) {{
            setActiveNav(index + 1);
            const ch = chaptersData[index];
            document.getElementById('chapterTitle').textContent = ch.title;
            document.getElementById('readerContent').innerHTML = renderMarkdown(ch.content, ch.number);
            document.getElementById('readerContent').scrollTop = 0;
        }}

        function loadChapterByNumber(chNum) {{
            const idx = chNum - 1;
            if (idx >= 0 && idx < chaptersData.length) {{
                loadChapter(idx);
            }}
        }}

        function handleConceptClick(concept) {{
            const query = concept.toLowerCase();
            document.getElementById('searchInput').value = query;
            filterNav();
            
            const foundIdx = chaptersData.findIndex(c => c.content.toLowerCase().includes(query) || c.concepts.some(k => k.toLowerCase() === query));
            if (foundIdx !== -1) {{
                loadChapter(foundIdx);
            }}
        }}

        function setActiveNav(navIdx) {{
            const items = document.querySelectorAll('.nav-item');
            items.forEach((item, idx) => {{
                if (idx === navIdx) item.classList.add('active');
                else item.classList.remove('active');
            }});
        }}

        function renderMarkdown(md, chapterNum) {{
            if (!md) return '';
            let lines = md.split('\\n');
            let html = [];
            let inTable = false;
            let tableRows = [];

            for (let i = 0; i < lines.length; i++) {{
                let line = lines[i].trim();

                if (line.startsWith('|')) {{
                    if (!inTable) {{
                        inTable = true;
                        tableRows = [];
                    }}
                    tableRows.push(line);
                    continue;
                }} else if (inTable) {{
                    inTable = false;
                    html.push(renderTable(tableRows));
                    tableRows = [];
                }}

                if (!line) continue;

                if (line.startsWith('### ')) {{
                    html.push('<h3>' + processLine(line.substring(4)) + '</h3>');
                }} else if (line.startsWith('## ')) {{
                    html.push('<h2>' + processLine(line.substring(3)) + '</h2>');
                }} else if (line.startsWith('# ')) {{
                    html.push('<h1>' + processLine(line.substring(2)) + '</h1>');
                }} else if (line.startsWith('---')) {{
                    html.push('<hr style="border-color:#1e293b; margin:2rem 0;">');
                }} else {{
                    html.push('<p>' + processLine(line) + '</p>');
                }}
            }}

            if (inTable) {{
                html.push(renderTable(tableRows));
            }}

            // Inject Figures Guaranteed per Chapter
            if (chapterNum === 2) {{
                html.splice(4, 0, renderFigureCard('🖼️ איור 2.2: מחסום המעי והמיקרוביום', 'תרשים רפואי 3D: שכבת ריר מגינה, תאי אפיתל של המעי, חיבורים הדוקים (Tight Junctions), והרקמה שמתחת למחסום.', '/assets/gut_barrier.jpg'));
                html.splice(10, 0, renderFigureCard('🥗 איור 2.4: מזונות מותססים נפוצים', 'גלריית תמונות סטודיו: כרוב כבוש, קימצ׳י, קפיר, יוגורט פעיל, קומבוצ׳ה, מיסו וטמפה.', '/assets/fermented_foods.jpg'));
            }} else if (chapterNum === 5 || chapterNum === 17) {{
                html.splice(5, 0, renderFigureCard('📊 איור 17.2: סולם בריסטול למרקם יציאות', 'לוח אבחון רפואי רשמי להערכת מרקם היציאות (סוגים 1-7).', '/assets/bristol_chart.jpg'));
            }}

            return html.join('\\n');
        }}

        function processLine(text) {{
            text = text.replace(/\\[\\[chapter_(\\d+)\\]\\]/gi, (match, chNum) => {{
                return `<button onclick="loadChapterByNumber(${{parseInt(chNum)}})" class="chapter-btn">📖 פרק ${{parseInt(chNum)}}</button>`;
            }});

            text = text.replace(/\\[\\[([^\\]]+)\\]\\]/g, (match, concept) => {{
                return `<span onclick="handleConceptClick('${{concept}}')" class="wikilink-btn">🔗 ${{concept}}</span>`;
            }});

            text = text.replace(/\\^([a-zA-Z0-9_\\-]+)/g, '<span class="block-anchor">^$1</span>');
            return text;
        }}

        function renderTable(rows) {{
            if (rows.length < 2) return '';
            let out = '<table><thead><tr>';
            let headers = rows[0].split('|').map(c => c.trim()).filter(c => c !== '');
            headers.forEach(h => {{ out += '<th>' + processLine(h) + '</th>'; }});
            out += '</tr></thead><tbody>';

            for (let i = 2; i < rows.length; i++) {{
                let cells = rows[i].split('|').map(c => c.trim()).filter(c => c !== '');
                if (cells.length > 0) {{
                    out += '<tr>';
                    cells.forEach(c => {{ out += '<td>' + processLine(c) + '</td>'; }});
                    out += '</tr>';
                }}
            }}
            out += '</tbody></table>';
            return out;
        }}

        function renderFigureCard(title, description, imgSrc) {{
            return `
            <div class="figure-card">
                <div class="figure-header">${{title}}</div>
                <div class="figure-body">${{description}}</div>
                <img src="${{imgSrc}}" class="figure-img" alt="${{title}}" onclick="openModal('${{imgSrc}}')">
            </div>`;
        }}

        function filterNav() {{
            const query = document.getElementById('searchInput').value.toLowerCase();
            const items = document.querySelectorAll('.nav-item');
            items.forEach((item, idx) => {{
                if (idx === 0) return;
                const text = item.textContent.toLowerCase();
                const ch = chaptersData[idx - 1];
                const matchesConcept = ch && ch.concepts.some(c => c.toLowerCase().includes(query));
                if (text.includes(query) || matchesConcept) {{
                    item.style.display = 'flex';
                }} else {{
                    item.style.display = 'none';
                }}
            }});
        }}

        function openModal(imgSrc) {{
            document.getElementById('modalImg').src = imgSrc;
            document.getElementById('imgModal').classList.add('open');
        }}

        function closeModal() {{
            document.getElementById('imgModal').classList.remove('open');
        }}

        document.addEventListener('DOMContentLoaded', initNav);
    </script>
</body>
</html>"""

    output_file = site_dir / "index.html"
    output_file.write_text(html_content, encoding="utf-8")
    print(f"SUCCESS! Built 3-column Web Knowledge Application at {output_file}. File size: {len(html_content)}")

if __name__ == "__main__":
    generate_web_app()
