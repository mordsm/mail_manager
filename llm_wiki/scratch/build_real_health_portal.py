import json
import re
import urllib.parse
from pathlib import Path

def generate_portal():
    root_dir = Path(".")
    book_dir = root_dir / "wiki" / "research" / "books" / "inner_gate"
    site_dir = root_dir / "site" / "inner_gate"
    assets_dir = site_dir / "assets" / "gut_images"

    # Gather all 35 real images copied from Downloads/gut_images
    user_images = []
    if assets_dir.exists():
        for p in sorted(list(assets_dir.glob("*"))):
            if p.is_file() and p.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp', '.svg']:
                fname = p.name
                url_path = f"/assets/gut_images/{urllib.parse.quote(fname)}"
                
                # Deduce topic/chapter from filename
                ch_num = 0
                match = re.search(r"פרק_(\d+)", fname)
                if match:
                    ch_num = int(match.group(1))

                user_images.append({
                    "filename": fname,
                    "url": url_path,
                    "chapter": ch_num
                })

    # Group chapters into 8 Medical Knowledge Domains for a Real Web Portal feel
    domains = [
        {
            "id": "anatomy",
            "icon": "🧬",
            "title": "אנטומיה ומסע המזון בגוף",
            "subtitle": "מפת מערכת העיכול מן הפה, הקיבה, המעי הדק ועד המעי הגס",
            "chapters": [1],
            "tags": ["מערכת העיכול", "פה וושט", "הקיבה", "המעי הדק", "המעי הגס"]
        },
        {
            "id": "microbiome",
            "icon": "🦠",
            "title": "המיקרוביום ומחסום המעי",
            "subtitle": "הקהילה המיקרוביאלית, חומצות שומן קצרות שרשרת, בוטיראט ומזונות מותססים",
            "chapters": [2, 3],
            "tags": ["מיקרוביום", "מחסום המעי", "בוטיראט", "פרה־ביוטיקה", "מזונות מותססים"]
        },
        {
            "id": "nutrition",
            "icon": "🥗",
            "title": "תזונה יומיומית ורכיבים תזונתיים",
            "subtitle": "צלחת מאוזנת, סיבים תזונתיים, קריאת תוויות, Meal Prep ותזמון רכיבים",
            "chapters": [4, 11],
            "tags": ["צלחת מאוזנת", "דגנים וקטניות", "תוויות מזון", "קפאין", "גליקוגן"]
        },
        {
            "id": "symptoms",
            "icon": "🩺",
            "title": "תסמינים עיכוליים, IBS ורגישויות",
            "subtitle": "טיפול בנפיחות, עצירות, שלשול, מעי רגיז (IBS), דיאטת FODMAP, צליאק וצרבת",
            "chapters": [5, 7],
            "tags": ["נפיחות וגזים", "עצירות", "IBS - מעי רגיז", "FODMAP", "צליאק", "צרבת"]
        },
        {
            "id": "gut_brain",
            "icon": "🧠",
            "title": "ציר המעי–מוח, אנרגיה ועייפות",
            "subtitle": "המערכת העצבית, סרוטונין, דופמין, GABA ועייפות כרונית",
            "chapters": [9, 13],
            "tags": ["ציר המעי–מוח", "סרוטונין", "דופמין", "עייפות כרונית", "PEM"]
        },
        {
            "id": "chrono",
            "icon": "⏰",
            "title": "כרונו־תזונה, שינה ולחץ",
            "subtitle": "השעון הצירקדי, אכילה מוגבלת בזמן (16:8 TRE), מלטונין ואיכות השינה",
            "chapters": [10, 12],
            "tags": ["כרונו־תזונה", "השעון הצירקדי", "אכילה מוגבלת בזמן 16:8", "שינה", "לחץ"]
        },
        {
            "id": "diagnosis",
            "icon": "📊",
            "title": "אבחון, בדיקות וניטור אישי",
            "subtitle": "בדיקות דם, צואה, קלפרוטקטין, אנדוסקופיה, יומן מעקב וסולם בריסטול",
            "chapters": [6, 17, 18],
            "tags": ["בדיקות דם", "בדיקות צואה", "קלפרוטקטין", "סולם בריסטול", "יומן 14 ימים"]
        },
        {
            "id": "lifestyle",
            "icon": "💡",
            "title": "שינוי הרגלים וחזון הבריאות",
            "subtitle": "הרגלים אטומיים, Tiny Habits, NLP, תוכנית 7 הימים ופרוטוקול התאוששות",
            "chapters": [8, 14, 15, 16, 19],
            "tags": ["הרגלים אטומיים", "Tiny Habits", "NLP", "תוכנית 7 הימים", "תוחלת בריאות"]
        }
    ]

    # Load chapter Markdown contents
    chapter_dict = {}
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

            # Filter user images matching this chapter
            imgs = [img for img in user_images if img["chapter"] == num]

            chapter_dict[num] = {
                "number": num,
                "title": title,
                "content": content,
                "images": imgs
            }

    domains_json = json.dumps(domains, ensure_ascii=False)
    chapters_json = json.dumps(chapter_dict, ensure_ascii=False)
    images_json = json.dumps(user_images, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>פורטל בריאות המעי, התזונה והמטבוליזם | Gut Health Portal</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            margin: 0;
            padding: 0;
            background: #090d16;
            color: #f8fafc;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }}

        /* REAL WEB PORTAL HEADER */
        .portal-header {{
            background: linear-gradient(180deg, #0f172a 0%, #090d16 100%);
            border-bottom: 1px solid #1e293b;
            padding: 1rem 2rem;
            position: sticky;
            top: 0;
            z-index: 1000;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
        }}

        .header-container {{
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}

        .portal-brand {{
            display: flex;
            align-items: center;
            gap: 14px;
            text-decoration: none;
        }}

        .brand-icon {{
            background: linear-gradient(135deg, #0284c7, #22c55e);
            color: #fff;
            font-size: 1.4rem;
            width: 44px;
            height: 44px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 15px rgba(2, 132, 199, 0.4);
        }}

        .brand-text h1 {{
            margin: 0;
            font-size: 1.25rem;
            color: #38bdf8;
            font-weight: 800;
        }}

        .brand-text p {{
            margin: 2px 0 0 0;
            font-size: 0.8rem;
            color: #94a3b8;
        }}

        .nav-categories {{
            display: flex;
            gap: 8px;
            overflow-x: auto;
            padding: 4px 0;
        }}

        .cat-btn {{
            background: #1e293b;
            color: #cbd5e1;
            border: 1px solid #334155;
            padding: 8px 14px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            white-space: nowrap;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .cat-btn:hover, .cat-btn.active {{
            background: #0284c7;
            color: #fff;
            border-color: #38bdf8;
            box-shadow: 0 0 10px rgba(2, 132, 199, 0.4);
        }}

        .header-actions {{
            display: flex;
            gap: 10px;
        }}

        .action-link {{
            background: rgba(34, 197, 94, 0.15);
            color: #22c55e;
            border: 1px solid rgba(34, 197, 94, 0.4);
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 0.85rem;
            font-weight: 700;
            text-decoration: none;
            transition: all 0.2s;
        }}

        .action-link:hover {{
            background: #22c55e;
            color: #0f172a;
        }}

        /* MAIN HERO & SEARCH PORTAL SECTION */
        .hero-section {{
            background: radial-gradient(circle at top center, #1e293b 0%, #090d16 70%);
            padding: 2.5rem 2rem 2rem 2rem;
            text-align: center;
            border-bottom: 1px solid #1e293b;
        }}

        .hero-title {{
            font-size: 2.2rem;
            font-weight: 900;
            color: #f8fafc;
            margin: 0 0 0.75rem 0;
        }}

        .hero-title span {{
            background: linear-gradient(135deg, #38bdf8, #22c55e);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .hero-subtitle {{
            color: #94a3b8;
            font-size: 1.1rem;
            max-width: 750px;
            margin: 0 auto 1.5rem auto;
        }}

        .search-bar-wrapper {{
            max-width: 650px;
            margin: 0 auto;
            position: relative;
        }}

        .search-bar-input {{
            width: 100%;
            padding: 1rem 1.25rem;
            padding-right: 3rem;
            border-radius: 30px;
            border: 2px solid #334155;
            background: #0f172a;
            color: #fff;
            font-size: 1.05rem;
            outline: none;
            box-shadow: 0 8px 25px rgba(0,0,0,0.4);
            transition: all 0.2s;
        }}

        .search-bar-input:focus {{
            border-color: #38bdf8;
            box-shadow: 0 0 20px rgba(56, 189, 248, 0.4);
        }}

        /* PORTAL MAIN CONTENT LAYOUT */
        .portal-container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
            width: 100%;
            flex: 1;
            display: grid;
            grid-template-columns: 1fr 360px;
            gap: 2rem;
        }}

        /* TOPIC GRID & ARTICLE VIEW */
        .domain-cards-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}

        .domain-card {{
            background: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 14px;
            padding: 1.5rem;
            cursor: pointer;
            transition: all 0.25s ease;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}

        .domain-card:hover {{
            transform: translateY(-4px);
            border-color: #0284c7;
            box-shadow: 0 10px 30px rgba(2, 132, 199, 0.25);
        }}

        .domain-card-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 0.75rem;
        }}

        .domain-card-icon {{
            font-size: 1.6rem;
            background: #1e293b;
            width: 46px;
            height: 46px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .domain-card-title {{
            font-size: 1.15rem;
            font-weight: bold;
            color: #38bdf8;
            margin: 0;
        }}

        .domain-card-desc {{
            color: #94a3b8;
            font-size: 0.92rem;
            line-height: 1.5;
            margin-bottom: 1.25rem;
        }}

        .domain-tags {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }}

        .tag-pill {{
            background: #1e293b;
            color: #22c55e;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 0.78rem;
            font-weight: 600;
        }}

        /* FULL ARTICLE VIEW */
        .article-view {{
            background: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 16px;
            padding: 2.5rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.4);
            display: none;
        }}

        .article-view.active {{
            display: block;
        }}

        .article-header-meta {{
            border-bottom: 2px solid #1e293b;
            padding-bottom: 1rem;
            margin-bottom: 1.5rem;
        }}

        .article-header-meta h2 {{
            color: #38bdf8;
            font-size: 1.8rem;
            margin: 0 0 0.5rem 0;
        }}

        .article-body {{
            line-height: 1.85;
            font-size: 1.05rem;
            color: #e2e8f0;
        }}

        /* REAL USER IMAGE GALLERY CARD */
        .real-image-card {{
            background: #090d16;
            border: 2px solid #0284c7;
            border-radius: 12px;
            padding: 1.25rem;
            margin: 2rem 0;
            box-shadow: 0 8px 25px rgba(0,0,0,0.5);
        }}

        .real-image-title {{
            color: #38bdf8;
            font-weight: bold;
            font-size: 1.1rem;
            margin-bottom: 0.75rem;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .real-image-element {{
            width: 100%;
            max-height: 480px;
            object-fit: contain;
            background: #000;
            border-radius: 8px;
            border: 1px solid #334155;
            cursor: pointer;
            transition: transform 0.2s;
        }}

        .real-image-element:hover {{
            transform: scale(1.01);
            border-color: #38bdf8;
        }}

        /* RIGHT SIDEBAR WIDGETS */
        .right-sidebar {{
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }}

        .widget-box {{
            background: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 14px;
            padding: 1.25rem;
        }}

        .widget-header {{
            color: #38bdf8;
            font-size: 1.05rem;
            font-weight: bold;
            margin-top: 0;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .media-gallery-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 8px;
            max-height: 520px;
            overflow-y: auto;
        }}

        .media-thumb {{
            background: #090d16;
            border: 1px solid #334155;
            border-radius: 8px;
            overflow: hidden;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .media-thumb:hover {{
            border-color: #38bdf8;
            box-shadow: 0 0 10px rgba(56, 189, 248, 0.4);
        }}

        .media-thumb img {{
            width: 100%;
            height: 90px;
            object-fit: cover;
            display: block;
        }}

        .media-thumb-caption {{
            padding: 4px 6px;
            font-size: 0.72rem;
            color: #94a3b8;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        /* MODAL FULLSCREEN */
        .modal-overlay {{
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.9);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 9999;
            padding: 2rem;
        }}

        .modal-overlay.active {{
            display: flex;
        }}

        .modal-img-large {{
            max-width: 90vw;
            max-height: 85vh;
            border-radius: 10px;
            border: 2px solid #38bdf8;
            box-shadow: 0 0 35px rgba(56, 189, 248, 0.6);
        }}
    </style>
</head>
<body>
    <!-- REAL WEB PORTAL HEADER -->
    <header class="portal-header">
        <div class="header-container">
            <a href="#" class="portal-brand" onclick="showDomainCards()">
                <div class="brand-icon">🔬</div>
                <div class="brand-text">
                    <h1>פורטל בריאות המעי והמטבוליזם</h1>
                    <p>Gut Health & Microbiome Knowledge Hub</p>
                </div>
            </a>
            <nav class="nav-categories" id="navCategories">
                <!-- Domain Cat Buttons Load Here -->
            </nav>
            <div class="header-actions">
                <a href="/" class="action-link">🔍 חיפוש היברידי (RAG)</a>
                <a href="/data/books/inner_gate_clean.docx" download class="action-link" style="background:#0284c7; color:#fff; border:none;">📥 DOCX</a>
            </div>
        </div>
    </header>

    <!-- HERO SECTION -->
    <section class="hero-section">
        <h2 class="hero-title">מרכז המידע המדעי והקליני ל<span>בריאות המעיים והאנרגיה</span></h2>
        <p class="hero-subtitle">מאגר ידע נושאי מקיף, תרשימים קליניים, מפת המיקרוביום, תזונה מותססת ופרוטוקולים אבחוניים מלווים ב-35 איורים רפואיים.</p>
        <div class="search-bar-wrapper">
            <input type="text" class="search-bar-input" id="portalSearch" placeholder="🔍 חפש נושא רפואי, תסמין, תרופה או איור (כגון: בוטיראט, FODMAP, צליאק)..." oninput="handleSearch()">
        </div>
    </section>

    <!-- PORTAL MAIN CONTAINER -->
    <main class="portal-container">
        <!-- LEFT: DYNAMIC TOPIC HUBS OR ARTICLE VIEW -->
        <div id="mainContentArea">
            <!-- TOPIC DOMAIN CARDS GRID -->
            <div class="domain-cards-grid" id="domainGrid">
                <!-- Category Domain Cards Load Here -->
            </div>

            <!-- DETAILED ARTICLE WORKSPACE VIEW -->
            <div class="article-view" id="articleView">
                <div class="article-header-meta">
                    <button onclick="showDomainCards()" style="background:#1e293b; color:#38bdf8; border:1px solid #334155; padding:6px 12px; border-radius:6px; cursor:pointer; font-weight:bold; margin-bottom:12px;">← חזרה לכל הנושאים</button>
                    <h2 id="articleTitle">נושא רפואי</h2>
                    <div id="articleMetaTags" class="domain-tags"></div>
                </div>
                <div class="article-body" id="articleBody">
                    <!-- Article HTML & Real Images Render Here -->
                </div>
            </div>
        </div>

        <!-- RIGHT SIDEBAR: REAL USER IMAGES HUB & QUICK ACCESS -->
        <aside class="right-sidebar">
            <div class="widget-box">
                <h3 class="widget-header">🖼️ 35 איורים ותמונות רפואיות מקוריות</h3>
                <p style="font-size:0.82rem; color:#94a3b8; margin-top:-8px; margin-bottom:12px;">לחץ על כל תמונה לצפייה באיכות גבוהה (High-Res):</p>
                <div class="media-gallery-grid" id="mediaGalleryGrid">
                    <!-- 35 Real User Images Thumbnails Load Here -->
                </div>
            </div>

            <div class="widget-box">
                <h3 class="widget-header">🔗 מפת המושגים והעוגנים</h3>
                <div class="domain-tags" id="conceptTagsCloud">
                    <span class="tag-pill" style="cursor:pointer;" onclick="searchTopic('מיקרוביום')">מיקרוביום</span>
                    <span class="tag-pill" style="cursor:pointer;" onclick="searchTopic('בוטיראט')">בוטיראט</span>
                    <span class="tag-pill" style="cursor:pointer;" onclick="searchTopic('FODMAP')">FODMAP</span>
                    <span class="tag-pill" style="cursor:pointer;" onclick="searchTopic('צליאק')">צליאק</span>
                    <span class="tag-pill" style="cursor:pointer;" onclick="searchTopic('כרונו־תזונה')">כרונו־תזונה</span>
                    <span class="tag-pill" style="cursor:pointer;" onclick="searchTopic('ציר המעי–מוח')">ציר המעי–מוח</span>
                    <span class="tag-pill" style="cursor:pointer;" onclick="searchTopic('סולם בריסטול')">סולם בריסטול</span>
                    <span class="tag-pill" style="cursor:pointer;" onclick="searchTopic('סרוטונין')">סרוטונין</span>
                </div>
            </div>
        </aside>
    </main>

    <!-- FULLSCREEN MODAL VIEWER -->
    <div class="modal-overlay" id="imageModal" onclick="closeModal()">
        <img src="" id="modalImgTag" class="modal-img-large" alt="Enlarged Medical Diagram">
    </div>

    <script>
        const domainsData = {domains_json};
        const chaptersData = {chapters_json};
        const imagesData = {images_json};

        function initPortal() {{
            renderCategoryNav();
            renderDomainCards();
            renderMediaGallery();
        }}

        function renderCategoryNav() {{
            const container = document.getElementById('navCategories');
            let html = `<button class="cat-btn active" onclick="showDomainCards()">🌐 כל הנושאים</button>`;
            domainsData.forEach(d => {{
                html += `<button class="cat-btn" onclick="openDomain('${{d.id}}')">${{d.icon}} ${{d.title}}</button>`;
            }});
            container.innerHTML = html;
        }}

        function renderDomainCards() {{
            const grid = document.getElementById('domainGrid');
            let html = '';
            domainsData.forEach(d => {{
                let tagsHtml = d.tags.map(t => `<span class="tag-pill">${{t}}</span>`).join(' ');
                html += `
                <div class="domain-card" onclick="openDomain('${{d.id}}')">
                    <div>
                        <div class="domain-card-header">
                            <div class="domain-card-icon">${{d.icon}}</div>
                            <h3 class="domain-card-title">${{d.title}}</h3>
                        </div>
                        <p class="domain-card-desc">${{d.subtitle}}</p>
                    </div>
                    <div class="domain-tags">${{tagsHtml}}</div>
                </div>`;
            }});
            grid.innerHTML = html;
        }}

        function renderMediaGallery() {{
            const grid = document.getElementById('mediaGalleryGrid');
            let html = '';
            imagesData.forEach(img => {{
                html += `
                <div class="media-thumb" onclick="openModal('${{img.url}}')">
                    <img src="${{img.url}}" alt="${{img.filename}}" loading="lazy">
                    <div class="media-thumb-caption">${{img.filename}}</div>
                </div>`;
            }});
            grid.innerHTML = html;
        }}

        function openDomain(domainId) {{
            const domain = domainsData.find(d => d.id === domainId);
            if (!domain) return;

            document.getElementById('domainGrid').style.display = 'none';
            const articleView = document.getElementById('articleView');
            articleView.classList.add('active');

            document.getElementById('articleTitle').textContent = domain.icon + ' ' + domain.title;
            document.getElementById('articleMetaTags').innerHTML = domain.tags.map(t => `<span class="tag-pill">${{t}}</span>`).join(' ');

            let html = `<p class="hero-subtitle" style="text-align:right; margin:0 0 2rem 0;">${{domain.subtitle}}</p>`;

            // Combine chapter contents and attach real images
            domain.chapters.forEach(chNum => {{
                const ch = chaptersData[chNum];
                if (ch) {{
                    html += `<div style="background:#090d16; border:1px solid #1e293b; padding:1.5rem; border-radius:12px; margin-bottom:2rem;">`;
                    html += renderMarkdown(ch.content);

                    // Attach user's real images for this chapter
                    if (ch.images && ch.images.length > 0) {{
                        ch.images.forEach(img => {{
                            html += `
                            <div class="real-image-card">
                                <div class="real-image-title">📷 איור רפואי מקורי מקושר: ${{escapeHtml(img.filename)}}</div>
                                <img src="${{img.url}}" class="real-image-element" alt="${{img.filename}}" onclick="openModal('${{img.url}}')">
                            </div>`;
                        }});
                    }}

                    html += `</div>`;
                }}
            }});

            document.getElementById('articleBody').innerHTML = html;
            window.scrollTo({{ top: 300, behavior: 'smooth' }});
        }}

        function escapeHtml(str) {{
            return str.replace(/</g, "&lt;").replace(/>/g, "&gt;");
        }}

        function showDomainCards() {{
            document.getElementById('domainGrid').style.display = 'grid';
            document.getElementById('articleView').classList.remove('active');
        }}

        function renderMarkdown(md) {{
            if (!md) return '';
            let lines = md.split('\\n');
            let out = [];

            lines.forEach(line => {{
                let l = line.trim();
                if (!l) return;
                if (l.startswith('# ')) out.push('<h2 style="color:#38bdf8;">' + l.substring(2) + '</h2>');
                else if (l.startswith('## ')) out.push('<h3 style="color:#7dd3fc;">' + l.substring(3) + '</h3>');
                else if (l.startswith('### ')) out.push('<h4 style="color:#a7f3d0;">' + l.substring(4) + '</h4>');
                else out.push('<p>' + l.replace(/\\^([a-zA-Z0-9_\\-]+)/g, '<span style="color:#64748b; background:#1e293b; padding:2px 6px; border-radius:4px; font-family:monospace; font-size:0.75rem;">^$1</span>') + '</p>');
            }});

            return out.join('\\n');
        }}

        function handleSearch() {{
            const query = document.getElementById('portalSearch').value.toLowerCase();
            if (!query) {{
                showDomainCards();
                return;
            }}

            const matched = domainsData.filter(d => 
                d.title.toLowerCase().includes(query) || 
                d.subtitle.toLowerCase().includes(query) || 
                d.tags.some(t => t.toLowerCase().includes(query))
            );

            const grid = document.getElementById('domainGrid');
            showDomainCards();
            
            let html = '';
            matched.forEach(d => {{
                let tagsHtml = d.tags.map(t => `<span class="tag-pill">${{t}}</span>`).join(' ');
                html += `
                <div class="domain-card" onclick="openDomain('${{d.id}}')">
                    <div>
                        <div class="domain-card-header">
                            <div class="domain-card-icon">${{d.icon}}</div>
                            <h3 class="domain-card-title">${{d.title}}</h3>
                        </div>
                        <p class="domain-card-desc">${{d.subtitle}}</p>
                    </div>
                    <div class="domain-tags">${{tagsHtml}}</div>
                </div>`;
            }});

            if (!matched.length) {{
                html = `<div style="grid-column: 1/-1; text-align:center; padding:3rem; color:#94a3b8;">לא נמצאו נושאים המתאימים לחיפוש "${{query}}". נסה לחפש בחיפוש ההיברידי ב-RAG.</div>`;
            }}

            grid.innerHTML = html;
        }}

        function searchTopic(topic) {{
            document.getElementById('portalSearch').value = topic;
            handleSearch();
        }}

        function openModal(imgUrl) {{
            document.getElementById('modalImgTag').src = imgUrl;
            document.getElementById('imageModal').classList.add('active');
        }}

        function closeModal() {{
            document.getElementById('imageModal').classList.remove('active');
        }}

        document.addEventListener('DOMContentLoaded', initPortal);
    </script>
</body>
</html>"""

    output_file = site_dir / "index.html"
    output_file.write_text(html_content, encoding="utf-8")
    print(f"SUCCESS! Built Real Health Portal at {output_file}. File size: {len(html_content)}")

if __name__ == "__main__":
    generate_portal()
