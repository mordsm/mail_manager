import json
import re
from pathlib import Path

def build_enhanced_website():
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

ברוכים הבאים לחוט השדרה של הספר **"שער פנימי: המעי, האנרגיה והבריאות"**.
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

    html = """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>שער פנימי — המעי, האנרגיה והבריאות | ספר דיגיטלי אינטראקטיבי</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            margin: 0;
            padding: 0;
            background: #0f172a;
            color: #f8fafc;
            display: flex;
            height: 100vh;
            overflow: hidden;
        }
        
        .sidebar {
            width: 360px;
            background: #1e293b;
            border-left: 2px solid #334155;
            display: flex;
            flex-direction: column;
            flex-shrink: 0;
        }

        .sidebar-header {
            padding: 1.25rem;
            background: #0f172a;
            border-bottom: 1px solid #334155;
            text-align: center;
        }

        .sidebar-header h2 {
            margin: 0;
            color: #38bdf8;
            font-size: 1.25rem;
        }

        .sidebar-header p {
            margin: 4px 0 0 0;
            color: #94a3b8;
            font-size: 0.85rem;
        }

        .search-box {
            padding: 0.75rem 1rem;
            border-bottom: 1px solid #334155;
        }

        .search-box input {
            width: 100%;
            padding: 0.65rem 0.85rem;
            border-radius: 6px;
            border: 1px solid #475569;
            background: #0f172a;
            color: #fff;
            font-size: 0.95rem;
            box-sizing: border-box;
        }

        .nav-list {
            flex: 1;
            overflow-y: auto;
            padding: 0.5rem 0;
            list-style: none;
            margin: 0;
        }

        .nav-item {
            padding: 0.75rem 1.25rem;
            cursor: pointer;
            border-bottom: 1px solid #1e293b;
            color: #cbd5e1;
            font-size: 0.95rem;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 10px;
            line-height: 1.4;
        }

        .nav-item:hover {
            background: #334155;
            color: #38bdf8;
        }

        .nav-item.active {
            background: #0f172a;
            color: #38bdf8;
            font-weight: bold;
            border-right: 4px solid #38bdf8;
        }

        .main-container {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: #0f172a;
            overflow: hidden;
        }

        .top-bar {
            padding: 1rem 2.5rem;
            background: #1e293b;
            border-bottom: 1px solid #334155;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .top-bar h1 {
            margin: 0;
            font-size: 1.35rem;
            color: #f8fafc;
        }

        .badge-tag {
            background: #0284c7;
            color: #fff;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85rem;
            font-weight: bold;
        }

        .reader-content {
            flex: 1;
            overflow-y: auto;
            padding: 3rem 4rem;
            max-width: 960px;
            margin: 0 auto;
            width: 100%;
            line-height: 1.8;
            font-size: 1.15rem;
        }

        .reader-content h1, .reader-content h2, .reader-content h3 {
            color: #38bdf8;
            margin-top: 1.8rem;
            margin-bottom: 0.8rem;
        }

        .reader-content p {
            margin-bottom: 1.25rem;
            color: #e2e8f0;
        }

        .block-anchor {
            font-size: 0.75rem;
            color: #64748b;
            background: #1e293b;
            padding: 2px 6px;
            border-radius: 4px;
            margin-right: 6px;
            font-family: monospace;
            display: inline-block;
        }

        /* CLICKABLE WIKILINKS */
        .wikilink-btn {
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
        }

        .wikilink-btn:hover {
            background: #064e3b;
            color: #a7f3d0;
            border-color: #22c55e;
            box-shadow: 0 0 8px rgba(34, 197, 94, 0.4);
        }

        /* CLICKABLE CHAPTER BUTTONS IN TABLES */
        .chapter-btn {
            background: #38bdf8;
            color: #0f172a;
            font-weight: bold;
            border: none;
            padding: 4px 10px;
            border-radius: 6px;
            cursor: pointer;
            transition: 0.2s;
            font-size: 0.9rem;
        }

        .chapter-btn:hover {
            background: #7dd3fc;
            box-shadow: 0 0 10px rgba(56, 189, 248, 0.5);
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 1.5rem 0;
            background: #1e293b;
            border-radius: 8px;
            overflow: hidden;
        }

        th, td {
            padding: 0.85rem 1rem;
            border: 1px solid #334155;
            text-align: right;
        }

        th {
            background: #0f172a;
            color: #38bdf8;
        }

        /* RICH VISUAL FIGURE CARDS */
        .figure-card {
            background: #1e293b;
            border: 2px solid #38bdf8;
            border-radius: 12px;
            padding: 1.5rem;
            margin: 2rem 0;
            box-shadow: 0 8px 20px rgba(0,0,0,0.4);
        }

        .figure-header {
            color: #38bdf8;
            font-weight: bold;
            font-size: 1.15rem;
            margin-bottom: 0.75rem;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .figure-body {
            color: #cbd5e1;
            font-size: 1.05rem;
        }

        .bristol-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 12px;
            margin-top: 1rem;
        }

        .bristol-item {
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 12px;
        }

        .bristol-item h4 {
            margin: 0 0 6px 0;
            color: #f59e0b;
        }
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="sidebar-header">
            <h2>📖 שער פנימי</h2>
            <p>המעי, האנרגיה והבריאות | מאת משה</p>
        </div>
        <div class="search-box">
            <input type="text" id="searchInput" placeholder="🔍 חפש בספר..." oninput="filterNav()">
        </div>
        <ul class="nav-list" id="navList">
            <li class="nav-item active" onclick="loadMOC()">🧠 מפת הידע והרשת (MOC)</li>
        </ul>
    </div>

    <div class="main-container">
        <div class="top-bar">
            <h1 id="chapterTitle">שער פנימי — מפת הידע והרשת (MOC)</h1>
            <span class="badge-tag">OCKA Interactive Book</span>
        </div>
        <div class="reader-content" id="readerContent">
            <!-- Content Loads Here -->
        </div>
    </div>

    <script>
        const chaptersData = """ + chapters_json + """;
        const mocContent = """ + moc_json + """;

        function initNav() {
            const list = document.getElementById('navList');
            chaptersData.forEach((ch, idx) => {
                const li = document.createElement('li');
                li.className = 'nav-item';
                li.innerHTML = `<span>📖</span> <span>${ch.title}</span>`;
                li.onclick = () => loadChapter(idx);
                list.appendChild(li);
            });
            loadMOC();
        }

        function loadMOC() {
            setActiveNav(0);
            document.getElementById('chapterTitle').textContent = 'שער פנימי — מפת הידע והרשת (Master MOC)';
            document.getElementById('readerContent').innerHTML = renderMarkdown(mocContent);
        }

        function loadChapter(index) {
            setActiveNav(index + 1);
            const ch = chaptersData[index];
            document.getElementById('chapterTitle').textContent = ch.title;
            document.getElementById('readerContent').innerHTML = renderMarkdown(ch.content);
            document.getElementById('readerContent').scrollTop = 0;
        }

        function loadChapterByNumber(chNum) {
            const idx = chNum - 1;
            if (idx >= 0 && idx < chaptersData.length) {
                loadChapter(idx);
            }
        }

        function handleConceptClick(concept) {
            const query = concept.toLowerCase();
            document.getElementById('searchInput').value = query;
            filterNav();
            
            // Search for first chapter containing concept
            const foundIdx = chaptersData.findIndex(c => c.content.toLowerCase().includes(query) || c.concepts.some(k => k.toLowerCase() === query));
            if (foundIdx !== -1) {
                loadChapter(foundIdx);
            }
        }

        function setActiveNav(navIdx) {
            const items = document.querySelectorAll('.nav-item');
            items.forEach((item, idx) => {
                if (idx === navIdx) item.classList.add('active');
                else item.classList.remove('active');
            });
        }

        function renderMarkdown(md) {
            if (!md) return '';
            let lines = md.split('\\n');
            let html = [];
            let inTable = false;
            let tableRows = [];

            for (let i = 0; i < lines.length; i++) {
                let line = lines[i].trim();

                if (line.startsWith('|')) {
                    if (!inTable) {
                        inTable = true;
                        tableRows = [];
                    }
                    tableRows.push(line);
                    continue;
                } else if (inTable) {
                    inTable = false;
                    html.push(renderTable(tableRows));
                    tableRows = [];
                }

                if (!line) continue;

                // Render Visual Figures
                if (line.includes('איור 2.2')) {
                    html.push(renderFigureCard('🖼️ איור 2.2: מחסום המעי והמיקרוביום', 'שכבת ריר מגינה, תאי אפיתל של המעי, חיבורים הדוקים (Tight Junctions), והרקמה שמתחת למחסום.'));
                    continue;
                } else if (line.includes('איור 2.3')) {
                    html.push(renderFigureCard('🧪 איור 2.3: סיבים פרה-ביוטיים ומזון למיקרוביום', 'מקורות סיבים (שיבולת שועל, קטניות, שום, בצל, בננה) -> תסיסה מיקרוביאלית -> חומצות שומן קצרות שרשרת: אצטט, פרופיונאט, בוטיראט.'));
                    continue;
                } else if (line.includes('איור 2.4')) {
                    html.push(renderFigureCard('🥗 איור 2.4: מזונות מותססים נפוצים', 'כרוב כבוש, קימצ׳י, קפיר, יוגורט פעיל, קומבוצ׳ה, מיסו וטמפה.'));
                    continue;
                } else if (line.includes('איור 17.2')) {
                    html.push(renderBristolScaleCard());
                    continue;
                }

                if (line.startsWith('### ')) {
                    html.push('<h3>' + processLine(line.substring(4)) + '</h3>');
                } else if (line.startsWith('## ')) {
                    html.push('<h2>' + processLine(line.substring(3)) + '</h2>');
                } else if (line.startsWith('# ')) {
                    html.push('<h1>' + processLine(line.substring(2)) + '</h1>');
                } else if (line.startsWith('---')) {
                    html.push('<hr style="border-color:#334155; margin:2rem 0;">');
                } else {
                    html.push('<p>' + processLine(line) + '</p>');
                }
            }

            if (inTable) {
                html.push(renderTable(tableRows));
            }

            return html.join('\\n');
        }

        function processLine(text) {
            // Process Wikilinks [[chapter_XX]]
            text = text.replace(/\[\[chapter_(\d+)\]\]/gi, (match, chNum) => {
                return `<button onclick="loadChapterByNumber(${parseInt(chNum)})" class="chapter-btn">📖 פרק ${parseInt(chNum)}</button>`;
            });

            // Process Concept Wikilinks [[Concept]]
            text = text.replace(/\[\[([^\]]+)\]\]/g, (match, concept) => {
                return `<span onclick="handleConceptClick('${concept}')" class="wikilink-btn">🔗 ${concept}</span>`;
            });

            // Process Block Anchors ^block-xxxx
            text = text.replace(/\\^([a-zA-Z0-9_\\-]+)/g, '<span class="block-anchor">^$1</span>');
            return text;
        }

        function renderTable(rows) {
            if (rows.length < 2) return '';
            let out = '<table><thead><tr>';
            let headers = rows[0].split('|').map(c => c.trim()).filter(c => c !== '');
            headers.forEach(h => { out += '<th>' + processLine(h) + '</th>'; });
            out += '</tr></thead><tbody>';

            for (let i = 2; i < rows.length; i++) {
                let cells = rows[i].split('|').map(c => c.trim()).filter(c => c !== '');
                if (cells.length > 0) {
                    out += '<tr>';
                    cells.forEach(c => { out += '<td>' + processLine(c) + '</td>'; });
                    out += '</tr>';
                }
            }
            out += '</tbody></table>';
            return out;
        }

        function renderFigureCard(title, description) {
            return `
            <div class="figure-card">
                <div class="figure-header">${title}</div>
                <div class="figure-body">${description}</div>
            </div>`;
        }

        function renderBristolScaleCard() {
            return `
            <div class="figure-card">
                <div class="figure-header">💩 איור 17.2: סולם בריסטול — כלי לתיאור מרקם הצואה</div>
                <div class="figure-body">
                    <p>סולם בריסטול מתאר 7 סוגי מרקם צואה לצורך הערכה ומעקב:</p>
                    <div class="bristol-grid">
                        <div class="bristol-item">
                            <h4 style="color:#ef4444;">סוג 1-2 (עצירות)</h4>
                            <p style="font-size:0.9rem; margin:0;">גושים נפרדים וקשים כגאזים, או צואה מעוצבת וגושית.</p>
                        </div>
                        <div class="bristol-item">
                            <h4 style="color:#22c55e;">סוג 3-4 (תקין)</h4>
                            <p style="font-size:0.9rem; margin:0;">מעוצב עם סדקים או מעוצב וחלק כמו נקניק רך.</p>
                        </div>
                        <div class="bristol-item">
                            <h4 style="color:#38bdf8;">סוג 5-7 (שלשול)</h4>
                            <p style="font-size:0.9rem; margin:0;">חתיכות רכות, דייסתיות או נוזליות ללא חלקים מוצקים.</p>
                        </div>
                    </div>
                </div>
            </div>`;
        }

        function filterNav() {
            const query = document.getElementById('searchInput').value.toLowerCase();
            const items = document.querySelectorAll('.nav-item');
            items.forEach((item, idx) => {
                if (idx === 0) return;
                const text = item.textContent.toLowerCase();
                item.style.display = text.includes(query) ? 'flex' : 'none';
            });
        }

        document.addEventListener('DOMContentLoaded', initNav);
    </script>
</body>
</html>
"""

    out_file = site_dir / "index.html"
    out_file.write_text(html, encoding="utf-8")
    print(f"SUCCESS! Enhanced website generated. Size: {len(html)}")

if __name__ == "__main__":
    build_enhanced_website()
