/*
 * RB Health clinic price list widget.
 * Prices come from prices.json (built hourly from the Google Sheet "Broadcast" tab).
 *
 * Usage on a page:
 *   <div id="rb-prices" data-name="Hirshmans Chemist"
 *        data-booking="https://www.hirshmanspharmacy.co.uk/book-now.html"
 *        data-campaign="pharmacy"></div>
 *   <script src="https://rishi235.github.io/rbhealth/prices.js" defer></script>
 */
(function () {
    var SCRIPT = document.currentScript;
    var BASE = SCRIPT ? SCRIPT.src.replace(/[^\/]*$/, '') : 'https://rishi235.github.io/rbhealth/';
    var DATA_URL = BASE + 'prices.json';
    var WHATSAPP = '4417521775631';
    var EMAIL = 'helpdesk@rbhealth.co.uk';

    var CSS = '' +
        '.tc-wrap{max-width:980px;margin:0 auto;font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;font-size:16px;color:#1f2937}' +
        '.tc-table{width:100%;border-collapse:collapse;table-layout:fixed}' +
        '.tc-table th,.tc-table td{border:1px solid #e5e7eb;padding:12px 14px;vertical-align:middle;background:#fff;text-align:left}' +
        '.tc-table th{background:#dff1fb;color:#0b3d62;font-weight:700;font-size:1.1em}' +
        '.tc-table col.c1{width:42%}.tc-table col.c2{width:22%}.tc-table col.c3{width:36%}' +
        '.tc-table tr.tc-category-header td{background:#f8fafc;color:#0b3d62;font-weight:700;border-bottom:2px solid #d1d5db}' +
        '.tc-actions{display:flex;gap:8px;flex-wrap:wrap}' +
        '.tc-btn{display:inline-block;line-height:1;padding:7px 10px;border-radius:999px;font-size:13px;font-weight:600;text-decoration:none;border:1px solid transparent;white-space:nowrap}' +
        '.tc-btn:focus{outline:2px solid #111827;outline-offset:1px}.tc-btn:hover{filter:brightness(.95)}' +
        '.tc-btn-book{background:#005EB8;color:#fff!important;border-color:#0053a1}' +
        '.tc-btn-wa{background:#25D366;color:#0b3d1e!important;border-color:#21be5b}' +
        '.tc-btn-email{background:#f3f4f6;color:#111827!important;border-color:#e5e7eb}' +
        '.tc-msg{text-align:center;padding:32px;color:#6b7280;font-style:italic}' +
        '.tc-table caption{caption-side:top;text-align:left;font-weight:700;padding:0 0 8px;color:#0b3d62;font-size:1.1em}' +
        '@media (max-width:640px){.tc-table th,.tc-table td{padding:9px}.tc-table col.c1{width:40%}.tc-table col.c2{width:22%}.tc-table col.c3{width:38%}.tc-actions{gap:5px}.tc-btn{padding:6px 8px;font-size:12px}}';

    function el(tag, cls, text) {
        var e = document.createElement(tag);
        if (cls) e.className = cls;
        if (text != null) e.textContent = text;
        return e;
    }

    function withUtm(url, campaign, content, term) {
        var u = new URL(url, location.href);
        u.searchParams.set('utm_source', 'clinic-prices');
        u.searchParams.set('utm_medium', 'button');
        u.searchParams.set('utm_campaign', campaign);
        u.searchParams.set('utm_content', content);
        u.searchParams.set('utm_term', term);
        return u.toString();
    }

    function message(p, via) {
        return ['I would like to book:', '', 'Service: ' + p.productName, 'Price: ' + p.retail, '',
            'Please contact me to confirm the booking.', '', 'My details:', '- Full Name:',
            '- Phone Number:', '- Email Address:', '', 'Ref: clinic-prices · ' + via].join('\n');
    }

    function link(cls, href, label, aria, newTab) {
        var a = el('a', 'tc-btn ' + cls, label);
        a.href = href;
        a.setAttribute('aria-label', aria);
        if (newTab) { a.target = '_blank'; a.rel = 'noopener noreferrer'; }
        return a;
    }

    function actions(p, cfg) {
        var wrap = el('div', 'tc-actions');
        var book = cfg.booking + (cfg.booking.indexOf('?') < 0 ? '?' : '&') + 'service=' + encodeURIComponent(p.productName);
        wrap.appendChild(link('tc-btn-book', withUtm(book, cfg.campaign, 'book', p.productName), 'Book now', 'Book ' + p.productName, true));
        wrap.appendChild(link('tc-btn-wa', 'https://wa.me/' + WHATSAPP + '?text=' + encodeURIComponent(message(p, 'whatsapp')), 'WhatsApp', 'WhatsApp about ' + p.productName, true));
        wrap.appendChild(link('tc-btn-email', 'mailto:' + EMAIL + '?subject=' + encodeURIComponent('Service Booking Request - ' + p.productName) + '&body=' + encodeURIComponent(message(p, 'email')), 'Email', 'Email about ' + p.productName, cfg.inFrame));
        return wrap;
    }

    function render(box, data, cfg) {
        var table = el('table', 'tc-table');
        table.setAttribute('aria-label', 'Clinic prices');
        table.innerHTML = '<colgroup><col class="c1"><col class="c2"><col class="c3"></colgroup>';
        table.appendChild(el('caption', null, cfg.name ? cfg.name + ' – clinic prices' : 'Clinic prices'));
        var thead = el('thead'), hr = el('tr');
        ['Service', 'Price', 'Book'].forEach(function (h) { var th = el('th', null, h); th.scope = 'col'; hr.appendChild(th); });
        thead.appendChild(hr);
        table.appendChild(thead);

        var tbody = el('tbody'), offers = [];
        Object.keys(data.categorized).forEach(function (cat) {
            var items = data.categorized[cat] || [];
            if (!items.length) return;
            var tr = el('tr', 'tc-category-header'), td = el('td', null, cat);
            td.colSpan = 3;
            tr.appendChild(td);
            tbody.appendChild(tr);
            items.forEach(function (p) {
                var row = el('tr');
                row.appendChild(el('td', null, p.productName));
                row.appendChild(el('td', null, p.retail));
                var a = el('td');
                a.appendChild(actions(p, cfg));
                row.appendChild(a);
                tbody.appendChild(row);
                offers.push({ '@type': 'Offer', name: p.productName, category: cat, price: p.retail.replace(/[^0-9.]/g, ''), priceCurrency: 'GBP' });
            });
        });
        table.appendChild(tbody);
        box.replaceChildren(table);
        box.setAttribute('aria-busy', 'false');

        if (!cfg.inFrame) {
            var s = el('script');
            s.type = 'application/ld+json';
            s.text = JSON.stringify({
                '@context': 'https://schema.org', '@type': ['MedicalBusiness', 'Pharmacy'],
                name: cfg.name || document.title, url: location.origin + '/',
                hasOfferCatalog: { '@type': 'OfferCatalog', name: 'Clinic prices', itemListElement: offers }
            });
            document.head.appendChild(s);
        }
        if (cfg.inFrame && window.parent !== window) {
            window.parent.postMessage({ rbPricesHeight: document.documentElement.scrollHeight }, '*');
        }
    }

    function config(box) {
        var inFrame = window.parent !== window;
        var origin = location.origin;
        if (inFrame && document.referrer) {
            try { origin = new URL(document.referrer).origin; } catch (e) {}
        }
        var d = box.dataset;
        return {
            inFrame: inFrame,
            name: d.name || '',
            campaign: d.campaign || 'pharmacy',
            booking: d.booking || origin + (/tiffenbergs/.test(origin) ? '/book.html' : '/book-now.html')
        };
    }

    function start() {
        var box = document.getElementById('rb-prices') || document.getElementById('tc-prices-container');
        if (!box) return;
        if (!document.getElementById('rb-prices-css')) {
            var st = el('style');
            st.id = 'rb-prices-css';
            st.textContent = CSS;
            document.head.appendChild(st);
        }
        if (!box.parentNode.classList.contains('tc-wrap')) box.classList.add('tc-wrap');
        box.setAttribute('aria-busy', 'true');
        var cfg = config(box);
        if (!box.querySelector('table')) box.innerHTML = '<div class="tc-msg">Loading clinic prices…</div>';
        fetch(DATA_URL, { cache: 'no-cache' })
            .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
            .then(function (data) { render(box, data, cfg); })
            .catch(function () {
                box.setAttribute('aria-busy', 'false');
                if (!box.querySelector('table')) {
                    box.innerHTML = '<div class="tc-msg">Prices are temporarily unavailable – please call or WhatsApp us on 07521 775631.</div>';
                }
            });
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
    else start();
})();
