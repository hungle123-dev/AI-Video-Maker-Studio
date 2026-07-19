#!/usr/bin/env node

/**

 * TubeCraft — Canvas Frame Renderer

 * Auto-layout + Geometry Zone + Dynamic Box

 */

global.window = global;

// Public easing helper for AI-authored custom_js. The script prompt documents
// EZ(), so an illustration must not vanish just because the generated block
// uses it without redeclaring it.
global.EZ = function (t) {
    t = Math.max(0, Math.min(1, t));
    return 1 - Math.pow(1 - t, 3);
};

const fs = require('fs');

const path = require('path');

function parseArgs(argv) {

    const r = {};

    for (let i = 0; i < argv.length; i++) {

        if (argv[i].startsWith('--')) {

            const key = argv[i].slice(2);

            const val = argv[i + 1];

            if (val !== undefined && !val.startsWith('--')) {

                r[key] = val;

                i++;

            } else {

                r[key] = true;

            }

        }

    }

    return r;

}

const args = parseArgs(process.argv.slice(2));

const scriptPath = args.script, timingPath = args.timing, outputDir = args.output;

const themeName = args.theme || 'dark', FPS = parseInt(args.fps || '30');

// ── Tuỳ biến NỀN, độc lập với phong cách ────────────────────────────
//   --bg-color "#111"           nền trơn một màu
//   --bg-grad  "#0a0a1a,#1a1030" nền gradient 2 màu (ưu tiên hơn bg-color)
//   --bg-fx    off | auto        auto = giữ hiệu ứng nền của phong cách
//                                off  = nền phẳng, bỏ lưới/sao/quả cầu
// LƯU Ý: phải áp SAU khối STYLE_PALETTES (dòng ~304) vì phong cách ghi đè
// T.bgGrad — trước đây bg-color đặt trước nên bị nuốt, không bao giờ có tác dụng.
// Ưu tiên CLI arg, fallback env TUBECRAFT_* (video_encoder set env cho
// worker song song — giống cách làm của title-color/text-color/font).
const customBgColor = args['bg-color'] || '';
const customBgGrad = (args['bg-grad'] || process.env.TUBECRAFT_BG_GRAD || '')
    .split(',').map(function (s) { return s.trim(); }).filter(Boolean);
const bgFx = (args['bg-fx'] || process.env.TUBECRAFT_BG_FX || 'auto').toLowerCase();
global.bgFxOff = (bgFx === 'off' || bgFx === 'none');

if (!scriptPath || !timingPath || !outputDir) {

    console.log(JSON.stringify({status:'error',message:'--script, --timing, --output required'}));

    process.exit(1);

}

const script = JSON.parse(fs.readFileSync(scriptPath, 'utf-8'));

const timing = JSON.parse(fs.readFileSync(timingPath, 'utf-8'));

fs.mkdirSync(outputDir, { recursive: true });

const aspect_ratio = args.aspect || '9:16';

const W = aspect_ratio === '16:9' ? 1920 : (aspect_ratio === '1:1' ? 1080 : 1080);

const H = aspect_ratio === '16:9' ? 1080 : (aspect_ratio === '1:1' ? 1080 : 1920);

const MX = 60; // horizontal margin

// NOTE: 'sans-serif' MUST come before "Segoe UI" — the fontconfig alias prefers
// "Be Vietnam Pro"; direct family lookup can fail under pango-win32, so the alias
// is the reliable path to BVP. Putting Segoe first would silently win the fallback.
// Font phải liệt kê TƯỜNG MINH cho từng hệ chữ: fontconfig không tự nhảy sang
// font CJK/Devanagari nếu family không có trong stack → chữ Nhật/Hàn/Trung/Hindi
// ra ô vuông mã codepoint (tofu). Thứ tự: Latin+Việt trước, rồi các hệ chữ khác.
const SYSTEM_FONT_STACK = '"Be Vietnam Pro", sans-serif, ' +
    '"Yu Gothic UI", "Meiryo", "MS Gothic", ' +      // 日本語
    '"Malgun Gothic", ' +                            // 한국어
    '"Microsoft YaHei", "SimSun", ' +                // 中文
    '"Nirmala UI", ' +                               // हिन्दी + Ấn Độ
    '"Leelawadee UI", ' +                            // ไทย
    '"Segoe UI", ' +                                 // Cyrillic/Ả Rập/Hy Lạp
    '"Segoe UI Emoji", "Noto Color Emoji", "Segoe UI Symbol"';

// Every renderer-owned text path needs a font with Vietnamese glyphs.  A
// user/style font stays first (so the requested visual style is preserved),
// but it must never be the only family in the stack: many Windows/Pango
// combinations report an installed family while still rendering Vietnamese
// diacritics as question marks.
function withVietnameseFallback(fontValue) {
    const font = String(fontValue || '').trim();
    if (!font) return SYSTEM_FONT_STACK;
    if (font.toLowerCase().includes('be vietnam pro')) return font;
    return font + ', "Be Vietnam Pro", sans-serif';
}

const THEMES = {

    dark: {

        bgGrad: ['#0a0a1a', '#1a1030'],

        cardBg: 'rgba(255,255,255,0.06)', cardBorder: 'rgba(255,255,255,0.12)',

        titleColor: '#FFD700', textColor: '#F0F0F0', mutedColor: '#888',

        hlColor: '#FFD700', hlBg: 'rgba(255,215,0,0.15)',

        resultBg: 'rgba(0,255,136,0.1)', resultBorder: '#00FF88',

        eqBg: 'rgba(124,58,237,0.12)', eqBorder: 'rgba(167,139,250,0.4)',

        tipBg: 'rgba(251,191,36,0.1)', tipBorder: 'rgba(251,191,36,0.4)',

        progressBg: 'rgba(255,255,255,0.08)', progressFill: '#FFD700',

        geoBg: 'rgba(255,255,255,0.03)', geoBorder: 'rgba(255,255,255,0.1)',

        font: SYSTEM_FONT_STACK,

    },

    whiteboard: {

        bgGrad: ['#F5F0E8', '#E8E0D0'],

        cardBg: 'rgba(0,0,0,0.03)', cardBorder: 'rgba(0,0,0,0.1)',

        titleColor: '#1a1a1a', textColor: '#333', mutedColor: '#888',

        hlColor: '#E53E3E', hlBg: 'rgba(229,62,62,0.1)',

        resultBg: 'rgba(56,161,105,0.1)', resultBorder: '#38A169',

        eqBg: 'rgba(49,130,206,0.08)', eqBorder: 'rgba(49,130,206,0.3)',

        tipBg: 'rgba(237,137,54,0.1)', tipBorder: 'rgba(237,137,54,0.4)',

        progressBg: 'rgba(0,0,0,0.06)', progressFill: '#3182CE',

        geoBg: 'rgba(0,0,0,0.02)', geoBorder: 'rgba(0,0,0,0.08)',

        font: SYSTEM_FONT_STACK,

    },

    chalkboard: {

        bgGrad: ['#1a3528', '#2D4A3E'],

        cardBg: 'rgba(255,255,255,0.04)', cardBorder: 'rgba(255,255,255,0.1)',

        titleColor: '#FFFFFF', textColor: '#E0E0D0', mutedColor: '#8A8A7A',

        hlColor: '#FFE066', hlBg: 'rgba(255,224,102,0.12)',

        resultBg: 'rgba(255,224,102,0.1)', resultBorder: '#FFE066',

        eqBg: 'rgba(255,255,255,0.05)', eqBorder: 'rgba(255,255,255,0.15)',

        tipBg: 'rgba(144,238,144,0.1)', tipBorder: 'rgba(144,238,144,0.3)',

        progressBg: 'rgba(255,255,255,0.06)', progressFill: '#FFE066',

        geoBg: 'rgba(255,255,255,0.03)', geoBorder: 'rgba(255,255,255,0.08)',

        font: SYSTEM_FONT_STACK,

    },

};

let T = THEMES[themeName] || THEMES.dark;

// (nền tuỳ biến áp ở CUỐI, sau khi phong cách ghi đè bgGrad)

// ── Overwrite Theme & Font Family by Selected Art Style ────────────────

const artStyle = args.style || 'default';

global.artStyle = artStyle;

const STYLE_PALETTES = {

    cyberpunk: {

        bgGrad: ['#070714', '#0d0d29'],

        font: "'Orbitron', sans-serif",

        titleColor: '#00ffff', textColor: '#f0f0f5', hlColor: '#ff007f', mutedColor: '#7a7a9a',

        greenColor: '#39ff14', redColor: '#ff073a', yellowColor: '#efff14', whiteColor: '#ffffff', cyanColor: '#00ffff',

    },

    watercolor: {

        bgGrad: ['#fcf8f2', '#f5eedc'],

        font: "'EB Garamond', serif",

        titleColor: '#2c4c38', textColor: '#3a3532', hlColor: '#c85a53', mutedColor: '#8e8680',

        greenColor: '#6b8e23', redColor: '#b22222', yellowColor: '#daa520', whiteColor: '#fdfbf7', cyanColor: '#4682b4',

    },

    inkwash: {

        bgGrad: ['#efe9db', '#e4dcce'],

        font: "'YouthTouch', cursive, serif",

        titleColor: '#0e1111', textColor: '#2f3e46', hlColor: '#621708', mutedColor: '#6c757d',

        greenColor: '#2d4a22', redColor: '#800808', yellowColor: '#9b7a36', whiteColor: '#f5f2eb', cyanColor: '#4a5759',

    },

    pastel: {

        bgGrad: ['#fff5f5', '#f0e6ff'],

        font: "'Outfit', sans-serif",

        titleColor: '#4a4e69', textColor: '#5c677d', hlColor: '#ffb5a7', mutedColor: '#9a8c98',

        greenColor: '#b5e2fa', redColor: '#ffcad4', yellowColor: '#ffe5ec', whiteColor: '#ffffff', cyanColor: '#b5f2ea',

    },

    // aurora — TÔNG SÁNG premium (mesh pastel + bokeh), mực TỐI tương phản cao.
    // Khác pastel: accent đậm rõ (đọc được trên nền sáng), whiteColor = mực tối
    // để rc('white') trong mọi cảnh tự thành chữ tối. Proxy light-style lo phần
    // còn lại (hạ card tối thành kính trắng, đổi màu chuỗi sáng thành tối).
    aurora: {

        bgGrad: ['#fdfdff', '#edf0fb'],

        font: "'Outfit', sans-serif",

        // LƯU Ý: mực KHÔNG được trùng các hex slate trong isDarkColor
        // (#0f172a, #1a1a2e...) — chúng bị remap thành kính trắng (dành cho
        // CARD bg của cảnh tối). Dùng navy khác: #152238 / #223154.
        titleColor: '#152238', textColor: '#223154', hlColor: '#1d4ed8', mutedColor: '#57627a',

        greenColor: '#15803d', redColor: '#dc2626', yellowColor: '#b45309', whiteColor: '#152238', cyanColor: '#0e7490',

    },

    // Math Noir: đen tuyền + nét trắng mảnh kiểu manim/3Blue1Brown — toán
    // học tối giản, hình tự vẽ nét (template math_noir, cảnh mn_*).
    mathnoir: {

        bgGrad: ['#060607', '#0b0b0d'],

        font: "'Segoe UI', sans-serif",

        titleColor: '#e8e8ea', textColor: '#c9c9ce', hlColor: '#facc15', mutedColor: '#8b8b92',

        greenColor: '#4ade80', redColor: '#f87171', yellowColor: '#facc15', whiteColor: '#e8e8ea', cyanColor: '#60a5fa',

    },

    // Giấy ấm bình luận: nền kem ấm + lưới nhạt + glow cam nhẹ — bình luận
    // công nghệ kiểu poster giấy (template paper_explainer). Cảnh wp_* tự
    // quản màu — KHÔNG đưa vào isLightStyle (proxy remap sẽ phá card trắng).
    warmpaper: {

        bgGrad: ['#fdf8f0', '#f6e9d5'],

        font: "'Segoe UI', sans-serif",

        titleColor: '#211a12', textColor: '#3d362c', hlColor: '#e8590c', mutedColor: '#a4917a',

        greenColor: '#2f9e44', redColor: '#d9480f', yellowColor: '#e8590c', whiteColor: '#211a12', cyanColor: '#1c7ed6',

    },

    // Mổ xẻ công nghệ: than chì + lưới chéo mờ + vignette — chuyên đề
    // giải thích kỹ thuật kiểu editorial (template tech_explainer).
    techdark: {

        bgGrad: ['#0a0d10', '#12171c'],

        font: "'Segoe UI', sans-serif",

        titleColor: '#f5f7f9', textColor: '#e7ebef', hlColor: '#fbbf24', mutedColor: '#9aa3ad',

        greenColor: '#34d399', redColor: '#f87171', yellowColor: '#fbbf24', whiteColor: '#f5f7f9', cyanColor: '#22d3ee',

    },

    // Phác thảo neon: nền đen ánh rêu + lưới blueprint, nhân vật que neon vẽ
    // tay, panel terminal viền mảnh + label mono in hoa. (template neon_sketch)
    neonsketch: {

        bgGrad: ['#060a04', '#0c1207'],

        font: "'Arial Black', 'Segoe UI', sans-serif",

        titleColor: '#f2f7ec', textColor: '#dbe5d0', hlColor: '#fde047', mutedColor: '#93a58a',

        greenColor: '#a3e635', redColor: '#f87171', yellowColor: '#fde047', whiteColor: '#f2f7ec', cyanColor: '#38bdf8',

    },

    pixel: {

        bgGrad: ['#05010f', '#1a0820'],

        font: "Orbitron, 'JetBrains Mono', sans-serif",

        titleColor: '#00ffff', textColor: '#e0f7ff', hlColor: '#ff00aa', mutedColor: '#7a5a9a',

        greenColor: '#00ff00', redColor: '#ff0000', yellowColor: '#ffff00', whiteColor: '#ffffff', cyanColor: '#00ffff',

    },

    sketch: {

        bgGrad: ['#ffffff', '#f0f0f0'],

        font: "Pangolin",

        titleColor: '#000000', textColor: '#1c1c1c', hlColor: '#4b5563', mutedColor: '#9ca3af',

        greenColor: '#374151', redColor: '#111827', yellowColor: '#4b5563', whiteColor: '#ffffff', cyanColor: '#1f2937',

    },

    sketchnote: {

        bgGrad: ['#fcfbfa', '#f7f5f0'],

        font: "Pangolin",

        titleColor: '#1e3a8a', textColor: '#1e293b', hlColor: '#ea580c', mutedColor: '#64748b',

        greenColor: '#16a34a', redColor: '#dc2626', yellowColor: '#f59e0b', whiteColor: '#fcfbfa', cyanColor: '#2563eb',

    },

    cartoon: {

        bgGrad: ['#ffdf00', '#ff4b5c'],

        font: "'Fredoka', sans-serif",

        titleColor: '#000000', textColor: '#ffffff', hlColor: '#00d2fc', mutedColor: '#1d2d50',

        greenColor: '#00e676', redColor: '#ff1744', yellowColor: '#ffea00', whiteColor: '#ffffff', cyanColor: '#00e5ff',

    },

    liquidglass: {

        bgGrad: ['#05070d', '#0d1424'],

        font: SYSTEM_FONT_STACK,

        titleColor: '#ffffff', textColor: '#e8edf5', hlColor: '#ff5a47', mutedColor: '#8a94a8',

        greenColor: '#34d399', redColor: '#ff5a47', yellowColor: '#fbbf24', whiteColor: '#ffffff', cyanColor: '#60d4ff',

        glass: {

            cardBg: 'rgba(255,255,255,0.055)', cardBorder: 'rgba(255,255,255,0.22)',

            hlBg: 'rgba(255,90,71,0.14)',

            resultBg: 'rgba(255,255,255,0.06)', resultBorder: 'rgba(255,255,255,0.28)',

            eqBg: 'rgba(96,212,255,0.10)', eqBorder: 'rgba(96,212,255,0.32)',

            tipBg: 'rgba(52,211,153,0.10)', tipBorder: 'rgba(52,211,153,0.32)',

            progressBg: 'rgba(255,255,255,0.08)', progressFill: '#ff5a47',

            geoBg: 'rgba(255,255,255,0.04)', geoBorder: 'rgba(255,255,255,0.14)',

        },

    }

};

if (artStyle !== 'default' && STYLE_PALETTES[artStyle]) {

    const pal = STYLE_PALETTES[artStyle];

    T = Object.assign({}, T, {

        bgGrad: pal.bgGrad,

        font: pal.font,

        titleColor: pal.titleColor,

        textColor: pal.textColor,

        hlColor: pal.hlColor,

        mutedColor: pal.mutedColor

    });

    // Apply accent colors (used by rc()) when the palette defines them

    ['greenColor','redColor','yellowColor','whiteColor','cyanColor'].forEach(function(k){

        if (pal[k]) T[k] = pal[k];

    });

    // Glassmorphism: override card/box surfaces and enable frosted rendering

    if (pal.glass) {

        T = Object.assign({}, T, pal.glass);

        T.glassEffect = true;

    }

}

// ── User overrides: màu tiêu đề / font / màu chữ (thắng cả theme lẫn style) ──
// Ưu tiên CLI arg, fallback biến môi trường do video_encoder set.
const _ovTitle = args['title-color'] || process.env.TUBECRAFT_TITLE_COLOR || '';
const _ovText  = args['text-color']  || process.env.TUBECRAFT_TEXT_COLOR  || '';
const _ovFont  = args['font']        || process.env.TUBECRAFT_FONT        || '';
if (_ovTitle && String(_ovTitle).trim()) {
    T = Object.assign({}, T, { titleColor: _ovTitle, hlColor: _ovTitle });
}
if (_ovText && String(_ovText).trim()) {
    T = Object.assign({}, T, { textColor: _ovText });
}
if (_ovFont && String(_ovFont).trim()) {
    T = Object.assign({}, T, { font: _ovFont });
}
T.font = withVietnameseFallback(T.font);

// ── PHỤ ĐỀ (subtitle) ─────────────────────────────────────────────────
//   --subtitle '{"enabled":true,"preset":"capcut_bold","fontScale":1.0,
//                "yPct":null,"maxLines":null}'      (null = theo preset)
// Fallback env TUBECRAFT_SUBTITLE: set một lần để mọi worker chunk đều nhận.
// Không có / enabled=false → KHÔNG vẽ gì (đúng hành vi cũ).
const _subRaw = (typeof args['subtitle'] === 'string' ? args['subtitle'] : '') ||
    process.env.TUBECRAFT_SUBTITLE || '';
let SUB_CFG = null;
if (_subRaw && String(_subRaw).trim()) {
    try {
        const c = JSON.parse(String(_subRaw));
        if (c && c.enabled) SUB_CFG = c;
    } catch (e) {
        process.stderr.write(`[Subtitle] --subtitle không phải JSON hợp lệ: ${e.message}\n`);
    }
}

// ── Ghi đè NỀN (sau phong cách → thắng bgGrad của phong cách) ──────────
if (customBgGrad.length >= 2) {
    T = Object.assign({}, T, { bgGrad: [customBgGrad[0], customBgGrad[1]] });
} else if (customBgGrad.length === 1) {
    T = Object.assign({}, T, { bgGrad: [customBgGrad[0], customBgGrad[0]] });
} else if (customBgColor && String(customBgColor).trim()) {
    T = Object.assign({}, T, { bgGrad: [customBgColor, customBgColor] });
}

global.glassEffect = !!T.glassEffect;

let createCanvas, loadImage, registerFont;

// ── Fix: enable custom & system fonts under node-canvas/Pango on Windows ──
// Pango on Windows defaults to the win32 backend which IGNORES registerFont(),
// causing "couldn't load font ... falling back to Sans" and breaking Vietnamese
// diacritics. Force the fontconfig backend and provide a config pointing at our
// bundled fonts + the Windows system fonts so every family resolves correctly.
(function setupFontconfig() {
    try {
        if (process.platform !== 'win32') return;
        const os = require('os');
        const staticAbs = path.resolve(path.join(__dirname, '..', 'static')).replace(/\\/g, '/');
        const userFontDir = String(process.env.TUBECRAFT_FONTS_DIR || '').trim()
            .replace(/\\/g, '/');
        const winFonts = (process.env.WINDIR ? process.env.WINDIR.replace(/\\/g, '/') : 'C:/Windows') + '/Fonts';
        const cacheDir = path.join(os.tmpdir(), 'edu_fontconfig_cache');
        try { fs.mkdirSync(cacheDir, { recursive: true }); } catch (e) {}
        const cacheAbs = cacheDir.replace(/\\/g, '/');
        const confXml = '<?xml version="1.0"?>\n' +
            '<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n' +
            '<fontconfig>\n' +
            '  <dir>' + staticAbs + '</dir>\n' +
            (userFontDir ? '  <dir>' + userFontDir.replace(/&/g, '&amp;') + '</dir>\n' : '') +
            '  <dir>' + winFonts + '</dir>\n' +
            '  <cachedir>' + cacheAbs + '</cachedir>\n' +
            '  <alias><family>sans-serif</family><prefer><family>Be Vietnam Pro</family><family>Arial</family><family>Segoe UI</family><family>Tahoma</family></prefer></alias>\n' +
            '  <alias><family>serif</family><prefer><family>Times New Roman</family><family>Georgia</family></prefer></alias>\n' +
            '  <alias><family>monospace</family><prefer><family>Consolas</family><family>Courier New</family></prefer></alias>\n' +
            '</fontconfig>\n';
        const confPath = path.join(cacheDir, 'fonts.conf');
        fs.writeFileSync(confPath, confXml, 'utf8');
        process.env.PANGOCAIRO_BACKEND = 'fc';
        process.env.FONTCONFIG_FILE = confPath;
        process.env.FONTCONFIG_PATH = cacheDir;
    } catch (e) {
        process.stderr.write('[Renderer] Fontconfig setup skipped: ' + e.message + '\n');
    }
})();

try { ({ createCanvas, loadImage, registerFont } = require('canvas')); } catch(e) {

    try { ({ createCanvas, loadImage, registerFont } = require(path.join(process.env.NODE_PATH||'','canvas'))); } catch(e2) {

        console.log(JSON.stringify({status:'error',message:'canvas not installed'}));

        process.exit(1);

    }

}

// ── Register Youth Touch demo font for Ink Wash Calligraphy style ───

if (registerFont) {

    // Fonts ship alongside the renderer in engines/web in both source and
    // the portable bundle.  The old ../static path silently fell back to a
    // system font, changing line metrics and causing layout drift.
    const fontPath = path.join(__dirname, 'web', 'YouthTouch.ttf');

    if (fs.existsSync(fontPath)) {

        registerFont(fontPath, { family: 'YouthTouch' });

        process.stderr.write(`[Renderer] Registered font family: YouthTouch\n`);

    } else {

        process.stderr.write(`[Renderer] Font file not found at: ${fontPath}\n`);

    }

    // Register Be Vietnam Pro — primary UI font (full Vietnamese diacritics).
    // These files deliberately live in static/, not engines/web/.  The old
    // path was wrong, which made the renderer silently use a font without
    // Vietnamese glyphs and turn diacritics into '?'.
    const bvpWeights = [["Regular", "normal"], ["SemiBold", "600"], ["Bold", "bold"]];
    for (const [w, weight] of bvpWeights) {
        const bvpPath = path.join(__dirname, '..', 'static', `BeVietnamPro-${w}.ttf`);
        if (fs.existsSync(bvpPath)) {
            registerFont(bvpPath, { family: 'Be Vietnam Pro', weight });
        } else {
            process.stderr.write(`[Renderer] Missing bundled Vietnamese font: ${bvpPath}\n`);
        }
    }

    // Register Pangolin handwriting font for Sketchnote style

    const pangolinPath = path.join(__dirname, 'web', 'Pangolin-Regular.ttf');

    if (fs.existsSync(pangolinPath)) {

        registerFont(pangolinPath, { family: 'Pangolin', weight: 'normal' });

        registerFont(pangolinPath, { family: 'Pangolin', weight: 'bold' });

        process.stderr.write(`[Renderer] Registered font family: Pangolin\n`);

    }

    // Font người dùng thêm (data/fonts.json) — do core/fonts.py ghi.  The
    // manifest is explicitly passed by Python so TUBECRAFT_DATA_DIR continues
    // to work after moving the portable app.  Only relative files below its
    // own data/fonts directory are accepted; a modified manifest cannot make
    // the renderer parse an arbitrary absolute system file.
    try {
        const manifest = process.env.TUBECRAFT_FONTS_MANIFEST ||
            path.join(__dirname, '..', 'data', 'fonts.json');
        if (fs.existsSync(manifest)) {
            const list = JSON.parse(fs.readFileSync(manifest, 'utf8'));
            const manifestDir = path.dirname(path.resolve(manifest));
            const allowedRoot = path.resolve(manifestDir, 'fonts');
            for (const it of (Array.isArray(list) ? list : [])) {
                if (!it || typeof it.file !== 'string' || !it.family || path.isAbsolute(it.file)) {
                    continue;
                }
                const file = path.resolve(manifestDir, it.file);
                if (!(file === allowedRoot || file.startsWith(allowedRoot + path.sep)) || !fs.existsSync(file)) {
                    continue;
                }
                if (it && it.family) {
                    try {
                        registerFont(file, { family: it.family });
                        process.stderr.write(`[Renderer] Registered user font: ${it.family}\n`);
                    } catch (e) {
                        process.stderr.write(`[Renderer] Font register failed ${it.family}: ${e.message}\n`);
                    }
                }
            }
        }
    } catch (e) {
        process.stderr.write(`[Renderer] User fonts skipped: ${e.message}\n`);
    }

}

const canvas = createCanvas(W, H), ctx = canvas.getContext('2d');

// ── Twemoji Full Color Emoji Preloader & Cache ─────────────────────

const emojiCacheDir = path.join(__dirname, '..', 'static', 'emoji_cache');

const emojiImageCache = {};

function getEmojiCodePoint(emoji) {

    const codePoints = [];

    for (let i = 0; i < emoji.length; i++) {

        const code = emoji.charCodeAt(i);

        if (code >= 0xd800 && code <= 0xdbff && i + 1 < emoji.length) {

            const next = emoji.charCodeAt(i + 1);

            if (next >= 0xdc00 && next <= 0xdfff) {

                codePoints.push(((code - 0xd800) << 10) + (next - 0xdc00) + 0x10000);

                i++;

                continue;

            }

        }

        codePoints.push(code);

    }

    return codePoints.filter(x => x !== 0xfe0f).map(x => x.toString(16)).join('-');

}

async function loadEmojiImage(emoji) {

    const cp = getEmojiCodePoint(emoji);

    if (emojiImageCache[cp]) return emojiImageCache[cp];

    const localPath = path.join(emojiCacheDir, `${cp}.png`);

    if (fs.existsSync(localPath)) {

        try {

            const img = await loadImage(localPath);

            emojiImageCache[cp] = img;

            return img;

        } catch (e) {

            process.stderr.write(`[Emoji] Error loading cached emoji ${cp}: ${e.message}\n`);

        }

    }

    // Fully local renderer: use a bundled cache when present and otherwise
    // let drawEmoji() use the platform font.  No preview/render may download
    // or write assets into the application directory.
    return null;

}

function extractEmojis(obj, set = new Set()) {

    if (typeof obj === 'string') {

        const regex = /[\uD800-\uDBFF][\uDC00-\uDFFF]|[\u2600-\u27BF]|[\u2300-\u23FF]/g;

        let match;

        while ((match = regex.exec(obj)) !== null) {

            set.add(match[0]);

        }

    } else if (Array.isArray(obj)) {

        for (const item of obj) extractEmojis(item, set);

    } else if (obj && typeof obj === 'object') {

        for (const k in obj) extractEmojis(obj[k], set);

    }

    return set;

}

async function preloadEmojis(script) {

    const emojis = extractEmojis(script);

    process.stderr.write(`[Emoji] Found ${emojis.size} unique emojis in script. Preloading...\n`);

    for (const em of emojis) {

        const img = await loadEmojiImage(em);

        if (img) {

            process.stderr.write(`[Emoji] Preloaded: ${em}\n`);

        } else {

            process.stderr.write(`[Emoji] Failed to load: ${em}\n`);

        }

    }

}

// ── drawEmoji global helper ─────────────────────────────

global.drawEmoji = function(ctx, emoji, x, y, size) {
    if (!emoji) return;
    const cp = getEmojiCodePoint(emoji);
    const img = emojiImageCache[cp];
    if (img) {
        ctx.drawImage(img, x - size / 2, y - size / 2, size, size);
        return;
    }
    // Fallback: render via canvas font (PNG not cached yet or failed to download)
    // Always save/restore and ensure white fillStyle so emoji is visible on dark backgrounds
    ctx.save();
    ctx.font = `${Math.round(size)}px "Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji", "Segoe UI Symbol", sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = 'rgba(255,255,255,0.95)'; // ensure visible on dark bg
    // Strip VS16 (U+FE0F) — fonts without variation-selector support render it as a dotted circle
    ctx.fillText(String(emoji).replace(/️/g, ''), x, y);
    ctx.restore();
};

// ── getElementCoords offline helper ─────────────────────────────

function getElementCoords(el, fallbackY) {

    let x = null, y = null, isAbsolute = false;

    if (aspect_ratio === '16:9') {

        if (el.x_16_9 !== undefined && el.y_16_9 !== undefined) {

            x = el.x_16_9 * W; y = el.y_16_9 * H; isAbsolute = true;

        } else if (el.x !== undefined && el.y !== undefined) {

            x = el.x * W; y = el.y * H; isAbsolute = true;

        }

    } else {

        if (el.x_9_16 !== undefined && el.y_9_16 !== undefined) {

            x = el.x_9_16 * W; y = el.y_9_16 * H; isAbsolute = true;

        } else if (el.x !== undefined && el.y !== undefined) {

            x = el.x * W; y = el.y * H; isAbsolute = true;

        }

    }

    if (isAbsolute) {

        return { x, y, isAbsolute: true };

    } else {

        const tx = el.align === 'center' ? W/2 : el.align === 'right' ? W-MX : MX;

        return { x: tx, y: fallbackY, isAbsolute: false };

    }

}

// ── Path2D Polyfill for node-canvas ─────────────────────────────

if (typeof global.Path2D === 'undefined') {

    global.Path2D = class Path2D {

        constructor(pathStr) {

            this.commands = [];

            if (!pathStr) return;

            const tokenRegex = /([MmLlHhVvCcSsQqTtAaZz])|(-?\d*\.?\d+(?:[eE][-+]?\d+)?)/g;

            let match;

            let currentCmd = null;

            let currentArgs = [];

            while ((match = tokenRegex.exec(pathStr)) !== null) {

                if (match[1]) {

                    if (currentCmd) {

                        this.commands.push({ cmd: currentCmd, args: currentArgs });

                    }

                    currentCmd = match[1];

                    currentArgs = [];

                } else if (match[2]) {

                    currentArgs.push(parseFloat(match[2]));

                }

            }

            if (currentCmd) {

                this.commands.push({ cmd: currentCmd, args: currentArgs });

            }

        }

    };

    function applyPathToContext(c, path) {

        c.beginPath();

        let cx = 0, cy = 0;

        let startX = 0, startY = 0;

        for (const item of path.commands) {

            let { cmd, args } = item;

            let argIdx = 0;

            const nextArgs = (count) => {

                if (argIdx + count > args.length) return null;

                const slice = args.slice(argIdx, argIdx + count);

                argIdx += count;

                return slice;

            };

            do {

                if (cmd === 'M' || cmd === 'm') {

                    const pt = nextArgs(2);

                    if (!pt) break;

                    if (cmd === 'm') {

                        cx += pt[0];

                        cy += pt[1];

                    } else {

                        cx = pt[0];

                        cy = pt[1];

                    }

                    c.moveTo(cx, cy);

                    startX = cx;

                    startY = cy;

                    cmd = (cmd === 'm') ? 'l' : 'L';

                } else if (cmd === 'L' || cmd === 'l') {

                    const pt = nextArgs(2);

                    if (!pt) break;

                    if (cmd === 'l') {

                        cx += pt[0];

                        cy += pt[1];

                    } else {

                        cx = pt[0];

                        cy = pt[1];

                    }

                    c.lineTo(cx, cy);

                } else if (cmd === 'H' || cmd === 'h') {

                    const xVal = nextArgs(1);

                    if (!xVal) break;

                    if (cmd === 'h') {

                        cx += xVal[0];

                    } else {

                        cx = xVal[0];

                    }

                    c.lineTo(cx, cy);

                } else if (cmd === 'V' || cmd === 'v') {

                    const yVal = nextArgs(1);

                    if (!yVal) break;

                    if (cmd === 'v') {

                        cy += yVal[0];

                    } else {

                        cy = yVal[0];

                    }

                    c.lineTo(cx, cy);

                } else if (cmd === 'C' || cmd === 'c') {

                    const pts = nextArgs(6);

                    if (!pts) break;

                    let cp1x, cp1y, cp2x, cp2y, destx, desty;

                    if (cmd === 'c') {

                        cp1x = cx + pts[0]; cp1y = cy + pts[1];

                        cp2x = cx + pts[2]; cp2y = cy + pts[3];

                        destx = cx + pts[4]; desty = cy + pts[5];

                    } else {

                        cp1x = pts[0]; cp1y = pts[1];

                        cp2x = pts[2]; cp2y = pts[3];

                        destx = pts[4]; desty = pts[5];

                    }

                    c.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, destx, desty);

                    cx = destx;

                    cy = desty;

                } else if (cmd === 'Q' || cmd === 'q') {

                    const pts = nextArgs(4);

                    if (!pts) break;

                    let cpx, cpy, destx, desty;

                    if (cmd === 'q') {

                        cpx = cx + pts[0]; cpy = cy + pts[1];

                        destx = cx + pts[2]; desty = cy + pts[3];

                    } else {

                        cpx = pts[0]; cpy = pts[1];

                        destx = pts[2]; desty = pts[3];

                    }

                    c.quadraticCurveTo(cpx, cpy, destx, desty);

                    cx = destx;

                    cy = desty;

                } else if (cmd === 'Z' || cmd === 'z') {

                    c.closePath();

                    cx = startX;

                    cy = startY;

                    break;

                } else {

                    break;

                }

            } while (argIdx < args.length);

        }

    }

    const canvasPrototype = ctx.constructor.prototype;

    const originalFill = canvasPrototype.fill;

    const originalStroke = canvasPrototype.stroke;

    canvasPrototype.fill = function(arg1, arg2) {

        if (arg1 instanceof global.Path2D) {

            applyPathToContext(this, arg1);

            return originalFill.call(this, arg2);

        }

        return originalFill.apply(this, arguments);

    };

    canvasPrototype.stroke = function(arg1) {

        if (arg1 instanceof global.Path2D) {

            applyPathToContext(this, arg1);

            return originalStroke.call(this);

        }

        return originalStroke.apply(this, arguments);

    };

}

// ── Global Emoji Rendering Optimization for node-canvas ──────────

const canvasPrototype = ctx.constructor.prototype;

const originalFillText = canvasPrototype.fillText || ctx.fillText;

canvasPrototype.fillText = function(text, x, y, maxWidth) {
    if (this._isDrawingEmoji) {
        return originalFillText.apply(this, arguments);
    }
    if (text) {
        const str = String(text);
        const isEmoji = /[\uD800-\uDBFF][\uDC00-\uDFFF]|[\u2600-\u27BF]|[\u2300-\u23FF]/.test(str);
        if (isEmoji) {
            this.save();

            // Resolve a bright, solid color from transparent styles
            let currentFill = this.fillStyle;
            let solidColor = '#ffffff';

            if (typeof currentFill === 'string') {
                currentFill = currentFill.trim();
                if (currentFill.startsWith('#')) {
                    if (currentFill.length === 9) {
                        solidColor = currentFill.slice(0, 7); // #RRGGBBAA -> #RRGGBB
                    } else {
                        solidColor = currentFill;
                    }
                } else if (currentFill.startsWith('rgba')) {
                    const match = currentFill.match(/rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)/);
                    if (match) {
                        const r = parseInt(match[1]), g = parseInt(match[2]), b = parseInt(match[3]);
                        if (r < 65 && g < 65 && b < 65) {
                            solidColor = '#ffffff'; // Fallback if current fill is dark/background color
                        } else {
                            solidColor = `rgb(${r},${g},${b})`;
                        }
                    }
                } else if (currentFill.startsWith('rgb')) {
                    solidColor = currentFill;
                }
            }
            // Split string into text and emoji segments
            const emojiRegex = /([\uD800-\uDBFF][\uDC00-\uDFFF]|[\u2600-\u27BF]|[\u2300-\u23FF])/g;
            const parts = str.split(emojiRegex);
            const totalWidth = this.measureText(str).width;

            const align = this.textAlign || 'left';
            const baseline = this.textBaseline || 'alphabetic';

            let startX = x;
            if (align === 'center') {
                startX = x - totalWidth / 2;
            } else if (align === 'right') {
                startX = x - totalWidth;
            }

            let fontSize = 24;
            const fontMatch = this.font.match(/(\d+)px/);
            if (fontMatch) {
                fontSize = parseInt(fontMatch[1]);
            }

            let emojiY = y;
            if (baseline === 'top') {
                emojiY = y + fontSize / 2;
            } else if (baseline === 'bottom') {
                emojiY = y - fontSize / 2;
            } else if (baseline === 'middle') {
                emojiY = y;
            } else {
                emojiY = y - fontSize * 0.35;
            }

            let currentX = startX;
            this._isDrawingEmoji = true;
            try {
                for (const part of parts) {
                    if (!part) continue;
                    const isPartEmoji = /[\uD800-\uDBFF][\uDC00-\uDFFF]|[\u2600-\u27BF]|[\u2300-\u23FF]/.test(part);
                    const partWidth = this.measureText(part).width;
                    if (isPartEmoji) {
                        if (global.drawEmoji) {
                            global.drawEmoji(this, part, currentX + partWidth / 2, emojiY, fontSize * 1.1);
                        } else {
                            originalFillText.call(this, part, currentX, y);
                        }
                    } else {
                        this.save();
                        this.textAlign = 'left';
                        this.textBaseline = baseline;
                        originalFillText.call(this, part, currentX, y);
                        this.restore();
                    }
                    currentX += partWidth;
                }
            } finally {
                this._isDrawingEmoji = false;
            }

            this.restore();

            return;

        }

    }

    return originalFillText.apply(this, arguments);

};

// ── Drawing helpers ─────────────────────────────────────────────

function drawBg() {

    const g = ctx.createLinearGradient(0, 0, W, H);

    g.addColorStop(0, T.bgGrad[0]); g.addColorStop(1, T.bgGrad[1]);

    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);

    // Cyberpunk pixel ambience for the 'pixel' art style — neon grid + horizon + scanlines.

    // Chữ giữ nét căng vì chỉ vẽ ở lớp nền, không động vào font hay text layer.

    // --bg-fx off: nền phẳng (bỏ lưới/sao/quả cầu của phong cách)
    if (global.bgFxOff) return;

    if (global.artStyle === 'pixel') {

        const horizonY = H * 0.62;

        // Sun-like glow at horizon

        const sunGrad = ctx.createRadialGradient(W/2, horizonY, 0, W/2, horizonY, W * 0.55);

        sunGrad.addColorStop(0, 'rgba(255, 0, 170, 0.22)');

        sunGrad.addColorStop(0.4, 'rgba(120, 0, 200, 0.10)');

        sunGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');

        ctx.fillStyle = sunGrad;

        ctx.fillRect(0, 0, W, H);

        // Perspective neon grid below horizon

        ctx.save();

        ctx.strokeStyle = 'rgba(255, 0, 170, 0.18)';

        ctx.lineWidth = 1.5;

        // Vertical lines converging to vanishing point (W/2, horizonY)

        const cols = 24;

        for (let i = 0; i <= cols; i++) {

            const x = (i / cols) * W;

            ctx.beginPath();

            ctx.moveTo(W/2, horizonY);

            ctx.lineTo(x, H);

            ctx.stroke();

        }

        // Horizontal rows getting denser toward horizon

        ctx.strokeStyle = 'rgba(0, 255, 255, 0.18)';

        for (let r = 1; r <= 14; r++) {

            const t = r / 14;

            const y = horizonY + Math.pow(t, 1.7) * (H - horizonY);

            ctx.beginPath();

            ctx.moveTo(0, y);

            ctx.lineTo(W, y);

            ctx.stroke();

        }

        // Stars above horizon

        for (let i = 0; i < 60; i++) {

            const sx = (i * 73) % W;

            const sy = (i * 41) % horizonY;

            const a = 0.3 + 0.5 * (((i * 17) % 100) / 100);

            ctx.fillStyle = `rgba(${i % 3 === 0 ? '255,255,255' : '160,200,255'},${a * 0.5})`;

            ctx.fillRect(sx, sy, 2, 2);

        }

        // Soft scanlines overlay (Optimized with Offscreen Canvas)
        ctx.drawImage(getPixelScanlinesCanvas(), 0, 0);

        ctx.restore();

    }

    if (global.artStyle === 'liquidglass') {
        const t = typeof currentFrameTime !== 'undefined' ? currentFrameTime : 0;
        ctx.save();

        // 1. Draw thin background alignment grid
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.035)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        // Vertical center line
        ctx.moveTo(W / 2, 0);
        ctx.lineTo(W / 2, H);
        // Horizontal center line
        ctx.moveTo(0, H / 2);
        ctx.lineTo(W, H / 2);
        ctx.stroke();

        // Draw general grid lines
        ctx.beginPath();
        for (let x = W / 10; x < W; x += W / 10) {
            if (Math.abs(x - W/2) < 2) continue;
            ctx.moveTo(x, 0);
            ctx.lineTo(x, H);
        }
        for (let y = H / 20; y < H; y += H / 20) {
            if (Math.abs(y - H/2) < 2) continue;
            ctx.moveTo(0, y);
            ctx.lineTo(W, y);
        }
        ctx.stroke();

        // 2. Draw 4 floating blurred neon orbs (radial gradients)
        // Orb 1: Teal/Cyan
        const o1x = W * 0.25 + Math.sin(t * 0.3) * 60;
        const o1y = H * 0.3 + Math.cos(t * 0.25) * 60;
        const o1r = W * 0.55;
        const og1 = ctx.createRadialGradient(o1x, o1y, 0, o1x, o1y, o1r);
        og1.addColorStop(0, 'rgba(6, 182, 212, 0.15)');
        og1.addColorStop(1, 'rgba(6, 182, 212, 0)');
        ctx.fillStyle = og1;
        ctx.beginPath();
        ctx.arc(o1x, o1y, o1r, 0, Math.PI * 2);
        ctx.fill();

        // Orb 2: Purple/Violet
        const o2x = W * 0.8 + Math.cos(t * 0.2) * 80;
        const o2y = H * 0.2 + Math.sin(t * 0.35) * 80;
        const o2r = W * 0.65;
        const og2 = ctx.createRadialGradient(o2x, o2y, 0, o2x, o2y, o2r);
        og2.addColorStop(0, 'rgba(168, 85, 247, 0.13)');
        og2.addColorStop(1, 'rgba(168, 85, 247, 0)');
        ctx.fillStyle = og2;
        ctx.beginPath();
        ctx.arc(o2x, o2y, o2r, 0, Math.PI * 2);
        ctx.fill();

        // Orb 3: Green/Emerald
        const o3x = W * 0.3 + Math.sin(t * 0.25) * 70;
        const o3y = H * 0.75 + Math.cos(t * 0.3) * 70;
        const o3r = W * 0.6;
        const og3 = ctx.createRadialGradient(o3x, o3y, 0, o3x, o3y, o3r);
        og3.addColorStop(0, 'rgba(52, 211, 153, 0.12)');
        og3.addColorStop(1, 'rgba(52, 211, 153, 0)');
        ctx.fillStyle = og3;
        ctx.beginPath();
        ctx.arc(o3x, o3y, o3r, 0, Math.PI * 2);
        ctx.fill();

        // Orb 4: Soft Pink/Rose
        const o4x = W * 0.7 + Math.cos(t * 0.3) * 60;
        const o4y = H * 0.8 + Math.sin(t * 0.2) * 60;
        const o4r = W * 0.5;
        const og4 = ctx.createRadialGradient(o4x, o4y, 0, o4x, o4y, o4r);
        og4.addColorStop(0, 'rgba(251, 113, 133, 0.10)');
        og4.addColorStop(1, 'rgba(251, 113, 133, 0)');
        ctx.fillStyle = og4;
        ctx.beginPath();
        ctx.arc(o4x, o4y, o4r, 0, Math.PI * 2);
        ctx.fill();

        // 3. Draw scattered tiny twinkling background stars/particles
        for (let i = 0; i < 40; i++) {
            const sx = (i * 113) % W;
            const sy = (i * 79) % H;
            const size = 1 + (i % 2);
            const twinkle = 0.3 + 0.7 * Math.sin(t * (0.8 + (i % 3) * 0.4) + i);
            ctx.fillStyle = `rgba(255, 255, 255, ${twinkle * 0.35})`;
            ctx.fillRect(sx, sy, size, size);
        }

        ctx.restore();
    }

    ctx.globalAlpha = 1;

}

// ── Background removal via color-keying ──────────────────────

const _bgRemovalCache = {};

function removeImageBackground(img, cacheKey) {

    // Cache by explicit key to avoid reprocessing every frame

    const key = cacheKey || img.src || '';

    if (_bgRemovalCache[key]) return _bgRemovalCache[key];

    try {

        const sw = img.width, sh = img.height;

        if (sw <= 0 || sh <= 0) return img; // safety check

        const tmpCanvas = createCanvas(sw, sh);

        const tmpCtx = tmpCanvas.getContext('2d');

        tmpCtx.drawImage(img, 0, 0);

        const imgData = tmpCtx.getImageData(0, 0, sw, sh);

        const d = imgData.data;

        // Sample corners (5x5 blocks) to detect background color

        const samples = [];

        const S = 5;

        const corners = [

            [0, 0], [sw - S, 0],

            [0, sh - S], [sw - S, sh - S],

        ];

        for (const [cx, cy] of corners) {

            for (let y = Math.max(0, cy); y < Math.min(cy + S, sh); y++) {

                for (let x = Math.max(0, cx); x < Math.min(cx + S, sw); x++) {

                    const i = (y * sw + x) * 4;

                    samples.push([d[i], d[i+1], d[i+2]]);

                }

            }

        }

        if (samples.length === 0) return img;

        let bgR = 0, bgG = 0, bgB = 0;

        for (const [r, g, b] of samples) { bgR += r; bgG += g; bgB += b; }

        bgR = Math.round(bgR / samples.length);

        bgG = Math.round(bgG / samples.length);

        bgB = Math.round(bgB / samples.length);

        const TOLERANCE = 48, FADE_RANGE = 20;

        for (let i = 0; i < d.length; i += 4) {

            const dr = d[i] - bgR, dg = d[i+1] - bgG, db = d[i+2] - bgB;

            const dist = Math.sqrt(dr*dr + dg*dg + db*db);

            if (dist < TOLERANCE) { d[i+3] = 0; }

            else if (dist < TOLERANCE + FADE_RANGE) {

                d[i+3] = Math.round(((dist - TOLERANCE) / FADE_RANGE) * d[i+3]);

            }

        }

        tmpCtx.putImageData(imgData, 0, 0);

        _bgRemovalCache[key] = tmpCanvas;

        return tmpCanvas;

    } catch(e) {

        process.stderr.write(`[Renderer] removeImageBackground error: ${e.message}\n`);

        return img; // fallback to original

    }

}

function roundRect(x, y, w, h, r) {

    ctx.beginPath();

    ctx.moveTo(x+r, y); ctx.lineTo(x+w-r, y);

    ctx.arcTo(x+w, y, x+w, y+r, r); ctx.lineTo(x+w, y+h-r);

    ctx.arcTo(x+w, y+h, x+w-r, y+h, r); ctx.lineTo(x+r, y+h);

    ctx.arcTo(x, y+h, x, y+h-r, r); ctx.lineTo(x, y+r);

    ctx.arcTo(x, y, x+r, y, r); ctx.closePath();

}

function drawProgress(currentTime, totalDuration) {

    const barW = W - 120, barH = 6, barX = 60, barY = H - 50;

    roundRect(barX, barY, barW, barH, 3);

    ctx.fillStyle = T.progressBg; ctx.fill();

    const pct = Math.min(currentTime / totalDuration, 1);

    if (pct > 0) {

        roundRect(barX, barY, barW * pct, barH, 3);

        ctx.fillStyle = T.progressFill; ctx.fill();

    }

}

function parseMathString(str) {

    let index = 0;

    function parseExpression(endChar) {

        let parts = [];

        while (index < str.length) {

            if (endChar && str[index] === endChar) {

                break;

            }

            // Check for square root

            if (str.startsWith('\\sqrt{', index)) {

                index += 6; // skip '\sqrt{'

                let inner = parseExpression('}');

                if (index < str.length && str[index] === '}') {

                    index++; // skip '}'

                }

                parts.push({ type: 'sqrt', expr: inner });

                continue;

            }

            if (str.startsWith('√{', index)) {

                index += 2; // skip '√{'

                let inner = parseExpression('}');

                if (index < str.length && str[index] === '}') {

                    index++; // skip '}'

                }

                parts.push({ type: 'sqrt', expr: inner });

                continue;

            }

            // Exponents / Superscripts

            if (str[index] === '^') {

                index++; // skip '^'

                let expr;

                if (str[index] === '{') {

                    index++; // skip '{'

                    expr = parseExpression('}');

                    if (index < str.length && str[index] === '}') {

                        index++;

                    }

                } else {

                    // Group contiguous digits (e.g., ^50 -> superscript 50)

                    let textVal = "";

                    if (str[index] && /[0-9]/.test(str[index])) {

                        while (index < str.length && /[0-9]/.test(str[index])) {

                            textVal += str[index];

                            index++;

                        }

                    } else {

                        textVal = str[index] || '';

                        index++;

                    }

                    expr = [{ type: 'text', text: textVal }];

                }

                parts.push({ type: 'sup', expr: expr });

                continue;

            }

            // Subscripts

            if (str[index] === '_') {

                index++; // skip '_'

                let expr;

                if (str[index] === '{') {

                    index++; // skip '{'

                    expr = parseExpression('}');

                    if (index < str.length && str[index] === '}') {

                        index++;

                    }

                } else {

                    // Group contiguous digits (e.g., _10 -> subscript 10)

                    let textVal = "";

                    if (str[index] && /[0-9]/.test(str[index])) {

                        while (index < str.length && /[0-9]/.test(str[index])) {

                            textVal += str[index];

                            index++;

                        }

                    } else {

                        textVal = str[index] || '';

                        index++;

                    }

                    expr = [{ type: 'text', text: textVal }];

                }

                parts.push({ type: 'sub', expr: expr });

                continue;

            }

            // Regular characters

            let char = str[index];

            if (parts.length > 0 && parts[parts.length - 1].type === 'text') {

                parts[parts.length - 1].text += char;

            } else {

                parts.push({ type: 'text', text: char });

            }

            index++;

        }

        return parts;

    }

    return parseExpression();

}

function getFontForSize(size, bold) {

    return `${bold ? 'bold ' : ''}${Math.round(size)}px ${T.font}`;

}

function measureMathBlock(ctx, parts, fontSize) {

    let width = 0;

    const originalFont = ctx.font;

    for (const part of parts) {

        if (part.type === 'text') {

            ctx.font = getFontForSize(fontSize, false);

            width += ctx.measureText(part.text).width;

        } else if (part.type === 'sup') {

            width += measureMathBlock(ctx, part.expr, fontSize * 0.6);

        } else if (part.type === 'sub') {

            width += measureMathBlock(ctx, part.expr, fontSize * 0.6);

        } else if (part.type === 'sqrt') {

            const rw = fontSize * 0.4;

            const w = measureMathBlock(ctx, part.expr, fontSize);

            width += rw + w + 4;

        }

    }

    ctx.font = originalFont;

    return width;

}

function measureMathAwareText(text, font) {

    ctx.font = font;

    if (!text.includes('^') && !text.includes('_') && !text.includes('√') && !text.includes('\\sqrt')) {

        return ctx.measureText(text).width;

    }

    const sizeMatch = font.match(/(\d+)px/);

    const fontSize = sizeMatch ? parseInt(sizeMatch[1]) : 40;

    const parts = parseMathString(text);

    return measureMathBlock(ctx, parts, fontSize);

}

function drawMathBlock(ctx, parts, x, y, fontSize, color, bold) {

    let currentX = x;

    const originalFont = ctx.font;

    for (const part of parts) {

        if (part.type === 'text') {

            ctx.font = getFontForSize(fontSize, bold);

            ctx.fillStyle = color;

            ctx.fillText(part.text, currentX, y);

            currentX += ctx.measureText(part.text).width;

        } else if (part.type === 'sup') {

            const supSize = fontSize * 0.6;

            const supY = y - fontSize * 0.35;

            ctx.font = getFontForSize(supSize, bold);

            drawMathBlock(ctx, part.expr, currentX, supY, supSize, color, bold);

            currentX += measureMathBlock(ctx, part.expr, supSize);

        } else if (part.type === 'sub') {

            const subSize = fontSize * 0.6;

            const subY = y + fontSize * 0.18;

            ctx.font = getFontForSize(subSize, bold);

            drawMathBlock(ctx, part.expr, currentX, subY, subSize, color, bold);

            currentX += measureMathBlock(ctx, part.expr, subSize);

        } else if (part.type === 'sqrt') {

            const rw = fontSize * 0.4;

            const radicandWidth = measureMathBlock(ctx, part.expr, fontSize);

            // Draw radical symbol

            ctx.save();

            ctx.beginPath();

            ctx.moveTo(currentX, y - fontSize * 0.18);

            ctx.lineTo(currentX + rw * 0.3, y - fontSize * 0.08);

            ctx.lineTo(currentX + rw * 0.6, y + fontSize * 0.15);

            ctx.lineTo(currentX + rw, y - fontSize * 0.82);

            ctx.lineTo(currentX + rw + radicandWidth + 2, y - fontSize * 0.82);

            ctx.strokeStyle = color;

            ctx.lineWidth = Math.max(1.8, fontSize * 0.055);

            ctx.lineJoin = 'round';

            ctx.lineCap = 'round';

            ctx.stroke();

            ctx.restore();

            // Draw radicand

            drawMathBlock(ctx, part.expr, currentX + rw, y, fontSize, color, bold);

            currentX += rw + radicandWidth + 4;

        }

    }

    ctx.font = originalFont;

}

function drawRichMathText(ctx, text, x, y, fontSize, color, align, bold, currentBaseline) {

    if (!text.includes('^') && !text.includes('_') && !text.includes('√') && !text.includes('\\sqrt')) {

        ctx.fillStyle = color;

        ctx.textAlign = align;

        ctx.textBaseline = currentBaseline || 'top';

        ctx.font = getFontForSize(fontSize, bold);

        ctx.fillText(text, x, y);

        return;

    }

    const parts = parseMathString(text);

    const originalFont = ctx.font;

    const totalW = measureMathBlock(ctx, parts, fontSize);

    let startX = x;

    if (align === 'center') {

        startX = x - totalW / 2;

    } else if (align === 'right') {

        startX = x - totalW;

    } else {

        startX = x;

    }

    let baselineY = y;

    const bl = currentBaseline || 'top';

    if (bl === 'top') {

        baselineY = y + fontSize * 0.82;

    } else if (bl === 'middle') {

        baselineY = y + fontSize * 0.32;

    }

    ctx.save();

    ctx.textAlign = 'left';

    ctx.textBaseline = 'alphabetic';

    drawMathBlock(ctx, parts, startX, baselineY, fontSize, color, bold);

    ctx.restore();

}

function wrapText(text, maxW, font) {

    ctx.font = font;

    const words = text.split(' ');

    const lines = [];

    let line = '';

    for (const w of words) {

        const test = line ? line + ' ' + w : w;

        if (measureMathAwareText(test, font) > maxW && line) {

            lines.push(line);

            line = w;

        } else {

            line = test;

        }

    }

    if (line) lines.push(line);

    return lines.length > 0 ? lines : [''];

}

// Cứu custom_js một-dòng bị comment // nuốt hết lệnh vẽ phía sau: AI hay xuất
// code trên 1 dòng JSON nhưng vẫn chèn "// chú thích" — trong JS, // ăn đến
// hết dòng nên toàn bộ phần sau thành code chết (chạy êm, không vẽ gì).
// Chèn \n ngay trước câu lệnh thật đầu tiên sau mỗi // (bỏ qua // trong chuỗi
// như URL). Chỉ áp dụng cho code gần-một-dòng — code nhiều dòng comment kết
// thúc tự nhiên, không đụng vào.
function fixInlineComments(code) {
    if (!code || code.indexOf('//') === -1) return code;
    if ((code.match(/\n/g) || []).length >= 2 || code.length < 200) return code;
    const STMT = /ctx\.|ctx\[|ui\.|const\s|let\s|var\s|function\s|if\s*\(|for\s*\(|while\s*\(|return\s/g;
    let out = '', i = 0, q = null;
    const n = code.length;
    while (i < n) {
        const c = code[i];
        if (q) {
            if (c === '\\' && i + 1 < n) { out += code.substr(i, 2); i += 2; continue; }
            if (c === q) q = null;
            out += c; i++; continue;
        }
        if (c === '"' || c === "'" || c === '`') { q = c; out += c; i++; continue; }
        if (c === '/' && code[i + 1] === '/') {
            let j = code.indexOf('\n', i);
            const end = j === -1 ? n : j;
            STMT.lastIndex = i + 2;
            const m = STMT.exec(code);
            if (m && m.index < end) {
                out += code.slice(i, m.index) + '\n';
                i = m.index;
                continue;
            }
            out += code.slice(i, end); i = end; continue;
        }
        out += c; i++;
    }
    return out;
}

// ── Bộ icon Lucide (premium, nét mảnh, tô theo màu) ──────────────────────
// Thay cho emoji Twemoji kiểu hoạt hình ở các template editorial: emoji có
// icon tương ứng trong EMOJI_TO_LUCIDE sẽ vẽ Lucide stroke-based (ăn màu
// accent); emoji không có map (mặt cười, cờ...) vẫn dùng Twemoji màu.
let LUCIDE_ICONS = {};
try { LUCIDE_ICONS = require('./lucide_icons.js'); }
catch (e) {
    try { LUCIDE_ICONS = require(path.join(__dirname, 'lucide_icons.js')); }
    catch (e2) { LUCIDE_ICONS = {}; }
}
const EMOJI_TO_LUCIDE = {
    '📥': 'download', '📤': 'upload', '🧭': 'compass', '🛠': 'wrench', '🛠️': 'wrench',
    '⚙': 'settings', '⚙️': 'settings', '🔧': 'wrench', '🔍': 'search', '🔎': 'search',
    '🚀': 'rocket', '🧠': 'brain', '💬': 'message', '🗨': 'message',
    '👍': 'thumbs-up', '⭐': 'star', '🌟': 'sparkles', '✨': 'sparkles',
    '💰': 'coins', '🪙': 'coins', '💵': 'wallet', '👛': 'wallet',
    '✓': 'check', '✔': 'check', '✔️': 'check', '✅': 'check-circle',
    '📄': 'file', '📃': 'file', '📁': 'folder', '📂': 'folder',
    '🔒': 'lock', '🔐': 'lock', '🔑': 'key', '🗝': 'key',
    '🛡': 'shield', '🛡️': 'shield', '⚡': 'zap', '📊': 'chart',
    '📈': 'trending-up', '📉': 'trending-down', '💡': 'lightbulb', '🎯': 'target',
    '▶': 'play', '▶️': 'play', '📺': 'tv', '🎵': 'music', '🎶': 'music',
    '🌐': 'globe', '🌍': 'globe', '☁': 'cloud', '☁️': 'cloud',
    '🗄': 'database', '💾': 'database', '🖥': 'monitor', '💻': 'monitor',
    '📱': 'phone', '⏱': 'timer', '⏳': 'timer', '⏰': 'clock', '🕒': 'clock',
    '📅': 'calendar', '✉': 'mail', '✉️': 'mail', '📧': 'mail', '🔗': 'link',
    '👁': 'eye', '❌': 'x', '✖': 'x', '⚠': 'alert', '⚠️': 'alert',
    '➡': 'arrow-right', '➡️': 'arrow-right', '→': 'arrow-right',
    '🔄': 'refresh', '🔁': 'refresh', '📦': 'package', '🧊': 'box',
    '👥': 'users', '🤝': 'user-check', '🔖': 'bookmark', '🔥': 'flame',
    '📖': 'book', '📚': 'book', '🖊': 'pen', '✏': 'pen', '✏️': 'pen',
    '🧮': 'gauge', '🕸': 'network', '🌿': 'git-branch', '⏺': 'circle-dot',
};
// Parser path SVG tự viết (M/L/H/V/C/S/Q/T/A/Z, tuyệt đối + tương đối) —
// Path2D của node-canvas không hỗ trợ lệnh arc nên icon phức tạp vẽ thiếu.
function _svgArcToCtx(c, x1, y1, rx, ry, phi, fa, fs, x2, y2) {
    if (rx === 0 || ry === 0) { c.lineTo(x2, y2); return; }
    const rad = phi * Math.PI / 180;
    const cosP = Math.cos(rad), sinP = Math.sin(rad);
    const dx = (x1 - x2) / 2, dy = (y1 - y2) / 2;
    const x1p = cosP * dx + sinP * dy, y1p = -sinP * dx + cosP * dy;
    let rxs = rx * rx, rys = ry * ry;
    const lam = (x1p * x1p) / rxs + (y1p * y1p) / rys;
    if (lam > 1) { const sl = Math.sqrt(lam); rx *= sl; ry *= sl; rxs = rx * rx; rys = ry * ry; }
    let num = rxs * rys - rxs * y1p * y1p - rys * x1p * x1p;
    if (num < 0) num = 0;
    let coef = Math.sqrt(num / (rxs * y1p * y1p + rys * x1p * x1p));
    if (fa === fs) coef = -coef;
    const cxp = coef * rx * y1p / ry, cyp = -coef * ry * x1p / rx;
    const cxx = cosP * cxp - sinP * cyp + (x1 + x2) / 2;
    const cyy = sinP * cxp + cosP * cyp + (y1 + y2) / 2;
    const ang = (ux, uy, vx, vy) => {
        const dot = ux * vx + uy * vy;
        const len = Math.sqrt((ux * ux + uy * uy) * (vx * vx + vy * vy));
        let a = Math.acos(Math.max(-1, Math.min(1, dot / len)));
        if (ux * vy - uy * vx < 0) a = -a;
        return a;
    };
    const th1 = ang(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry);
    let dth = ang((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry);
    if (!fs && dth > 0) dth -= 2 * Math.PI;
    if (fs && dth < 0) dth += 2 * Math.PI;
    const segs = Math.max(1, Math.ceil(Math.abs(dth) / (Math.PI / 2)));
    const delta = dth / segs;
    const t = 4 / 3 * Math.tan(delta / 4);
    let th = th1, px = x1, py = y1;
    for (let i = 0; i < segs; i++) {
        const th2 = th + delta;
        const c1 = Math.cos(th), s1 = Math.sin(th);
        const c2 = Math.cos(th2), s2 = Math.sin(th2);
        const ex = cxx + rx * c2 * cosP - ry * s2 * sinP;
        const ey = cyy + rx * c2 * sinP + ry * s2 * cosP;
        const q1x = px - t * (rx * s1 * cosP + ry * c1 * sinP);
        const q1y = py + t * (-rx * s1 * sinP + ry * c1 * cosP);
        const q2x = ex + t * (rx * s2 * cosP + ry * c2 * sinP);
        const q2y = ey - t * (-rx * s2 * sinP + ry * c2 * cosP);
        c.bezierCurveTo(q1x, q1y, q2x, q2y, ex, ey);
        th = th2; px = ex; py = ey;
    }
}
function strokeSvgPath(c, d) {
    const tok = d.match(/[a-df-z]|[-+]?\d*\.?\d+(?:e[-+]?\d+)?/gi) || [];
    let i = 0, cmd = '', x = 0, y = 0, sx = 0, sy = 0;
    let cpx = null, cpy = null, qx = null, qy = null;
    const num = () => parseFloat(tok[i++]);
    c.beginPath();
    while (i < tok.length) {
        const t0 = tok[i];
        if (/[a-z]/i.test(t0) && t0.length === 1) { cmd = t0; i++; }
        const rel = cmd === cmd.toLowerCase() && cmd !== 'z' && cmd !== 'Z';
        switch (cmd.toUpperCase()) {
            case 'M': { const nx = num() + (rel ? x : 0), ny = num() + (rel ? y : 0);
                c.moveTo(nx, ny); x = sx = nx; y = sy = ny; cmd = rel ? 'l' : 'L'; break; }
            case 'L': { const nx = num() + (rel ? x : 0), ny = num() + (rel ? y : 0);
                c.lineTo(nx, ny); x = nx; y = ny; break; }
            case 'H': { const nx = num() + (rel ? x : 0); c.lineTo(nx, y); x = nx; break; }
            case 'V': { const ny = num() + (rel ? y : 0); c.lineTo(x, ny); y = ny; break; }
            case 'C': { const a1 = num() + (rel ? x : 0), a2 = num() + (rel ? y : 0);
                const b1 = num() + (rel ? x : 0), b2 = num() + (rel ? y : 0);
                const nx = num() + (rel ? x : 0), ny = num() + (rel ? y : 0);
                c.bezierCurveTo(a1, a2, b1, b2, nx, ny);
                cpx = b1; cpy = b2; x = nx; y = ny; break; }
            case 'S': { const b1 = num() + (rel ? x : 0), b2 = num() + (rel ? y : 0);
                const nx = num() + (rel ? x : 0), ny = num() + (rel ? y : 0);
                const a1 = cpx !== null ? 2 * x - cpx : x;
                const a2 = cpy !== null ? 2 * y - cpy : y;
                c.bezierCurveTo(a1, a2, b1, b2, nx, ny);
                cpx = b1; cpy = b2; x = nx; y = ny; break; }
            case 'Q': { const a1 = num() + (rel ? x : 0), a2 = num() + (rel ? y : 0);
                const nx = num() + (rel ? x : 0), ny = num() + (rel ? y : 0);
                c.quadraticCurveTo(a1, a2, nx, ny);
                qx = a1; qy = a2; x = nx; y = ny; break; }
            case 'T': { const a1 = qx !== null ? 2 * x - qx : x;
                const a2 = qy !== null ? 2 * y - qy : y;
                const nx = num() + (rel ? x : 0), ny = num() + (rel ? y : 0);
                c.quadraticCurveTo(a1, a2, nx, ny);
                qx = a1; qy = a2; x = nx; y = ny; break; }
            case 'A': { const rx = num(), ry = num(), rot = num();
                const fa = num() ? 1 : 0, fs = num() ? 1 : 0;
                const nx = num() + (rel ? x : 0), ny = num() + (rel ? y : 0);
                _svgArcToCtx(c, x, y, rx, ry, rot, fa, fs, nx, ny);
                x = nx; y = ny; break; }
            case 'Z': { c.closePath(); x = sx; y = sy; break; }
            default: i++; break;
        }
        if ('CS'.indexOf(cmd.toUpperCase()) < 0) { cpx = null; cpy = null; }
        if ('QT'.indexOf(cmd.toUpperCase()) < 0) { qx = null; qy = null; }
    }
    c.stroke();
}
function drawLucide(c, name, cx, cy, size, color) {
    const els = LUCIDE_ICONS[name];
    if (!els || !els.length) return false;
    c.save();
    c.translate(cx - size / 2, cy - size / 2);
    const s = size / 24;
    c.scale(s, s);
    c.strokeStyle = color || '#64748b';
    c.lineWidth = 2;
    c.lineCap = 'round';
    c.lineJoin = 'round';
    try {
        for (const e of els) {
            if (e.t === 'p') { strokeSvgPath(c, e.d); }
            else if (e.t === 'c') { c.beginPath(); c.arc(e.cx, e.cy, e.r, 0, Math.PI * 2); c.stroke(); }
            else if (e.t === 'l') { c.beginPath(); c.moveTo(e.x1, e.y1); c.lineTo(e.x2, e.y2); c.stroke(); }
            else if (e.t === 'r') {
                c.beginPath();
                if (c.roundRect) c.roundRect(e.x, e.y, e.w, e.h, e.rx || 0);
                else c.rect(e.x, e.y, e.w, e.h);
                c.stroke();
            }
            else if (e.t === 'pl') {
                c.beginPath(); c.moveTo(e.pts[0], e.pts[1]);
                for (let i = 2; i < e.pts.length; i += 2) c.lineTo(e.pts[i], e.pts[i + 1]);
                if (e.close) c.closePath();
                c.stroke();
            }
        }
    } catch (err) { c.restore(); return false; }
    c.restore();
    return true;
}
global.drawLucide = drawLucide;
global.EMOJI_TO_LUCIDE = EMOJI_TO_LUCIDE;

// ── Bộ linh kiện PREMIUM cho custom_js (ui.*) ────────────────────────────
// AI vẽ tay hay ra rect phẳng + màu nhạt + emoji trần → không premium.
// Bộ helper này dựng sẵn các linh kiện đã tune kỹ (thẻ kính, chip, KPI,
// gauge, luồng hạt...) — code AI chỉ lắp ráp. Vẽ bằng ctx GỐC (không qua
// proxy remap): màu đã tự chọn theo tông sáng/tối, bóng đổ mềm không bị
// proxy cắt, màu TƯƠI bão hoà cao thay vì màu chữ nhạt.
function makeUiKit(ctx, artStyle, time, rc, drawEmojiFn) {
    const light = ['watercolor', 'inkwash', 'pastel', 'sketch', 'sketchnote', 'aurora', 'warmpaper'].includes(artStyle);
    function hexRgb(h) {
        const m = /^#?([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(h || '');
        if (!m) return null;
        let s = m[1];
        if (s.length === 3) s = s.split('').map(c => c + c).join('');
        return [parseInt(s.slice(0, 2), 16), parseInt(s.slice(2, 4), 16), parseInt(s.slice(4, 6), 16)];
    }
    function mix(a, b, t) {
        const x = hexRgb(a), y = hexRgb(b);
        if (!x || !y) return a;
        return `rgb(${Math.round(x[0] + (y[0] - x[0]) * t)},${Math.round(x[1] + (y[1] - x[1]) * t)},${Math.round(x[2] + (y[2] - x[2]) * t)})`;
    }
    function withA(c, a) {
        const r = hexRgb(c);
        if (r) return `rgba(${r[0]},${r[1]},${r[2]},${a})`;
        const m = /^rgba?\(([^)]+)\)/.exec(c || '');
        if (m) { const p = m[1].split(',').slice(0, 3).map(s => s.trim()); return `rgba(${p.join(',')},${a})`; }
        return light ? `rgba(30,41,59,${a})` : `rgba(255,255,255,${a})`;
    }
    // Màu TƯƠI: bộ bão hoà cao — nền sáng không dùng màu chữ (nhạt nhoà).
    // yellow nền sáng = amber ĐẬM (#d97706): cam nhạt trên trắng rớt chuẩn
    // tương phản WCAG, chữ "cháy" khi xem ngoài trời.
    const VIVID = light
        ? { green: '#16a34a', cyan: '#0284c7', yellow: '#d97706', red: '#ef4444', purple: '#7c3aed', pink: '#db2777', white: '#334155', title: '#2563eb' }
        : (artStyle === 'neonsketch'
            ? { green: '#a3e635', cyan: '#38bdf8', yellow: '#fde047', red: '#f87171', purple: '#c4b5fd', pink: '#f9a8d4', white: '#f2f7ec', title: '#fde047' }
            : { green: '#34d399', cyan: '#22d3ee', yellow: '#fbbf24', red: '#fb7185', purple: '#a78bfa', pink: '#f472b6', white: '#e2e8f0', title: '#60a5fa' });
    function col(c) { return (c && VIVID[c]) || (hexRgb(c) ? c : (c && c.startsWith && c.startsWith('rgb') ? c : VIVID.cyan)); }
    function lite(c) { return mix(hexRgb(col(c)) ? col(c) : '#38bdf8', '#ffffff', light ? 0.22 : 0.45); }
    const FONT = (typeof SYSTEM_FONT_STACK !== 'undefined') ? SYSTEM_FONT_STACK : "'Segoe UI', sans-serif";
    function rr(x, y, w, h, r) { ctx.beginPath(); ctx.roundRect(x, y, w, h, r); }
    function noShadow() { ctx.shadowBlur = 0; ctx.shadowColor = 'rgba(0,0,0,0)'; ctx.shadowOffsetX = 0; ctx.shadowOffsetY = 0; }
    const CLA = v => Math.max(0, Math.min(1, v));

    const ui = {};
    // Thẻ kính premium: bóng mềm + gradient + viền + vệt sheen + mép nhấn màu
    ui.glass = function (x, y, w, h, o = {}) {
        // neonsketch: panel terminal PHẲNG viền lime — không phải kính xanh
        if (artStyle === 'neonsketch') {
            const r2 = o.r !== undefined ? o.r : 8;
            ctx.save();
            ctx.globalAlpha *= CLA(o.alpha === undefined ? 1 : o.alpha);
            ctx.fillStyle = 'rgba(8,13,5,0.78)';
            rr(x, y, w, h, r2); ctx.fill();
            ctx.shadowColor = 'rgba(163,230,53,0.45)'; ctx.shadowBlur = 12;
            ctx.strokeStyle = 'rgba(163,230,53,0.5)';
            ctx.lineWidth = 2;
            rr(x, y, w, h, r2); ctx.stroke();
            noShadow();
            if (o.accent) {
                const a2 = col(o.accent);
                ctx.shadowColor = withA(a2, 0.8); ctx.shadowBlur = 12;
                ctx.fillStyle = a2;
                rr(x + 12, y + 14, 4, h - 28, 2); ctx.fill();
            }
            ctx.restore();
            return;
        }
        const r = o.r !== undefined ? o.r : 28;
        ctx.save();
        ctx.globalAlpha *= CLA(o.alpha === undefined ? 1 : o.alpha);
        ctx.shadowColor = light ? 'rgba(80,100,160,0.22)' : 'rgba(0,0,0,0.4)';
        ctx.shadowBlur = light ? 22 : 28;
        ctx.shadowOffsetY = 10;
        const g = ctx.createLinearGradient(0, y, 0, y + h);
        if (light) { g.addColorStop(0, 'rgba(255,255,255,0.94)'); g.addColorStop(1, 'rgba(243,246,255,0.88)'); }
        else { g.addColorStop(0, 'rgba(26,34,62,0.88)'); g.addColorStop(1, 'rgba(13,17,36,0.84)'); }
        ctx.fillStyle = g;
        rr(x, y, w, h, r); ctx.fill();
        noShadow();
        ctx.strokeStyle = light ? 'rgba(30,45,90,0.13)' : 'rgba(255,255,255,0.15)';
        ctx.lineWidth = 1.5;
        rr(x, y, w, h, r); ctx.stroke();
        // sheen: vệt sáng mỏng trên đỉnh thẻ
        ctx.save();
        rr(x, y, w, h, r); ctx.clip();
        const s = ctx.createLinearGradient(0, y, 0, y + h * 0.4);
        s.addColorStop(0, light ? 'rgba(255,255,255,0.85)' : 'rgba(255,255,255,0.10)');
        s.addColorStop(1, 'rgba(255,255,255,0)');
        ctx.fillStyle = s;
        ctx.fillRect(x, y, w, h * 0.4);
        ctx.restore();
        if (o.accent) {
            const a = col(o.accent);
            if (!light) { ctx.shadowColor = withA(a, 0.7); ctx.shadowBlur = 14; }
            ctx.fillStyle = a;
            rr(x + 14, y + 18, 5, h - 36, 3); ctx.fill();
        }
        ctx.restore();
    };
    // Tiêu đề gradient tươi
    ui.title = function (cx, y, text, o = {}) {
        const size = Math.max(30, Number(o.size) || 46);
        const maxW = Math.max(160, Number(o.maxWidth) || W - 180);
        ctx.save();
        ctx.globalAlpha *= CLA(o.alpha === undefined ? 1 : o.alpha);
        ctx.font = `bold ${size}px ${FONT}`;
        ctx.textAlign = 'center';
        const w = ctx.measureText(text).width;
        const paintW = Math.min(w, maxW);
        const from = o.from || o.color || 'title';
        const to = o.to || o.color || 'cyan';
        const g = ctx.createLinearGradient(cx - paintW / 2, 0, cx + paintW / 2, 0);
        g.addColorStop(0, col(from));
        g.addColorStop(1, col(to));
        if (!light) { ctx.shadowColor = withA(col(from), 0.55); ctx.shadowBlur = 18; }
        ctx.fillStyle = g;
        ctx.fillText(text, cx, y, maxW);
        ctx.restore();
    };
    // Chip/pill nhãn
    ui.chip = function (cx, cy, text, o = {}) {
        const size = o.size || 26, pad = 18;
        ctx.save();
        ctx.globalAlpha *= CLA(o.alpha === undefined ? 1 : o.alpha);
        ctx.font = `600 ${size}px ${FONT}`;
        const c = col(o.color || 'cyan');
        const tw = ctx.measureText(text).width;
        // AI often places three chips in one row but gives one of them a long
        // sentence. Keep side chips compact and clamp every pill inside the
        // safe 40px frame margin instead of letting it overlap/cut off.
        const rowCap = Math.abs(cx - W / 2) > 80 ? 220 : W - 200;
        const maxW = Math.max(140, Number(o.maxWidth) || rowCap);
        const w = Math.min(tw + pad * 2, maxW), h = size + 20;
        const safeCx = Math.max(40 + w / 2, Math.min(W - 40 - w / 2, cx));
        const g = ctx.createLinearGradient(0, cy - h / 2, 0, cy + h / 2);
        g.addColorStop(0, withA(c, light ? 0.14 : 0.22));
        g.addColorStop(1, withA(c, light ? 0.22 : 0.34));
        ctx.fillStyle = g;
        rr(safeCx - w / 2, cy - h / 2, w, h, h / 2); ctx.fill();
        ctx.strokeStyle = withA(c, 0.6); ctx.lineWidth = 1.5;
        rr(safeCx - w / 2, cy - h / 2, w, h, h / 2); ctx.stroke();
        ctx.fillStyle = light ? mix(c, '#1e293b', 0.15) : lite(c);
        ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillText(text, safeCx, cy + 1, Math.max(40, w - pad * 2));
        ctx.restore();
    };
    // Số liệu lớn + nhãn
    ui.kpi = function (cx, y, value, label, o = {}) {
        const size = o.size || 86;
        ctx.save();
        ctx.globalAlpha *= CLA(o.alpha === undefined ? 1 : o.alpha);
        ctx.font = `bold ${size}px ${FONT}`;
        ctx.textAlign = 'center';
        const c = col(o.color || 'cyan');
        const w = ctx.measureText(String(value)).width;
        const maxW = Math.max(160, Number(o.maxWidth) || (Math.abs(cx - W / 2) > 80 ? 220 : W - 200));
        const safeCx = Math.max(40 + maxW / 2, Math.min(W - 40 - maxW / 2, cx));
        const paintW = Math.min(w, maxW);
        const g = ctx.createLinearGradient(safeCx - paintW / 2, 0, safeCx + paintW / 2, 0);
        g.addColorStop(0, c); g.addColorStop(1, lite(c));
        if (!light) { ctx.shadowColor = withA(c, 0.6); ctx.shadowBlur = 22; }
        ctx.fillStyle = g;
        ctx.fillText(String(value), safeCx, y, maxW);
        noShadow();
        if (label) {
            ctx.font = `600 24px ${FONT}`;
            ctx.fillStyle = light ? 'rgba(51,65,85,0.85)' : 'rgba(226,232,240,0.8)';
            ctx.fillText(String(label).toUpperCase(), safeCx, y + 40, maxW);
        }
        ctx.restore();
    };
    // Emoji trên đĩa gradient + vành sáng (emoji trần nhìn rẻ)
    ui.icon = function (cx, cy, emoji, size = 64, o = {}) {
        const c = col(o.color || 'cyan');
        const R = size * 0.82;
        ctx.save();
        ctx.globalAlpha *= CLA(o.alpha === undefined ? 1 : o.alpha);
        const g = ctx.createRadialGradient(cx, cy, R * 0.2, cx, cy, R);
        g.addColorStop(0, withA(c, light ? 0.18 : 0.32));
        g.addColorStop(1, withA(c, 0.05));
        ctx.fillStyle = g;
        ctx.beginPath(); ctx.arc(cx, cy, R, 0, Math.PI * 2); ctx.fill();
        if (!light) { ctx.shadowColor = withA(c, 0.6); ctx.shadowBlur = 16; }
        ctx.strokeStyle = withA(c, 0.55); ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(cx, cy, R, 0, Math.PI * 2); ctx.stroke();
        noShadow();
        // Ưu tiên icon Lucide (nét mảnh premium, tô màu accent) — emoji chỉ
        // là fallback khi không có icon tương ứng.
        const luc = (typeof EMOJI_TO_LUCIDE !== 'undefined') && EMOJI_TO_LUCIDE[emoji];
        if (luc && typeof drawLucide === 'function'
            && drawLucide(ctx, luc, cx, cy, size * 0.92, light ? c : lite(c))) {
            /* đã vẽ lucide */
        } else if (drawEmojiFn) drawEmojiFn(ctx, emoji, cx, cy + size * 0.36, size);
        else { ctx.font = `${size}px ${FONT}`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(emoji, cx, cy); }
        ctx.restore();
    };
    // Thanh gauge bo tròn + đầu phát sáng
    ui.bar = function (x, y, w, h, p, o = {}) {
        h = h || 16;
        const c = col(o.color || 'cyan');
        const pw = Math.max(h, w * CLA(p));
        ctx.save();
        ctx.globalAlpha *= CLA(o.alpha === undefined ? 1 : o.alpha);
        ctx.fillStyle = light ? 'rgba(30,41,59,0.08)' : 'rgba(255,255,255,0.10)';
        rr(x, y, w, h, h / 2); ctx.fill();
        const g = ctx.createLinearGradient(x, 0, x + pw, 0);
        g.addColorStop(0, c); g.addColorStop(1, lite(c));
        ctx.fillStyle = g;
        rr(x, y, pw, h, h / 2); ctx.fill();
        if (!light) { ctx.shadowColor = withA(c, 0.8); ctx.shadowBlur = 12; }
        ctx.fillStyle = lite(c);
        ctx.beginPath(); ctx.arc(x + pw - h / 2, y + h / 2, h * 0.62, 0, Math.PI * 2); ctx.fill();
        ctx.restore();
    };
    // Vòng gauge
    ui.ring = function (cx, cy, r, p, o = {}) {
        const lw = o.w || 14, c = col(o.color || 'cyan');
        const a0 = -Math.PI / 2, a1 = a0 + Math.PI * 2 * CLA(p);
        ctx.save();
        ctx.globalAlpha *= CLA(o.alpha === undefined ? 1 : o.alpha);
        ctx.lineCap = 'round';
        ctx.strokeStyle = light ? 'rgba(30,41,59,0.08)' : 'rgba(255,255,255,0.10)';
        ctx.lineWidth = lw;
        ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.stroke();
        if (!light) { ctx.shadowColor = withA(c, 0.7); ctx.shadowBlur = 16; }
        ctx.strokeStyle = c;
        ctx.beginPath(); ctx.arc(cx, cy, r, a0, a1); ctx.stroke();
        noShadow();
        ctx.fillStyle = lite(c);
        ctx.beginPath(); ctx.arc(cx + Math.cos(a1) * r, cy + Math.sin(a1) * r, lw * 0.55, 0, Math.PI * 2); ctx.fill();
        if (o.text) {
            ctx.fillStyle = light ? '#1e293b' : '#f1f5f9';
            ctx.font = `bold ${Math.round(r * 0.52)}px ${FONT}`;
            ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
            ctx.fillText(o.text, cx, cy + 2);
        }
        ctx.restore();
    };
    // Luồng kết nối + hạt sáng chạy theo đường
    ui.flow = function (pts, o = {}) {
        if (!pts || pts.length < 2) return;
        const c = col(o.color || 'cyan');
        ctx.save();
        ctx.globalAlpha *= CLA(o.alpha === undefined ? 1 : o.alpha);
        ctx.strokeStyle = withA(c, light ? 0.5 : 0.4);
        ctx.lineWidth = o.w || 3;
        ctx.beginPath();
        ctx.moveTo(pts[0][0], pts[0][1]);
        for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
        ctx.stroke();
        // tổng chiều dài để rải hạt đều
        let total = 0; const segs = [];
        for (let i = 1; i < pts.length; i++) {
            const d = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
            segs.push(d); total += d;
        }
        const N = o.n || 3;
        for (let k = 0; k < N; k++) {
            let t = ((time * (o.speed || 0.22)) + k / N) % 1;
            let dist = t * total, i = 0;
            while (i < segs.length && dist > segs[i]) { dist -= segs[i]; i++; }
            if (i >= segs.length) i = segs.length - 1;
            const f = segs[i] ? dist / segs[i] : 0;
            const px = pts[i][0] + (pts[i + 1][0] - pts[i][0]) * f;
            const py = pts[i][1] + (pts[i + 1][1] - pts[i][1]) * f;
            if (!light) { ctx.shadowColor = withA(c, 0.9); ctx.shadowBlur = 12; }
            ctx.fillStyle = lite(c);
            ctx.beginPath(); ctx.arc(px, py, o.dot || 5, 0, Math.PI * 2); ctx.fill();
            noShadow();
        }
        ctx.restore();
    };
    // Kẻ phân cách mờ dần 2 đầu
    ui.divider = function (x1, x2, y) {
        ctx.save();
        const g = ctx.createLinearGradient(x1, 0, x2, 0);
        const mid = light ? 'rgba(30,45,90,0.25)' : 'rgba(255,255,255,0.25)';
        g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(0.5, mid); g.addColorStop(1, 'rgba(0,0,0,0)');
        ctx.strokeStyle = g; ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.moveTo(x1, y); ctx.lineTo(x2, y); ctx.stroke();
        ctx.restore();
    };
    // Nhân vật/hình PNG từ kho sprite của template — nhún + lắc nhẹ theo
    // time cho "sống"; thiếu sprite thì vẽ que đơn giản thay (không trắng hình).
    ui.sprite = function (name, cx, cy, size, o = {}) {
        size = size || 420;
        const img = (typeof global !== 'undefined' && global.SPRITES)
            ? global.SPRITES[name] : null;
        ctx.save();
        const bob = Math.sin(time * 2 + (o.seed || 0)) * (o.bob !== undefined ? o.bob : 8);
        const tilt = Math.sin(time * 1.6 + (o.seed || 0)) * (o.tilt !== undefined ? o.tilt : 0.045);
        ctx.translate(cx, cy + bob);
        ctx.rotate(tilt);
        if (img) {
            const s = size / Math.max(img.width, img.height);
            ctx.drawImage(img, -img.width * s / 2, -img.height * s / 2,
                          img.width * s, img.height * s);
        } else {
            ctx.strokeStyle = '#fde047'; ctx.lineWidth = 7; ctx.lineCap = 'round';
            ctx.shadowColor = '#fde047'; ctx.shadowBlur = 20;
            const r = size * 0.14;
            ctx.beginPath(); ctx.arc(0, -size * 0.28, r, 0, Math.PI * 2); ctx.stroke();
            ctx.beginPath(); ctx.moveTo(0, -size * 0.28 + r); ctx.lineTo(0, size * 0.1); ctx.stroke();
            ctx.beginPath(); ctx.moveTo(0, -size * 0.1); ctx.lineTo(-size * 0.18, 0); ctx.stroke();
            ctx.beginPath(); ctx.moveTo(0, -size * 0.1); ctx.lineTo(size * 0.18, 0); ctx.stroke();
            ctx.beginPath(); ctx.moveTo(0, size * 0.1); ctx.lineTo(-size * 0.14, size * 0.32); ctx.stroke();
            ctx.beginPath(); ctx.moveTo(0, size * 0.1); ctx.lineTo(size * 0.14, size * 0.32); ctx.stroke();
        }
        ctx.restore();
    };
    ui.withA = withA; ui.mix = mix; ui.col = col; ui.lite = lite;
    return ui;
}

// ── Bộ dựng cảnh MATH NOIR cho custom_js (mnk.*) ─────────────────────────
// Ngôn ngữ manim/3Blue1Bồ: đen tuyền + nét trắng MẢNH + đúng MỘT accent
// vàng. Mọi hàm vẽ nhận progress e (0..1, mặc định 1) và TỰ VẼ NÉT
// (clip/dash-offset/path cắt) — ease cubic-out bên trong, code AI chỉ đưa
// tiến độ thô (thường qua mnk.seq để so le). Kit không phụ thuộc artStyle
// về mặt code — dùng được ở mọi style, nhưng tông màu tune cho mathnoir.
function makeMnKit(ctx, time) {
    const INK = '#e8e8ea', MUTED = '#9a9aa0', FAINT = 'rgba(232,232,234,0.45)', ACCENT = '#facc15';
    const FONT = "'Segoe UI', sans-serif";
    const CL = v => Math.max(0, Math.min(1, v));
    const EZ = t => 1 - Math.pow(1 - CL(t), 3); // cubic-out
    // sub-progress: đoạn [a..b] của e — để 1 hàm tự chia pha vẽ
    const seg = (e, a, b) => CL((e - a) / Math.max(b - a, 0.0001));
    function pen(color, lw) {
        ctx.strokeStyle = color || INK;
        ctx.lineWidth = lw || 2;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        ctx.setLineDash([]);
        ctx.shadowBlur = 0; ctx.shadowColor = 'rgba(0,0,0,0)';
        ctx.shadowOffsetX = 0; ctx.shadowOffsetY = 0;
    }
    function rrPath(x, y, w, h, r) {
        ctx.beginPath();
        if (ctx.roundRect) ctx.roundRect(x, y, w, h, r);
        else ctx.rect(x, y, w, h);
    }
    // đầu mũi tên nhỏ tại (x,y) theo hướng ang
    function head(x, y, ang, color, a) {
        const L = 13;
        ctx.save();
        ctx.globalAlpha *= CL(a);
        pen(color, 2);
        ctx.beginPath();
        ctx.moveTo(x - L * Math.cos(ang - 0.42), y - L * Math.sin(ang - 0.42));
        ctx.lineTo(x, y);
        ctx.lineTo(x - L * Math.cos(ang + 0.42), y - L * Math.sin(ang + 0.42));
        ctx.stroke();
        ctx.restore();
    }

    const mnk = {};
    // tokens lộ ra ngoài — code lắp ráp dùng lại đúng bảng màu
    mnk.INK = INK; mnk.MUTED = MUTED; mnk.FAINT = FAINT; mnk.ACCENT = ACCENT;

    // Tiến độ so le cho item i trong n item: item i bắt đầu sau
    // i*(1-overlap)/n (chuẩn hoá), mọi item cùng kết thúc tại P=1.
    mnk.seq = function (P, i, n, overlap) {
        overlap = overlap === undefined ? 0.35 : overlap;
        n = Math.max(1, n || 1);
        const start = i * (1 - overlap) / n;
        const dur = Math.max(1 - (n - 1) * (1 - overlap) / n, 0.0001);
        return CL((P - start) / dur);
    };

    // Hộp bo góc nét mảnh: viền tự vẽ vòng quanh, dash tuỳ chọn, label
    // nhỏ MUTED bên TRONG mép trên (kiểu "danh sách hữu hạn").
    mnk.box = function (x, y, w, h, o) {
        o = o || {};
        const e = o.e === undefined ? 1 : o.e, t = EZ(e);
        if (t <= 0) return;
        const r = o.r === undefined ? 10 : o.r;
        const col = o.accent ? ACCENT : INK;
        ctx.save();
        if (o.fill) {
            ctx.save();
            ctx.globalAlpha *= seg(t, 0.25, 1);
            ctx.fillStyle = 'rgba(255,255,255,0.04)';
            rrPath(x, y, w, h, r); ctx.fill();
            ctx.restore();
        }
        pen(col, 2);
        if (o.dash) {
            // dash: lộ dần bằng clip quét ngang (giữ nhịp dash đều)
            ctx.save();
            ctx.beginPath();
            ctx.rect(x - 6, y - 6, (w + 12) * t, h + 12);
            ctx.clip();
            ctx.setLineDash([10, 8]);
            rrPath(x, y, w, h, r); ctx.stroke();
            ctx.restore();
        } else {
            // nét liền: tự vẽ vòng quanh chu vi bằng dash-offset
            const per = 2 * (w + h) + 2 * Math.PI * r - 8 * r + 4;
            ctx.setLineDash([per * t, per]);
            rrPath(x, y, w, h, r); ctx.stroke();
            ctx.setLineDash([]);
        }
        if (o.label) {
            ctx.save();
            ctx.globalAlpha *= seg(t, 0.45, 1);
            ctx.font = `500 24px ${FONT}`;
            ctx.fillStyle = MUTED;
            ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic';
            ctx.fillText(o.label, x + w / 2, y + 34);
            ctx.restore();
        }
        ctx.restore();
    };

    // MỘT gạch chéo phủ nhận (trên-trái → dưới-phải), tự vẽ theo e.
    mnk.cross = function (x, y, w, h, o) {
        o = o || {};
        const e = o.e === undefined ? 1 : o.e, t = EZ(e);
        if (t <= 0) return;
        ctx.save();
        pen(o.color || FAINT, 2.5);
        ctx.beginPath();
        ctx.moveTo(x, y);
        ctx.lineTo(x + w * t, y + h * t);
        ctx.stroke();
        ctx.restore();
    };

    // Nhãn chữ: fade theo e + lún nhẹ 8px từ dưới lên.
    mnk.label = function (x, y, text, o) {
        o = o || {};
        const e = o.e === undefined ? 1 : o.e, t = EZ(e);
        if (t <= 0) return;
        const size = o.size || 26;
        const muted = o.muted === undefined ? true : o.muted;
        ctx.save();
        ctx.globalAlpha *= t;
        ctx.font = `${o.bold ? 'bold ' : ''}${size}px ${FONT}`;
        ctx.fillStyle = o.accent ? ACCENT : (muted ? MUTED : INK);
        ctx.textAlign = o.align || 'center';
        ctx.textBaseline = 'alphabetic';
        ctx.shadowBlur = 0;
        ctx.fillText(text, x, y + 8 * (1 - t));
        ctx.restore();
    };

    // Mũi tên mảnh: thân mọc từ (x1,y1), đầu chỉ hiện khi e>0.85.
    mnk.arrow = function (x1, y1, x2, y2, o) {
        o = o || {};
        const e = o.e === undefined ? 1 : o.e, t = EZ(e);
        if (t <= 0) return;
        const col = o.accent ? ACCENT : INK;
        const cx2 = x1 + (x2 - x1) * t, cy2 = y1 + (y2 - y1) * t;
        ctx.save();
        pen(col, 2);
        if (o.dash) ctx.setLineDash([10, 8]);
        ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(cx2, cy2); ctx.stroke();
        ctx.setLineDash([]);
        if (e > 0.85) head(cx2, cy2, Math.atan2(y2 - y1, x2 - x1), col, (e - 0.85) / 0.15);
        ctx.restore();
    };

    // Leader line ĐỨT cong nhẹ (quadratic, control lệch vuông góc ~40px),
    // màu FAINT — kiểu đường dẫn chú thích trong reference.
    mnk.connect = function (x1, y1, x2, y2, o) {
        o = o || {};
        const e = o.e === undefined ? 1 : o.e, t = EZ(e);
        if (t <= 0) return;
        const mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
        const dx = x2 - x1, dy = y2 - y1;
        const len = Math.max(Math.hypot(dx, dy), 0.0001);
        const cx = mx - dy / len * 40, cy = my + dx / len * 40;
        ctx.save();
        pen(FAINT, 2);
        ctx.setLineDash([8, 8]);
        ctx.beginPath();
        const N = 26;
        for (let i = 0; i <= Math.ceil(N * t); i++) {
            const u = Math.min(i / N, t);
            const a = 1 - u;
            const px = a * a * x1 + 2 * a * u * cx + u * u * x2;
            const py = a * a * y1 + 2 * a * u * cy + u * u * y2;
            if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
        }
        ctx.stroke();
        ctx.restore();
    };

    // Công thức lớn bold INK, phần accent (substring) tô vàng; lộ dần bằng
    // clip ngang theo e; tự thu nhỏ khi tràn W-160.
    mnk.formula = function (x, y, text, o) {
        o = o || {};
        const e = o.e === undefined ? 1 : o.e, t = EZ(e);
        if (t <= 0) return;
        let size = o.size || 52;
        const align = o.align || 'center';
        ctx.save();
        ctx.font = `bold ${size}px ${FONT}`;
        let tw = ctx.measureText(text).width;
        while (tw > W - 160 && size > 18) {
            size -= 2;
            ctx.font = `bold ${size}px ${FONT}`;
            tw = ctx.measureText(text).width;
        }
        let left = align === 'center' ? x - tw / 2 : (align === 'right' ? x - tw : x);
        ctx.beginPath();
        ctx.rect(left - 6, y - size * 1.25, (tw + 12) * t, size * 1.7);
        ctx.clip();
        ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic';
        const acc = o.accent || '';
        const idx = acc ? text.indexOf(acc) : -1;
        if (idx >= 0) {
            const pre = text.slice(0, idx), suf = text.slice(idx + acc.length);
            const wPre = ctx.measureText(pre).width;
            const wAcc = ctx.measureText(acc).width;
            ctx.fillStyle = INK;
            if (pre) ctx.fillText(pre, left, y);
            ctx.fillStyle = ACCENT;
            ctx.fillText(acc, left + wPre, y);
            ctx.fillStyle = INK;
            if (suf) ctx.fillText(suf, left + wPre + wAcc, y);
        } else {
            ctx.fillStyle = INK;
            ctx.fillText(text, left, y);
        }
        ctx.restore();
    };

    // Gạch ngang phủ định (đỏ dịu) mọc từ trái.
    mnk.strike = function (x, y, w, o) {
        o = o || {};
        const e = o.e === undefined ? 1 : o.e, t = EZ(e);
        if (t <= 0) return;
        ctx.save();
        pen('rgba(248,113,113,0.9)', 3);
        ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + w * t, y); ctx.stroke();
        ctx.restore();
    };

    // So sánh hai cột: hairline FAINT dọc giữa W/2 vẽ xuống + 2 tiêu đề
    // cột 30px MUTED fade ở đỉnh mỗi nửa.
    mnk.split = function (o) {
        o = o || {};
        const e = o.e === undefined ? 1 : o.e, t = EZ(e);
        if (t <= 0) return;
        const y0 = o.y0 || 0, h = o.h || 300;
        ctx.save();
        pen(FAINT, 1);
        ctx.beginPath();
        ctx.moveTo(W / 2, y0);
        ctx.lineTo(W / 2, y0 + h * t);
        ctx.stroke();
        const ta = seg(t, 0.3, 1);
        if (ta > 0) {
            ctx.globalAlpha *= ta;
            ctx.font = `600 30px ${FONT}`;
            ctx.fillStyle = MUTED;
            ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic';
            if (o.left) ctx.fillText(o.left, W / 4, y0 + 40);
            if (o.right) ctx.fillText(o.right, W * 0.75, y0 + 40);
        }
        ctx.restore();
    };

    // Mini-diagram nét mảnh, tâm (x,y), khung ~s×s, tự vẽ theo e.
    mnk.glyph = function (kind, x, y, s, o) {
        o = o || {};
        const e = o.e === undefined ? 1 : o.e, t = EZ(e);
        if (t <= 0) return;
        const col = o.accent ? ACCENT : INK;
        const dot = (dx, dy, r, a) => {
            ctx.save(); ctx.globalAlpha *= CL(a);
            ctx.fillStyle = col;
            ctx.beginPath(); ctx.arc(dx, dy, r, 0, Math.PI * 2); ctx.fill();
            ctx.restore();
        };
        const line = (ax, ay, bx, by, u) => {
            if (u <= 0) return;
            ctx.beginPath(); ctx.moveTo(ax, ay);
            ctx.lineTo(ax + (bx - ax) * u, ay + (by - ay) * u); ctx.stroke();
        };
        ctx.save();
        ctx.translate(x, y);
        pen(col, 2);
        if (kind === 'line_pts') {
            line(-s * 0.4, s * 0.28, s * 0.4, -s * 0.28, seg(t, 0, 0.7));
            dot(-s * 0.4, s * 0.28, 4, seg(t, 0.6, 0.8));
            dot(s * 0.4, -s * 0.28, 4, seg(t, 0.8, 1));
        } else if (kind === 'segment') {
            const u = seg(t, 0, 0.8);
            line(-s * 0.45, 0, s * 0.45, 0, u);
            const ha = seg(t, 0.8, 1);
            head(s * 0.45, 0, 0, col, ha);
            head(-s * 0.45, 0, Math.PI, col, ha);
        } else if (kind === 'circle_r') {
            const r = s * 0.42;
            ctx.beginPath();
            ctx.arc(0, 0, r, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * seg(t, 0, 0.7));
            ctx.stroke();
            line(0, 0, r * 0.94, 0, seg(t, 0.65, 1));
            dot(0, 0, 3.5, seg(t, 0.6, 0.85));
        } else if (kind === 'right_angle') {
            const a = s * 0.38;
            line(-a, -a, -a, a, seg(t, 0, 0.5));            // cạnh đứng
            line(-a, a, a, a, seg(t, 0.4, 0.9));            // cạnh ngang
            const q = s * 0.16, qa = seg(t, 0.85, 1);
            if (qa > 0) {
                ctx.save(); ctx.globalAlpha *= qa;
                ctx.beginPath();
                ctx.moveTo(-a + q, a); ctx.lineTo(-a + q, a - q); ctx.lineTo(-a, a - q);
                ctx.stroke(); ctx.restore();
            }
        } else if (kind === 'axes') {
            const a = s * 0.4;
            line(-a, a * 0.8, a, a * 0.8, seg(t, 0, 0.5));   // trục x
            line(-a * 0.8, a, -a * 0.8, -a, seg(t, 0.35, 0.85));  // trục y
            const ha = seg(t, 0.85, 1);
            head(a, a * 0.8, 0, col, ha);
            head(-a * 0.8, -a, -Math.PI / 2, col, ha);
        } else if (kind === 'dots_curve') {
            const pts = [
                [-0.42, 0.30], [-0.25, 0.05], [-0.08, 0.22],
                [0.10, -0.12], [0.27, 0.02], [0.42, -0.30],
            ].map(p => [p[0] * s, p[1] * s]);
            for (let i = 0; i < pts.length; i++) {
                dot(pts[i][0], pts[i][1], 3.5, seg(t, i * 0.08, i * 0.08 + 0.15));
            }
            const cu = seg(t, 0.5, 1);
            if (cu > 0) {
                ctx.save();
                ctx.beginPath();
                ctx.rect(-s * 0.5, -s * 0.55, s * cu, s * 1.1);
                ctx.clip();
                ctx.beginPath();
                ctx.moveTo(pts[0][0], pts[0][1]);
                for (let i = 1; i < pts.length - 1; i++) {
                    const mx = (pts[i][0] + pts[i + 1][0]) / 2;
                    const my = (pts[i][1] + pts[i + 1][1]) / 2;
                    ctx.quadraticCurveTo(pts[i][0], pts[i][1], mx, my);
                }
                ctx.quadraticCurveTo(
                    pts[pts.length - 1][0], pts[pts.length - 1][1],
                    pts[pts.length - 1][0], pts[pts.length - 1][1]);
                ctx.stroke();
                ctx.restore();
            }
        } else if (kind === 'wave') {
            ctx.beginPath();
            const wN = 40, span = s * 0.9;
            const lim = Math.ceil(wN * t);
            for (let i = 0; i <= lim; i++) {
                const u = Math.min(i / wN, t);
                const px = -span / 2 + span * u;
                const py = -Math.sin(u * Math.PI * 2) * s * 0.28;
                if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
            }
            ctx.stroke();
        } else if (kind === 'infinity') {
            ctx.globalAlpha *= t;
            ctx.font = `bold ${Math.round(s * 0.5)}px ${FONT}`;
            ctx.fillStyle = col;
            ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
            ctx.fillText('∞', 0, 0);
        } else if (kind === 'parallel') {
            line(-s * 0.42, -s * 0.18, s * 0.42, -s * 0.18, seg(t, 0, 0.5));
            line(-s * 0.42, s * 0.18, s * 0.42, s * 0.18, seg(t, 0.3, 0.8));
            dot(s * 0.1, -s * 0.18, 4.5, seg(t, 0.75, 1));
        } else if (kind === 'bars') {
            // cột equalizer (nén nhạc / dữ liệu / thống kê)
            const hs = [0.55, 0.28, 0.14, 0.22, 0.34, 0.24, 0.46];
            const bw = s * 0.07, gap = s * 0.13, x0 = -gap * 3;
            for (let i = 0; i < hs.length; i++) {
                const u = seg(t, i * 0.09, i * 0.09 + 0.35);
                if (u <= 0) continue;
                const bh = s * hs[i] * u;
                ctx.fillStyle = col;
                ctx.fillRect(x0 + i * gap - bw / 2, s * 0.3 - bh, bw, bh);
            }
        } else if (kind === 'ecg') {
            // nhịp tim / tín hiệu (y tế, sóng xung)
            const span = s * 0.95, x0 = -span / 2;
            const beat = u => {
                const p = (u * 3) % 1;   // 3 nhịp trên chiều ngang
                if (p < 0.62 || p > 0.86) return 0;
                const q = (p - 0.62) / 0.24;
                return q < 0.35 ? -q / 0.35 * 0.32
                    : q < 0.7 ? (-0.32 + (q - 0.35) / 0.35 * 0.42)
                        : (0.1 - (q - 0.7) / 0.3 * 0.1);
            };
            ctx.beginPath();
            const N = 90, lim = Math.ceil(N * t);
            for (let i = 0; i <= lim; i++) {
                const u = Math.min(i / N, t);
                const px = x0 + span * u, py = beat(u) * s;
                if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
            }
            ctx.stroke();
        } else if (kind === 'network') {
            // mạng: nút giữa + vệ tinh nối tia (di động, đồ thị, liên kết)
            const R = s * 0.42;
            const sats = [[-0.9, -0.35], [-0.55, 0.55], [0.5, -0.6],
                          [0.95, 0.1], [0.55, 0.62], [-1.0, 0.15]];
            for (let i = 0; i < sats.length; i++) {
                const sx = sats[i][0] * R, sy = sats[i][1] * R;
                line(0, 0, sx, sy, seg(t, 0.15 + i * 0.06, 0.5 + i * 0.06));
                dot(sx, sy, 3.5, seg(t, 0.45 + i * 0.06, 0.7 + i * 0.06));
            }
            dot(0, 0, 6, seg(t, 0, 0.3));
        } else if (kind === 'check') {
            // dấu ✓ nét vẽ dần (đạt / đúng / đã kiểm)
            line(-s * 0.3, s * 0.02, -s * 0.08, s * 0.24, seg(t, 0, 0.45));
            line(-s * 0.08, s * 0.24, s * 0.32, -s * 0.22, seg(t, 0.4, 1));
        } else if (kind === 'clock') {
            // đồng hồ: vòng + 2 kim (thời gian, chu kỳ, lịch sử)
            const r = s * 0.4;
            ctx.beginPath();
            ctx.arc(0, 0, r, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * seg(t, 0, 0.65));
            ctx.stroke();
            line(0, 0, 0, -r * 0.62, seg(t, 0.6, 0.85));
            line(0, 0, r * 0.42, r * 0.1, seg(t, 0.75, 1));
            dot(0, 0, 3, seg(t, 0.55, 0.75));
        }
        ctx.restore();
    };

    // Quầng ACCENT thở liên tục theo time — giữ cảnh đã vẽ xong "còn sống".
    mnk.pulse = function (x, y, r) {
        const a = 0.095 + 0.045 * Math.sin(time * 1.6);
        ctx.save();
        const g = ctx.createRadialGradient(x, y, 0, x, y, Math.max(r, 1));
        g.addColorStop(0, `rgba(250,204,21,${a.toFixed(3)})`);
        g.addColorStop(1, 'rgba(250,204,21,0)');
        ctx.fillStyle = g;
        ctx.beginPath(); ctx.arc(x, y, Math.max(r, 1), 0, Math.PI * 2); ctx.fill();
        ctx.restore();
    };

    // CHỐNG BỊA HÀM: model hay gọi nhầm hàm của bộ ui.* (mnk.glass, mnk.chip,
    // mnk.kpi...) — TypeError một phát là chết cả sơ đồ. Alias về hàm gần
    // nghĩa nhất; tên hoàn toàn lạ → no-op có cảnh báo, phần còn lại vẫn vẽ.
    const MNK_ALIAS = {
        glass: 'box', card: 'box', panel: 'box',
        chip: 'label', badge: 'label', text: 'label', title: 'label',
        kpi: 'formula', big: 'formula',
        divider: 'strike', line: 'arrow', bar: 'arrow',
        icon: 'glyph', dot: 'pulse', ring: 'pulse',
    };
    return new Proxy(mnk, {
        get(target, prop) {
            if (prop in target) return target[prop];
            const alias = MNK_ALIAS[prop];
            if (alias && alias in target) return target[alias];
            if (typeof prop === 'string') {
                process.stderr.write(`[mnk] unknown fn '${prop}' -> no-op\n`);
                return function () {};
            }
            return undefined;
        },
    });
}

function easeOut(t) { return 1 - Math.pow(1 - t, 3); }

function easeOutBack(x) {

    const c1 = 1.70158;

    const c3 = c1 + 1;

    return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2);

}

// ── Word Highlight Helpers ───────────────────────────────────────

function normalizeWord(w) {

    return String(w).toLowerCase().replace(/[.,;:!?"'()«»]/g, '').replace(/[.,]/g, '');

}

/** Find the word currently being spoken at currentTime across all visible steps */

function getActiveWord(currentTime) {

    for (const ts of timing.steps) {

        if (!ts.words || !ts.words.length) continue;

        for (const wb of ts.words) {

            if (currentTime >= wb.start && currentTime < wb.end) {

                return { norm: wb.norm, word: wb.word, stepId: ts.id };

            }

        }

    }

    return null;

}

/**

 * Draw a highlight glow box around a canvas region.

 * type: 'box' (rounded rect glow) | 'underline'

 */

function drawHighlightBox(x, y, w, h, color) {

    ctx.save();

    ctx.globalAlpha = 0.35;

    ctx.fillStyle = color || 'rgba(255,215,0,0.4)';

    ctx.shadowColor = color || '#FFD700';

    ctx.shadowBlur = 18;

    roundRect(x - 8, y - 4, w + 16, h + 8, 10);

    ctx.fill();

    ctx.globalAlpha = 1;

    ctx.strokeStyle = color || '#FFD700';

    ctx.lineWidth = 2.5;

    ctx.shadowBlur = 0;

    roundRect(x - 8, y - 4, w + 16, h + 8, 10);

    ctx.stroke();

    ctx.restore();

}

// ── Color & Style resolvers ─────────────────────────────────────

const COLORS = {

    title: () => T.titleColor,

    text: () => T.textColor,

    highlight: () => T.hlColor,

    muted: () => T.mutedColor,

    green: () => (artStyle !== 'default' && STYLE_PALETTES[artStyle]?.greenColor) ? STYLE_PALETTES[artStyle].greenColor : '#00FF88',

    red: () => (artStyle !== 'default' && STYLE_PALETTES[artStyle]?.redColor) ? STYLE_PALETTES[artStyle].redColor : '#FF6B6B',

    blue: () => (artStyle !== 'default' && STYLE_PALETTES[artStyle]?.cyanColor) ? STYLE_PALETTES[artStyle].cyanColor : '#64B5F6',

    yellow: () => (artStyle !== 'default' && STYLE_PALETTES[artStyle]?.yellowColor) ? STYLE_PALETTES[artStyle].yellowColor : '#FFD700',

    white: () => (artStyle !== 'default' && STYLE_PALETTES[artStyle]?.whiteColor) ? STYLE_PALETTES[artStyle].whiteColor : '#F0F0F0',

    cyan: () => (artStyle !== 'default' && STYLE_PALETTES[artStyle]?.cyanColor) ? STYLE_PALETTES[artStyle].cyanColor : '#22D3EE',

    orange: () => '#FFA726',

};

// rc: resolve màu theo tên palette; CHO PHÉP mã hex/rgb đi thẳng — cần cho
// video tông sáng (chữ phải mực tối #0f172a, palette không có màu tối).
function rc(name) {
    if (typeof name === 'string' && (/^#([0-9a-fA-F]{3,8})$/.test(name) || name.startsWith('rgb'))) return name;
    return (COLORS[name] || COLORS.text)();
}

const BOX_STYLES = {

    equation: () => ({ bg: T.eqBg, border: T.eqBorder, glow: false }),

    result:   () => ({ bg: T.resultBg, border: T.resultBorder, glow: false }), // removed glow to fix glare

    tip:      () => ({ bg: T.tipBg, border: T.tipBorder, glow: false }),

    subtle:   () => ({ bg: T.cardBg, border: T.cardBorder, glow: false }),

};

// ── Measure text height (for dynamic box) ───────────────────────

function measureTextHeight(el) {

    if (el.type === 'math_calc') {

        const fs = el.fontSize || 48;

        if (el.op === ':') {

            const leftLines = 1 + (el.intermediates ? el.intermediates.length : 0);

            return Math.max(leftLines, 2) * (fs * 1.3) + 40;

        } else {

            let lines = (el.operands || []).length;

            if (el.intermediates) lines += el.intermediates.length;

            if (el.result || el.result_partial !== undefined) lines += 1;

            let extraPad = 40; // 1 separator

            if (el.intermediates && el.intermediates.length > 0 && (el.result || el.result_partial !== undefined)) {

                extraPad += 28; // 2 separators

            }

            return lines * (fs * 1.3) + extraPad;

        }

    }

    const fs = el.fontSize || 40;

    const font = `${el.bold ? 'bold ' : ''}${fs}px ${T.font}`;

    const contentWFixed = W - MX * 2 - 60;

    if (el.type === 'list') {

        const bullet = el.bullet || '•';

        ctx.font = font;

        const bw = ctx.measureText(bullet + ' ').width;

        let totalH = 0;

        for (const item of (el.items || [])) {

            const wrapped = wrapText(item, contentWFixed - bw, font);

            totalH += wrapped.length * fs * 1.4 + 10;

        }

        return totalH;

    }

    if (el.type === 'timeline') {

        const items = el.items || [];

        const isHoriz = true; // render timeline ngang cho mọi tỷ lệ màn hình

        if (isHoriz) {

            const itemW = (W - MX * 2 - 60) / Math.max(1, items.length);

            let maxH = 0;

            ctx.font = font;

            for (const item of items) {

                let lineH = wrapText(item.event || '', itemW - 20, font).length * fs * 1.4;

                maxH = Math.max(maxH, lineH);

            }

            return maxH + fs + 80;

        } else {

            const lineX = MX + 40;

            let totalH = 0;

            ctx.font = font;

            for (const item of items) {

                totalH += fs * 1.4 + 10;

                totalH += wrapText(item.event || '', W - lineX - 30 - MX - 60, font).length * fs * 1.4;

                totalH += 30;

            }

            return totalH;

        }

    }

    const rawLines = (el.text || '').split('\n');

    let totalH = 0;

    for (const raw of rawLines) {

        const wrapped = wrapText(raw, contentWFixed, font);

        totalH += wrapped.length * fs * 1.4;

    }

    return totalH;

}

// ── Auto-layout element renderer ────────────────────────────────

// Returns height consumed

// stepProgress: 0.0–1.0, how far through this step's duration we are

function renderElementAtY(el, cursorY, stepProgress) {

    stepProgress = stepProgress ?? 1.0;  // default fully revealed

    const contentW = W - MX * 2;

    switch (el.type) {

        case 'text': {

            const fs = el.fontSize || 40;

            const font = `${el.bold ? 'bold ' : ''}${fs}px ${T.font}`;

            ctx.font = font;

            ctx.fillStyle = rc(el.color);

            const align = el.align || 'left';

            ctx.textAlign = align; ctx.textBaseline = 'top';

            const coords = getElementCoords(el, cursorY);

            let rawText = el.text || '';

            let anim = el.animation;

            if (!anim || anim === 'typewriter') {

                anim = (rawText.length % 2 === 0) ? 'slide_in_left' : 'slide_up';

            }

            const fastP = Math.min(stepProgress * 4.0, 1.0);

            let offsetX = 0, offsetY = 0;

            if (anim === 'slide_in_left' && stepProgress < 1.0) {

                offsetX = -40 * (1 - easeOutBack(fastP));

            } else if (anim === 'slide_up' && stepProgress < 1.0) {

                offsetY = 30 * (1 - easeOutBack(fastP));

            }

            ctx.save();

            if (offsetX !== 0 || offsetY !== 0) {

                ctx.translate(offsetX, offsetY);

            }

            const rawLines = rawText.split('\n');

            let totalH = 0;

            const contentWFixed = W - MX * 2 - 60;

            for (const raw of rawLines) {

                const wrapped = wrapText(raw, contentWFixed, font);

                for (const line of wrapped) {

                    const tx = coords.isAbsolute ? coords.x : (align === 'center' ? W / 2 : align === 'right' ? W - MX : MX);

                    drawRichMathText(ctx, line, tx, coords.y + totalH, fs, rc(el.color), align, el.bold, 'top');

                    totalH += fs * 1.4;

                }

            }

            ctx.restore();

            ctx.textAlign = 'left';

            return coords.isAbsolute ? 0 : totalH + 6;

        }

        case 'list': {

            const fs = el.fontSize || 40;

            const bold = el.bold !== false; // default bold

            const font = `${bold ? 'bold ' : ''}${fs}px ${T.font}`;

            ctx.font = font;

            const bullet = el.bullet || '•';

            const align = el.align || 'center';

            const items = el.items || [];

            const n = items.length;

            const lineGap = Math.round(fs * 0.42);   // vertical gap between pills

            const padX = Math.round(fs * 0.6);        // horizontal padding inside pill

            const padY = Math.round(fs * 0.42);       // vertical padding — taller pills

            // Cap max pill width at 65% of canvas to avoid full-width stretch

            const maxPillW = Math.min(W - MX * 2, Math.round(W * 0.65));

            // Pre-measure all items → use UNIFORM width = widest item (aligned stack)

            const measuredW = items.map(item => measureMathAwareText(bullet + '  ' + item, font));

            const uniformW = Math.min(Math.max(...measuredW, 0) + padX * 2, maxPillW);

            const pillData = items.map(item => ({ item, pillW: uniformW }));

            const coords = getElementCoords(el, cursorY);

            let pillX = coords.x - uniformW / 2;

            if (!coords.isAbsolute) {

                pillX = (align === 'center') ? (W / 2 - uniformW / 2) : MX;

            }

            let totalH = 0;

            for (let j = 0; j < n; j++) {

                const itemStart = j / Math.max(n, 1);

                const itemProg = Math.max(0, Math.min((stepProgress - itemStart) * n * 2, 1.0));

                const { item, pillW } = pillData[j];

                const pillH = fs + padY * 2;

                const pillY = coords.y + totalH;

                if (itemProg > 0) {

                    ctx.save();

                    const alpha = easeOut(itemProg);

                    const slideY = 18 * (1 - easeOutBack(itemProg));

                    ctx.globalAlpha = alpha;

                    ctx.translate(0, slideY);

                    // Pill background

                    if (global.glassEffect) {
                        ctx.fillStyle = 'rgba(255,255,255,0.06)';
                        ctx.strokeStyle = 'rgba(255,255,255,0.22)';
                    } else {
                        ctx.fillStyle = rc(el.color) === rc('text') ? 'rgba(99,102,241,0.18)' : 'rgba(99,102,241,0.12)';
                        ctx.strokeStyle = rc(el.color || 'highlight');
                    }

                    ctx.lineWidth = 2;

                    if (global.glassEffect) {
                        ctx.shadowColor = 'rgba(0, 0, 0, 0.25)';
                        ctx.shadowBlur = 12;
                        ctx.shadowOffsetY = 4;
                    }

                    ctx.beginPath();

                    if (ctx.roundRect) ctx.roundRect(pillX, pillY, pillW, pillH, Math.min(pillH / 2, 18));

                    else ctx.rect(pillX, pillY, pillW, pillH);

                    ctx.fill();

                    // Clear shadow for stroke and text
                    ctx.shadowColor = 'rgba(0,0,0,0)';
                    ctx.shadowBlur = 0;
                    ctx.shadowOffsetY = 0;

                    ctx.stroke();

                    // Glassmorphism: frosted top sheen on pill

                    if (global.glassEffect) {

                        ctx.save();

                        ctx.beginPath();

                        if (ctx.roundRect) ctx.roundRect(pillX, pillY, pillW, pillH, Math.min(pillH / 2, 18));

                        else ctx.rect(pillX, pillY, pillW, pillH);

                        ctx.clip();

                        const gs = ctx.createLinearGradient(0, pillY, 0, pillY + pillH);

                        gs.addColorStop(0, 'rgba(255,255,255,0.20)');

                        gs.addColorStop(0.45, 'rgba(255,255,255,0.04)');

                        gs.addColorStop(1, 'rgba(255,255,255,0.0)');

                        ctx.fillStyle = gs;

                        ctx.fillRect(pillX, pillY, pillW, pillH);

                        ctx.strokeStyle = 'rgba(255,255,255,0.45)';

                        ctx.lineWidth = 1.2;

                        ctx.beginPath();

                        ctx.moveTo(pillX + pillH / 2, pillY + 1.2);

                        ctx.lineTo(pillX + pillW - pillH / 2, pillY + 1.2);

                        ctx.stroke();

                        ctx.restore();

                    }

                    // Text inside pill

                    ctx.fillStyle = rc(el.color || 'text');

                    ctx.font = font;

                    ctx.textAlign = 'left';

                    ctx.textBaseline = 'middle';

                    drawRichMathText(ctx, bullet + '  ' + item, pillX + padX, pillY + pillH / 2, fs, rc(el.color || 'text'), 'left', bold, 'middle');

                    ctx.restore();

                }

                totalH += pillH + lineGap;

            }

            return coords.isAbsolute ? 0 : totalH + 4;

        }

        case 'timeline': {

            const fs = el.fontSize || 32, font = `${fs}px ${T.font}`, boldFont = `bold ${fs+4}px ${T.font}`;

            ctx.fillStyle = rc(el.color);

            ctx.strokeStyle = rc(el.color);

            ctx.lineWidth = 4;

            const items = el.items || [];

            const isHoriz = true; // render timeline ngang cho mọi tỷ lệ màn hình

            const n = items.length;

            if (isHoriz) {

                const lineY = cursorY + fs + 20;

                // Draw growing horizontal line

                const lineProg = Math.min(stepProgress * 2.0, 1.0); // line draws first 50%

                if (lineProg > 0) {

                    ctx.save(); ctx.globalAlpha = easeOut(lineProg);

                    const lineW = (W - MX * 2) * lineProg;

                    ctx.beginPath(); ctx.moveTo(MX, lineY); ctx.lineTo(MX + lineW, lineY); ctx.stroke();

                    ctx.restore();

                }

                const itemW = (W - MX * 2) / Math.max(1, n);

                let maxH = 0;

                ctx.textAlign = 'center'; ctx.textBaseline = 'top';

                for (let i = 0; i < n; i++) {

                    const item = items[i];

                    const itemStart = i / Math.max(n, 1);

                    const itemProg = Math.max(0, Math.min((stepProgress - itemStart) * n * 2, 1.0));

                    const x = n === 1 ? W/2 : MX + itemW/2 + i * itemW;

                    let lineH = 0;

                    ctx.font = font;

                    const lines = wrapText(item.event || '', itemW - 20, font);

                    lineH = lines.length * fs * 1.4;

                    maxH = Math.max(maxH, lineY + 20 + lineH - cursorY);

                    if (itemProg > 0) {

                        ctx.save();

                        ctx.globalAlpha = easeOut(itemProg);

                        const offsetY = 20 * (1 - easeOutBack(itemProg));

                        ctx.translate(0, offsetY);

                        ctx.beginPath(); ctx.arc(x, lineY, 8, 0, Math.PI*2); ctx.fill();

                        ctx.font = boldFont;

                        ctx.fillText(item.year || '', x, cursorY);

                        ctx.font = font;

                        let textY = lineY + 20;

                        for (const line of lines) {

                            ctx.fillText(line, x, textY);

                            textY += fs * 1.4;

                        }

                        ctx.restore();

                    }

                }

                return maxH + 40;

            } else {

                const lineX = MX + 40;

                let curY = cursorY;

                ctx.textAlign = 'left'; ctx.textBaseline = 'top';

                // For vertical, measure total height to draw the line

                let totalH = 0;

                const itemHeights = [];

                for (let i = 0; i < n; i++) {

                    const item = items[i];

                    ctx.font = font;

                    const lines = wrapText(item.event || '', W - lineX - 30 - MX, font);

                    const h = (fs * 1.4 + 10) + (lines.length * fs * 1.4) + 30;

                    itemHeights.push(h);

                    totalH += h;

                }

                // Draw vertical line growing

                const lineProg = Math.min(stepProgress * 2.0, 1.0);

                if (lineProg > 0 && n > 0) {

                    ctx.save(); ctx.globalAlpha = easeOut(lineProg);

                    const drawH = (totalH - 30 - fs * 1.4) * lineProg;

                    ctx.beginPath(); ctx.moveTo(lineX, cursorY + 20); ctx.lineTo(lineX, cursorY + 20 + drawH); ctx.stroke();

                    ctx.restore();

                }

                for (let i = 0; i < n; i++) {

                    const item = items[i];

                    const itemStart = i / Math.max(n, 1);

                    const itemProg = Math.max(0, Math.min((stepProgress - itemStart) * n * 2, 1.0));

                    ctx.font = font;

                    const lines = wrapText(item.event || '', W - lineX - 30 - MX, font);

                    if (itemProg > 0) {

                        ctx.save();

                        ctx.globalAlpha = easeOut(itemProg);

                        const offsetX = -20 * (1 - easeOutBack(itemProg)); // slide in left

                        ctx.translate(offsetX, 0);

                        ctx.beginPath(); ctx.arc(lineX, curY + 20, 8, 0, Math.PI*2); ctx.fill();

                        ctx.font = boldFont;

                        ctx.fillText(item.year || '', lineX + 30, curY);

                        let textY = curY + fs * 1.4 + 10;

                        ctx.font = font;

                        for (const line of lines) {

                            ctx.fillText(line, lineX + 30, textY);

                            textY += fs * 1.4;

                        }

                        ctx.restore();

                    }

                    curY += itemHeights[i];

                }

                return totalH;

            }

        }

        case 'custom_js': {

            let h = el.height || 100;

            const coords = getElementCoords(el, cursorY);

            const scaleFactor = (el.fontSize || 40) / 40;

            const scaledH = h * scaleFactor;

            if (el.code) {

                try {

                    if (!el.template || el.template !== el.trusted_template) {
                        throw new Error('custom_js không có template tin cậy');
                    }

                    // Provide the actual video timeline frame time to the custom_js code block

                    const timeSecs = currentFrameTime;

                    // Create a smart Proxy for ctx to remap colors and soften shadows for light styles

                    const isLightStyle = ['watercolor', 'inkwash', 'pastel', 'sketch', 'sketchnote', 'aurora'].includes(artStyle);

                    const customCtx = new Proxy(ctx, {

                        get(target, prop) {
                            if (prop === 'drawImage') {
                                return function(img, ...args) {
                                    if (isLightStyle && img && typeof img.src === 'string' && img.src.toLowerCase().includes('logo') && !img.src.toLowerCase().includes('logo_tubecreate') && !img.src.toLowerCase().includes('tubecreate')) {
                                        target.save();
                                        target.fillStyle = 'rgba(15, 23, 42, 0.95)';
                                        target.strokeStyle = 'rgba(255, 255, 255, 0.1)';
                                        target.lineWidth = 2;
                                        target.beginPath();
                                        let dx = args[0], dy = args[1], dw = img.width || 120, dh = img.height || 120;
                                        if (args.length === 4 || args.length === 5) {
                                            dw = args[2];
                                            dh = args[3];
                                        } else if (args.length >= 8) {
                                            dx = args[4];
                                            dy = args[5];
                                            dw = args[6];
                                            dh = args[7];
                                        }
                                        let cx = dx + dw/2;
                                        let cy = dy + dh/2;
                                        let r = Math.max(dw, dh) * 0.65;
                                        target.arc(cx, cy, r, 0, Math.PI * 2);
                                        target.fill();
                                        target.stroke();
                                        target.restore();
                                    }
                                    return target.drawImage.apply(target, [img, ...args]);
                                };
                            }
                            if (prop === 'fill') {
                                return function(...args) {
                                    // Light styles: suppress neon glow on fill (looks harsh on light bg)
                                    // liquidglass: keep shadow glow for neon circle effect
                                    if (isLightStyle) {
                                        const oldBlur = target.shadowBlur;
                                        const oldColor = target.shadowColor;
                                        const oldOffsetX = target.shadowOffsetX;
                                        const oldOffsetY = target.shadowOffsetY;
                                        target.shadowBlur = 0;
                                        target.shadowColor = 'rgba(0,0,0,0)';
                                        target.shadowOffsetX = 0;
                                        target.shadowOffsetY = 0;
                                        const res = target.fill.apply(target, args);
                                        target.shadowBlur = oldBlur;
                                        target.shadowColor = oldColor;
                                        target.shadowOffsetX = oldOffsetX;
                                        target.shadowOffsetY = oldOffsetY;
                                        return res;
                                    }
                                    return target.fill.apply(target, args);
                                };
                            }
                            const val = target[prop];
                            if (typeof val === 'function') {
                                return val.bind(target);
                            }
                            return val;
                        },

                        set(target, prop, value) {

                            const toGrayscale = (colorStr) => {
                                if (typeof colorStr !== 'string') return colorStr;
                                const trimmed = colorStr.trim();
                                const lower = trimmed.toLowerCase();
                                if (lower.startsWith('hsl')) {
                                    return trimmed.replace(/hsl(a?)\(\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)%?\s*,/i, 'hsl$1($2, 0%,');
                                }
                                const rgbMatch = trimmed.match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*([\d.]+))?\s*\)/i);
                                if (rgbMatch) {
                                    const r = parseInt(rgbMatch[1]);
                                    const g = parseInt(rgbMatch[2]);
                                    const b = parseInt(rgbMatch[3]);
                                    const gray = Math.round(0.299 * r + 0.587 * g + 0.114 * b);
                                    if (rgbMatch[4] !== undefined) {
                                        return `rgba(${gray}, ${gray}, ${gray}, ${rgbMatch[4]})`;
                                    } else {
                                        return `rgb(${gray}, ${gray}, ${gray})`;
                                    }
                                }
                                if (trimmed.startsWith('#')) {
                                    const hex = trimmed.slice(1);
                                    let r = 255, g = 255, b = 255, a = '';
                                    if (hex.length === 3 || hex.length === 4) {
                                        r = parseInt(hex[0] + hex[0], 16);
                                        g = parseInt(hex[1] + hex[1], 16);
                                        b = parseInt(hex[2] + hex[2], 16);
                                        if (hex.length === 4) a = hex[3] + hex[3];
                                    } else if (hex.length === 6 || hex.length === 8) {
                                        r = parseInt(hex.slice(0, 2), 16);
                                        g = parseInt(hex.slice(2, 4), 16);
                                        b = parseInt(hex.slice(4, 6), 16);
                                        if (hex.length === 8) a = hex.slice(6, 8);
                                    }
                                    const gray = Math.round(0.299 * r + 0.587 * g + 0.114 * b);
                                    const grayHex = gray.toString(16).padStart(2, '0');
                                    return `#${grayHex}${grayHex}${grayHex}${a}`;
                                }
                                const namedColors = {
                                    'red': '#111827', 'green': '#374151', 'blue': '#1f2937', 'yellow': '#4b5563',
                                    'cyan': '#1f2937', 'magenta': '#4b5563', 'white': '#ffffff', 'black': '#000000',
                                    'gray': '#808080', 'grey': '#808080', 'orange': '#4b5563', 'purple': '#374151',
                                    'pink': '#9ca3af', 'brown': '#374151'
                                };
                                if (namedColors[lower]) {
                                    return namedColors[lower];
                                }
                                return colorStr;
                            };

                            let newVal = value;

                            // Intercept font styling to dynamically inject our premium font family

                            if (prop === 'font' && typeof value === 'string') {
                                newVal = value.replace(/sans-serif|monospace|serif/gi, (match) => {
                                    const lower = match.toLowerCase();
                                    if (lower === 'sans-serif') return T.font;
                                    if (lower === 'monospace') return T.font;
                                    if (lower === 'serif') return T.font;
                                    return match;
                                });

                                let scaleFactor = 1.0;
                                if (artStyle === 'pixel') scaleFactor = 0.85;
                                else if (artStyle === 'cyberpunk') scaleFactor = 0.78;
                                else if (artStyle === 'cartoon') scaleFactor = 0.85;
                                else if (artStyle === 'sketch') scaleFactor = 0.85;
                                else if (artStyle === 'inkwash') scaleFactor = 0.85;
                                else if (artStyle === 'sketchnote') scaleFactor = 0.92;
                                else if (artStyle === 'watercolor') scaleFactor = 0.95;
                                else if (artStyle === 'pastel') scaleFactor = 0.95;
                                else if (artStyle === 'aurora') scaleFactor = 0.95;

                                if (scaleFactor !== 1.0) {
                                    newVal = newVal.replace(/(\d+)px/gi, (match, size) => {
                                        const scaled = Math.round(parseInt(size) * scaleFactor);
                                        return `${Math.max(9, scaled)}px`;
                                    });
                                }

                                // Local named scenes contain their own font
                                // strings.  Keep their intended family, then
                                // append the bundled Vietnamese fallback just
                                // like normal text elements do.
                                newVal = withVietnameseFallback(newVal);

                            }

                            if (typeof value === 'string') {

                                const lowerVal = value.toLowerCase().trim();

                                // Intercept and map fill/stroke colors

                                if (prop === 'fillStyle' || prop === 'strokeStyle') {

                                    if (isLightStyle || artStyle === 'liquidglass') {

                                        // Intercept dark-slate box background and make it translucent/light

                                          const isLightColor = (val) => {
                                         if (!val) return false;
                                         const lower = val.toLowerCase().trim();
                                         if (lower === 'transparent' || lower === 'none' || lower === 'inherit' || lower === 'initial') return false;
                                         if (lower === 'text' || lower === 'title' || lower === 'muted' || lower === 'highlight' || lower === 'cyan' || lower === 'green' || lower === 'red' || lower === 'yellow' || lower === 'orange' || lower === 'blue') {
                                             return false;
                                         }
                                         let r = 255, g = 255, b = 255;
                                         if (lower.startsWith('#')) {
                                             const hex = lower.slice(1);
                                             if (hex.length === 3 || hex.length === 4) {
                                                 r = parseInt(hex[0] + hex[0], 16);
                                                 g = parseInt(hex[1] + hex[1], 16);
                                                 b = parseInt(hex[2] + hex[2], 16);
                                             } else if (hex.length === 6 || hex.length === 8) {
                                                 r = parseInt(hex.slice(0, 2), 16);
                                                 g = parseInt(hex.slice(2, 4), 16);
                                                 b = parseInt(hex.slice(4, 6), 16);
                                             } else {
                                                 return false;
                                             }
                                         } else if (lower.startsWith('rgba') || lower.startsWith('rgb')) {
                                             const match = lower.match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/);
                                             if (match) {
                                                 r = parseInt(match[1]);
                                                 g = parseInt(match[2]);
                                                 b = parseInt(match[3]);
                                             } else {
                                                 return false;
                                             }
                                         } else {
                                             const namedWhites = ['white', 'whitesmoke', 'aliceblue', 'azure', 'ghostwhite', 'honeydew', 'ivory', 'lavender', 'linen', 'snow', 'seashell', 'lightgray', 'lightgrey', 'gainsboro', 'silver'];
                                             if (namedWhites.includes(lower)) return true;
                                             return false;
                                         }
                                         return (r + g + b) / 3 > 195;
                                     };

                                     const isDarkColor = (val) => {

                                        if (!val) return false;

                                        const lower = val.toLowerCase().trim();

                                        if (lower === '#0f172a' || lower === '#0b0f19' || lower === '#1a1a2e' || lower === '#202035' || lower === '#1a1a35' || lower === '#141423' || lower === '#1a3528' || lower === '#0e1111') {

                                            return true;

                                        }

                                        if (lower.startsWith('rgba') || lower.startsWith('rgb')) {

                                            const match = lower.match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/);

                                            if (match) {

                                                const r = parseInt(match[1]), g = parseInt(match[2]), b = parseInt(match[3]);

                                                return r < 85 && g < 85 && b < 85;

                                            }

                                        }

                                        return false;

                                    };

                                    if (isDarkColor(lowerVal)) {

                                        if (artStyle === 'watercolor') newVal = 'rgba(44, 76, 56, 0.08)'; // sage green tint

                                        else if (artStyle === 'inkwash') newVal = 'rgba(0, 0, 0, 0.05)'; // gray sumi wash

                                        else if (artStyle === 'pastel') newVal = 'rgba(92, 103, 125, 0.06)'; // soft lavender tint
                                        else if (artStyle === 'aurora') newVal = 'rgba(255, 255, 255, 0.78)'; // white glass card

                                        else if (artStyle === 'sketch') newVal = 'rgba(255, 255, 255, 0.9)'; // white paper fill

                                        else if (artStyle === 'sketchnote') newVal = 'rgba(255, 255, 255, 0.95)'; // clean white notebook paper fill

                                        else if (artStyle === 'liquidglass') {
                                             // Deep dark-glass fill: preserve circle/node backgrounds as visible
                                             // dark surfaces so icons render clearly against them.
                                             // High-opacity fills (circle backgrounds) keep dark glass base.
                                             // Low-opacity fills (overlays) get subtle white glass tint.
                                             const ma = lowerVal.match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*([\d.]+))?\)/);
                                             const origAlpha = ma && ma[4] !== undefined ? parseFloat(ma[4]) : 1.0;
                                             if (origAlpha > 0.5) {
                                                 // Solid node/circle background — keep dark + glass readable
                                                 newVal = 'rgba(8,14,32,0.72)';
                                             } else {
                                                 // Overlay/tint — use subtle frosted white
                                                 const a = Math.min(0.18, origAlpha);
                                                 newVal = `rgba(255,255,255,${a})`;
                                             }

                                         }

                                    }

                                        // Intercept white text inside nodes and make it dark text

                                        else if (lowerVal === '#ccc' || lowerVal === '#bbb' || lowerVal === '#aaa' || lowerVal === '#999' || lowerVal === '#888' || lowerVal === '#d0d0ff' || lowerVal === '#e0e0ff' || lowerVal === '#c0c0c0' || lowerVal === '#d3d3d3' || lowerVal.includes('rgba(204,204,204') || lowerVal.includes('rgba(187,187,187') || lowerVal.includes('rgba(170,170,170') || lowerVal.includes('rgba(204, 204, 204') || lowerVal.includes('rgba(187, 187, 187') || lowerVal.includes('rgba(170, 170, 170')) {
                                            newVal = rc('muted');
                                        }
                                        else if (isLightStyle && isLightColor(lowerVal)) {
                                            let alpha = 1.0;
                                            const rgbaMatch = lowerVal.match(/rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\)/);
                                            if (rgbaMatch) {
                                                alpha = parseFloat(rgbaMatch[4]);
                                            } else if (lowerVal.startsWith('#')) {
                                                const hex = lowerVal.slice(1);
                                                if (hex.length === 8) {
                                                    alpha = parseInt(hex.slice(6, 8), 16) / 255;
                                                } else if (hex.length === 4) {
                                                    alpha = (parseInt(hex.slice(3, 4), 16) * 17) / 255;
                                                }
                                            }
                                            alpha = Math.round(alpha * 1000) / 1000;

                                            let r = 255, g = 255, b = 255;
                                            if (lowerVal.startsWith('#')) {
                                                const hex = lowerVal.slice(1);
                                                if (hex.length >= 6) {
                                                    r = parseInt(hex.slice(0, 2), 16);
                                                    g = parseInt(hex.slice(2, 4), 16);
                                                    b = parseInt(hex.slice(4, 6), 16);
                                                } else if (hex.length >= 3) {
                                                    r = parseInt(hex[0]+hex[0], 16);
                                                    g = parseInt(hex[1]+hex[1], 16);
                                                    b = parseInt(hex[2]+hex[2], 16);
                                                }
                                            } else if (lowerVal.startsWith('rgba') || lowerVal.startsWith('rgb')) {
                                                const match = lowerVal.match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/);
                                                if (match) {
                                                    r = parseInt(match[1]);
                                                    g = parseInt(match[2]);
                                                    b = parseInt(match[3]);
                                                }
                                            }
                                            const avg = (r + g + b) / 3;

                                            if (alpha < 1.0) {
                                                newVal = `rgba(30, 41, 59, ${alpha})`;
                                            } else {
                                                newVal = avg > 245 ? rc('text') : rc('muted');
                                            }
                                        }

                                    }// Make sure neon standard names mapped properly

                                    if (lowerVal === 'cyan' || lowerVal === '#22d3ee' || lowerVal === '#00ffff') newVal = rc('cyan');

                                    else if (lowerVal === 'yellow' || lowerVal === '#ffd700' || lowerVal === '#efff14') newVal = rc('yellow');

                                    else if (lowerVal === 'green' || lowerVal === '#22c55e' || lowerVal === '#39ff14') newVal = rc('green');

                                    else if (lowerVal === 'red' || lowerVal === '#ef4444' || lowerVal === '#ff073a') newVal = rc('red');

                                    if (artStyle === 'sketch') {
                                        newVal = toGrayscale(newVal);
                                    }

                                }

                                // Intercept shadowColor and disable/soften glow on light backgrounds

                                if (prop === 'shadowColor') {

                                    if (isLightStyle) {

                                        newVal = 'rgba(0, 0, 0, 0.08)'; // soft warm gray shadow instead of neon glow

                                    } else {

                                        // On dark cyberpunk, use proper neon colors

                                        if (lowerVal === 'cyan' || lowerVal === '#22d3ee' || lowerVal === '#00ffff') newVal = rc('cyan');

                                        else if (lowerVal === 'yellow' || lowerVal === '#ffd700' || lowerVal === '#efff14') newVal = rc('yellow');

                                        else if (lowerVal === 'green' || lowerVal === '#22c55e' || lowerVal === '#39ff14') newVal = rc('green');

                                        else if (lowerVal === '#ff007f' || lowerVal === 'magenta' || lowerVal === '#ff00ff') newVal = rc('highlight');

                                    }

                                }

                            }

                            // Intercept shadowBlur to soften it on light styles

                            if (prop === 'shadowBlur') {

                                if (isLightStyle) {

                                    newVal = Math.min(newVal, 4);

                                }

                            }

                            target[prop] = newVal;

                            return true;

                        }

                    });

                    const uiKit = makeUiKit(ctx, artStyle, timeSecs, rc, global.drawEmoji);
                    const mnKit = makeMnKit(ctx, timeSecs);
                    const fn = new Function('ctx', 'W', 'H', 'MX', 'cursorY', 'stepProgress', 'time', 'el', 'T', 'rc', 'wrapText', 'drawEmoji', 'ui', 'mnk', fixInlineComments(el.code));

                    // Wrap customCtx to intercept fillText for emoji — use drawEmoji (Twemoji PNG) instead
                    // of canvas font rendering which can be blurry/invisible after ctx.restore() resets fillStyle.
                    const emojiRegex = /[\u{1F300}-\u{1FFFF}]|[\u{2600}-\u{27BF}]|[\u{2300}-\u{23FF}]/u;
                    const customCtxWithEmoji = new Proxy(customCtx, {
                        get(target, prop) {
                            if (prop === 'fillText') {
                                return function(text, x, y, maxWidth) {
                                    // Check if text is a single emoji character
                                    const trimmed = String(text || '').trim();
                                    if (trimmed.length <= 4 && emojiRegex.test(trimmed)) {
                                        // Determine font size from current ctx font (read from real ctx)
                                        const fontStr = ctx.font || '';
                                        const sizeMatch = fontStr.match(/(\d+)px/);
                                        const size = sizeMatch ? parseInt(sizeMatch[1]) : 36;
                                        // Icon Lucide premium trước (nét mảnh, ăn fillStyle hiện
                                        // tại) — emoji Twemoji chỉ khi không có icon tương ứng.
                                        const licon = global.EMOJI_TO_LUCIDE && global.EMOJI_TO_LUCIDE[trimmed];
                                        if (licon && global.drawLucide) {
                                            const fs0 = (typeof ctx.fillStyle === 'string') ? ctx.fillStyle : '';
                                            const baseline0 = ctx.textBaseline || 'alphabetic';
                                            const yOff0 = baseline0 === 'middle' ? 0 : -size * 0.35;
                                            if (global.drawLucide(ctx, licon, x, y + yOff0, size, fs0 || '#64748b')) return;
                                        }
                                        // Use drawEmoji for full-color crisp rendering (pass real ctx, not proxy)
                                        if (global.drawEmoji) {
                                            // textBaseline affects y offset — compensate for 'alphabetic' (default)
                                            const baseline = ctx.textBaseline || 'alphabetic';
                                            const yOffset = baseline === 'middle' ? 0 : (baseline === 'alphabetic' ? -size * 0.15 : 0);
                                            global.drawEmoji(ctx, trimmed, x, y + yOffset, size);
                                            return;
                                        }
                                    }
                                    // For non-emoji text, check if fillStyle has gone dark (e.g. after ctx.restore()).
                                    // Threshold 120: sum of R+G+B < 120 is considered "too dark to render visible text".
                                    // NOTE: gradient/pattern objects are INTENTIONAL (gradient headline text) —
                                    // never clobber them to white; only plain dark color strings get rescued.
                                    const fs = ctx.fillStyle;
                                    const isDarkFill =
                                        (typeof fs === 'string' && /rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/.test(fs) && (()=>{
                                            const m = fs.match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/);
                                            return m && (parseInt(m[1]) + parseInt(m[2]) + parseInt(m[3])) < 120;
                                        })());
                                    if (isDarkFill) {
                                        ctx.save();
                                        ctx.fillStyle = 'rgba(255,255,255,0.95)';
                                        ctx.textAlign = ctx.textAlign; // preserve alignment
                                        if (maxWidth !== undefined) ctx.fillText(text, x, y, maxWidth);
                                        else ctx.fillText(text, x, y);
                                        ctx.restore();
                                        return;
                                    }
                                    if (maxWidth !== undefined) ctx.fillText(text, x, y, maxWidth);
                                    else ctx.fillText(text, x, y);
                                };
                            }
                            return target[prop];
                        }
                    });

                    ctx.save();

                    if (scaleFactor !== 1.0) {

                        const centerX = W / 2;

                        const centerY = coords.y + scaledH / 2;

                        ctx.translate(centerX, centerY);

                        ctx.scale(scaleFactor, scaleFactor);

                        ctx.translate(-centerX, -centerY);

                    }

                    // restore trong finally — code AI crash giữa chừng mà bỏ
                    // restore là transform rò rỉ sang element/step sau (chrome
                    // xếp bậc thang).
                    let retH;
                    try {
                        retH = fn(customCtxWithEmoji, W, H, MX, coords.y, stepProgress, timeSecs, el, T, rc, wrapText, global.drawEmoji, uiKit, mnKit);
                    } finally {
                        ctx.restore();
                    }

                    if (typeof retH === 'number') h = retH;

                } catch (e) {

                    // A partial scene is not a successful render.  Propagate
                    // this to Python so the old MP4 stays intact and the user
                    // can see the actual failed scene instead of a blank card.
                    const detail = String(e && e.message ? e.message : e);
                    process.stderr.write(`[custom_js Error] ${detail}\n`);
                    const fatal = new Error(`custom_scene_error: ${detail}`);
                    fatal.code = 'custom_scene_error';
                    throw fatal;

                }

            }

            return coords.isAbsolute ? 0 : h * scaleFactor;

        }

        case 'box': {

            // Dynamic box: look ahead to measure content inside

            // Box itself is rendered as background; returns 0 height (text inside handles it)

            // We store box info for the render pass

            return 0; // handled by renderBoxWithContent

        }

        case 'line': {

            ctx.beginPath();

            ctx.moveTo(MX, cursorY + 5);

            ctx.lineTo(W - MX, cursorY + 5);

            ctx.strokeStyle = rc(el.color || 'muted');

            ctx.lineWidth = 2;

            if (el.dash) ctx.setLineDash([8, 4]);

            ctx.stroke(); ctx.setLineDash([]);

            return 18;

        }

        case 'image': {

            if (el.hidden) return 0;

            if (el.src && IMAGE_CACHE[el.src]) {

                  const img = IMAGE_CACHE[el.src];

                  // Fit within content width, but also cap height at 50% of canvas H

                  // This prevents 1:1 AI images from scaling too large in 16:9 landscape

                  const availW = W - MX * 2;

                  const maxH = Math.min(Math.round(availW * 0.75), Math.round(H * 0.5));

                  const ratio = Math.min(availW / img.width, maxH / img.height);

                  const iw = Math.round(img.width * ratio);

                  const ih = Math.round(img.height * ratio);

                  const coords = getElementCoords(el, cursorY);

                  let ix = coords.x - iw / 2;

                  if (!coords.isAbsolute) {

                      ix = (W - iw) / 2;

                  }

                const anim = el.animation || 'pop_in';

                let scale = 1.0;

                if (anim === 'pop_in' && stepProgress < 1.0) {

                    const p = Math.min(stepProgress * 4.0, 1.0); // Fast pop in

                    scale = 0.8 + 0.2 * easeOutBack(p);

                }

                // ── Background removal via color-keying ──

                const processedImg = removeImageBackground(img, el.src);

                ctx.save();

                if (scale !== 1.0) {

                    ctx.translate(ix + iw/2, coords.y + ih/2);

                    ctx.scale(scale, scale);

                    ctx.translate(-(ix + iw/2), -(coords.y + ih/2));

                }

                // No clipping rect — draw transparent image directly

                ctx.drawImage(processedImg, ix, coords.y, iw, ih);

                ctx.restore();

                return coords.isAbsolute ? 0 : ih + 24;

            }

            return 0;

        }

        case 'digit_row': {

            // Renders digits 0-9 in a row with even/odd coloring

            // e.g. {"type":"digit_row","even_color":"cyan","odd_color":"orange","fontSize":52}

            const drFs = el.fontSize || 52;

            const drEven = rc(el.even_color || 'cyan');

            const drOdd  = rc(el.odd_color  || 'orange');

            const digits = ['0','1','2','3','4','5','6','7','8','9'];

            const cellW  = (W - MX * 2) / digits.length;

            const rowH   = drFs + 24;

            const bgEven = drEven + '33'; // 20% alpha

            const bgOdd  = drOdd  + '33';

            ctx.font = `bold ${drFs}px ${T.font}`;

            ctx.textAlign = 'center';

            ctx.textBaseline = 'middle';

            digits.forEach((d, i) => {

                const isEven = i % 2 === 0;

                const x = MX + cellW * i;

                const cy2 = cursorY + rowH / 2;

                // Background pill

                ctx.fillStyle = isEven ? bgEven : bgOdd;

                const r = 8;

                ctx.beginPath();

                ctx.roundRect(x + 2, cursorY + 2, cellW - 4, rowH - 4, r);

                ctx.fill();

                // Border

                ctx.strokeStyle = isEven ? drEven : drOdd;

                ctx.lineWidth = 1.5;

                ctx.stroke();

                // Digit

                ctx.fillStyle = isEven ? drEven : drOdd;

                ctx.fillText(d, x + cellW / 2, cy2);

            });

            ctx.textAlign = 'left';

            return rowH + 12;

        }

        case 'icon': {

            const sz = el.size || 64;

            ctx.font = `${sz}px "Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji", "Segoe UI Symbol", ${T.font}`;

            ctx.fillStyle = rc(el.color || 'yellow');

            ctx.textAlign = 'center'; ctx.textBaseline = 'top';

            const coords = getElementCoords(el, cursorY);

            const ix = coords.isAbsolute ? coords.x : W / 2;

            ctx.fillText(el.emoji || '', ix, coords.y);

            ctx.textAlign = 'left';

            return coords.isAbsolute ? 0 : sz + 10;

        }

        case 'arrow': {

            const col = rc(el.color || 'yellow');

            const ax1 = MX + 20, ax2 = W - MX - 20, ay = cursorY + 12;

            ctx.beginPath(); ctx.moveTo(ax1, ay); ctx.lineTo(ax2, ay);

            ctx.strokeStyle = col; ctx.lineWidth = 3; ctx.stroke();

            const a = Math.atan2(0, ax2 - ax1), hl = 16;

            ctx.beginPath(); ctx.moveTo(ax2, ay);

            ctx.lineTo(ax2 - hl * Math.cos(a - 0.4), ay - hl * Math.sin(a - 0.4));

            ctx.lineTo(ax2 - hl * Math.cos(a + 0.4), ay - hl * Math.sin(a + 0.4));

            ctx.closePath(); ctx.fillStyle = col; ctx.fill();

            return 30;

        }

        // ── VISUAL ELEMENT: number_line ──────────────────────────────

        // {"type":"number_line","min":0,"max":10,"highlight":[3,7],"mark":5,"color":"cyan","fontSize":28}

        // Draws a ruler-style number line with optional highlighted points

        case 'number_line': {

            const nlMin = el.min ?? 0;

            const nlMax = el.max ?? 10;

            const nlH = 80;

            const nlY = cursorY + nlH / 2;

            const nlX1 = MX + 10, nlX2 = W - MX - 10;

            const nlRange = nlMax - nlMin || 1;

            const nlColor = rc(el.color || 'cyan');

            const nlFs = el.fontSize || 24;

            const highlights = Array.isArray(el.highlight) ? el.highlight : [];

            // Main line

            ctx.strokeStyle = nlColor + '99'; ctx.lineWidth = 3;

            ctx.beginPath(); ctx.moveTo(nlX1, nlY); ctx.lineTo(nlX2, nlY); ctx.stroke();

            // Arrow head

            ctx.beginPath(); ctx.moveTo(nlX2, nlY);

            ctx.lineTo(nlX2 - 12, nlY - 6); ctx.lineTo(nlX2 - 12, nlY + 6);

            ctx.closePath(); ctx.fillStyle = nlColor + '99'; ctx.fill();

            // Ticks and labels

            ctx.font = `${nlFs}px ${T.font}`; ctx.textAlign = 'center'; ctx.textBaseline = 'top';

            for (let v = nlMin; v <= nlMax; v++) {

                const px = nlX1 + ((v - nlMin) / nlRange) * (nlX2 - nlX1 - 20);

                const isHighlight = highlights.includes(v);

                const isMark = v === el.mark;

                if (isMark) {

                    // Big circle marker

                    ctx.beginPath(); ctx.arc(px, nlY, 14, 0, Math.PI * 2);

                    ctx.fillStyle = nlColor; ctx.fill();

                    ctx.fillStyle = '#0d0d1a'; ctx.fillText(String(v), px, nlY - nlFs/2 - 2);

                } else if (isHighlight) {

                    ctx.beginPath(); ctx.arc(px, nlY, 8, 0, Math.PI * 2);

                    ctx.fillStyle = nlColor + '99'; ctx.fill();

                } else {

                    // Tick

                    ctx.strokeStyle = nlColor + '66'; ctx.lineWidth = 1.5;

                    ctx.beginPath(); ctx.moveTo(px, nlY - 6); ctx.lineTo(px, nlY + 6); ctx.stroke();

                }

                ctx.fillStyle = isHighlight || isMark ? nlColor : nlColor + '88';

                ctx.fillText(String(v), px, nlY + 12);

            }

            ctx.textAlign = 'left';

            return nlH + nlFs + 16;

        }

        // ── VISUAL ELEMENT: comparison_bar ───────────────────────────

        // {"type":"comparison_bar","left":{"label":"A","value":7,"color":"cyan"},"right":{"label":"B","value":5,"color":"orange"}}

        // Draws two horizontal bars side by side for comparison (lớn hơn/nhỏ hơn)

        case 'comparison_bar': {

            const cb = el;

            const left  = cb.left  || { label: 'A', value: 5, color: 'cyan' };

            const right = cb.right || { label: 'B', value: 3, color: 'orange' };

            const maxVal = Math.max(left.value, right.value, 1);

            const barH = 32, rowGap = 10, labelW = 140, valW = 50;

            const barX = MX + labelW;

            const availW = W - MX * 2 - labelW - valW;

            let rowY = cursorY + 6;

            [left, right].forEach((side) => {

                const barW = Math.max((side.value / maxVal) * availW, 8);

                const col = rc(side.color || 'cyan');

                // Label on the left

                ctx.font = `bold 24px ${T.font}`; ctx.textAlign = 'right'; ctx.textBaseline = 'middle';

                ctx.fillStyle = col;

                ctx.fillText(side.label, barX - 10, rowY + barH / 2);

                // Bar background

                ctx.fillStyle = col + '22';

                roundRect(barX, rowY, availW, barH, 5); ctx.fill();

                // Bar fill

                ctx.fillStyle = col + 'BB';

                roundRect(barX, rowY, barW, barH, 5); ctx.fill();

                // Value on the right

                ctx.textAlign = 'left'; ctx.fillStyle = col;

                ctx.font = `bold 22px ${T.font}`;

                ctx.fillText(String(side.value), barX + availW + 8, rowY + barH / 2);

                rowY += barH + rowGap;

            });

            ctx.textAlign = 'left';

            return (barH + rowGap) * 2 + 12;

        }

        // ── VISUAL ELEMENT: fraction_bar ─────────────────────────────

        // {"type":"fraction_bar","numerator":3,"denominator":4,"color":"cyan","showDecimal":false}

        // Draws a visual fraction as a segmented bar

        case 'fraction_bar': {

            const fn2 = el.numerator ?? 1, fd = el.denominator ?? 4;

            const fbH = 64, fbY = cursorY + 8;

            const fbW = W - MX * 2;

            const segW = fbW / fd;

            const fbCol = rc(el.color || 'cyan');

            for (let i = 0; i < fd; i++) {

                const sx = MX + i * segW;

                const filled = i < fn2;

                ctx.fillStyle = filled ? fbCol + 'CC' : fbCol + '22';

                ctx.beginPath(); ctx.roundRect(sx + 2, fbY, segW - 4, fbH, 4); ctx.fill();

                ctx.strokeStyle = fbCol + '88'; ctx.lineWidth = 1.5;

                ctx.stroke();

            }

            // Fraction label centered

            ctx.font = `bold 36px ${T.font}`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';

            ctx.fillStyle = '#fff';

            ctx.fillText(`${fn2}/${fd}`, W / 2, fbY + fbH / 2);

            if (el.showDecimal) {

                ctx.font = `24px ${T.font}`; ctx.fillStyle = fbCol;

                ctx.fillText(`= ${(fn2/fd).toFixed(2)}`, W / 2 + 80, fbY + fbH / 2);

            }

            ctx.textAlign = 'left';

            return fbH + 28;

        }

        case 'math_calc': {

            const fs = el.fontSize || 48;

            ctx.font = `bold ${fs}px 'Courier New', Consolas, monospace`;

            ctx.fillStyle = rc(el.color || 'white');

            ctx.textAlign = 'right'; ctx.textBaseline = 'top';

            const cx = W / 2 + 80;

            let cy = cursorY + 10;

            const ops = el.operands || [];

            const inters = el.intermediates || [];

            const fullResult = String(el.result || '');

            // ── Expression-mode fallback ──────────────────────────────

            // Detect when operands are expression strings (not simple numbers)

            // e.g. ["35 + 5 × 2", "5 × 2 = 10", "35 + 10 = 45"]

            const isExprMode = ops.some(o => /[a-zA-Z×÷=]/.test(String(o)) || String(o).includes('+') || String(o).includes('-'));

            if (isExprMode || (ops.length === 0 && el.expression)) {

                // Render as centered stacked expression lines

                ctx.textAlign = 'center';

                ctx.textBaseline = 'top';

                const lines = ops.length > 0 ? ops : (el.expression ? [el.expression] : []);

                for (let i = 0; i < lines.length; i++) {

                    const line = String(lines[i]);

                    // Last line or line containing '=' with result → highlight green

                    const isResult = i === lines.length - 1 && fullResult && line.includes(fullResult);

                    if (isResult) {

                        ctx.save();

                        ctx.shadowColor = '#00FF88'; ctx.shadowBlur = 18;

                        ctx.fillStyle = '#00FF88';

                    }

                    ctx.fillText(line, W / 2, cy);

                    if (isResult) ctx.restore();

                    cy += fs * 1.45;

                }

                // Separator + result if not already shown in last line

                if (fullResult && ops.length > 0 && !ops[ops.length - 1].toString().includes(fullResult)) {

                    cy += 4;

                    ctx.beginPath(); ctx.moveTo(W / 2 - 200, cy); ctx.lineTo(W / 2 + 200, cy);

                    ctx.strokeStyle = rc(el.color || 'white'); ctx.lineWidth = 3; ctx.stroke();

                    cy += 14;

                    ctx.save();

                    ctx.shadowColor = '#00FF88'; ctx.shadowBlur = 18;

                    ctx.fillStyle = '#00FF88';

                    ctx.fillText(fullResult, W / 2, cy);

                    ctx.restore();

                    cy += fs * 1.45;

                }

                ctx.textAlign = 'left';

                return (cy - cursorY) + 10;

            }

            // ── End expression-mode ───────────────────────────────────

            if (el.op === ':') {

                // Vietnamese Long Division Layout

                // Left side: Dividend and Intermediates (remainders)

                // Right side: Divisor and Quotient

                const cxLeft = W / 2 - 15;

                const cxRight = W / 2 + 15;

                // Left column: right aligned

                ctx.textAlign = 'right';

                ctx.fillText(ops[0] || '', cxLeft, cy);

                let cyLeft = cy + fs * 1.3;

                for (let i = 0; i < inters.length; i++) {

                    ctx.fillText(inters[i], cxLeft, cyLeft);

                    cyLeft += fs * 1.3;

                }

                // Right column: left aligned

                ctx.textAlign = 'left';

                ctx.fillText(ops[1] || '', cxRight, cy);

                // Horizontal line under divisor

                ctx.beginPath(); ctx.moveTo(W / 2, cy + fs * 1.2); ctx.lineTo(W / 2 + 150, cy + fs * 1.2);

                ctx.strokeStyle = ctx.fillStyle; ctx.lineWidth = 4; ctx.stroke();

                let cyRight = cy + fs * 1.3 + 8;

                // Result

                if (fullResult || el.result_partial !== undefined) {

                    const toDraw = (el.result_partial !== undefined && el.result_partial !== null) ? String(el.result_partial) : fullResult;

                    ctx.save();

                    if (el.result_partial !== undefined && el.result_partial !== null && toDraw.length > 0) {

                        ctx.shadowColor = '#00FF88'; ctx.shadowBlur = 22; ctx.fillStyle = '#00FF88';

                    } else if (el.reveal_result && stepProgress >= (el.reveal_at ?? 0.1)) {

                        ctx.fillStyle = rc('green');

                    } else if (!el.reveal_result) {

                        ctx.fillStyle = rc('green');

                    } else {

                        // Not revealed yet

                        ctx.globalAlpha = 0;

                    }

                    if (ctx.globalAlpha > 0) ctx.fillText(toDraw, cxRight, cyRight);

                    ctx.restore();

                    cyRight += fs * 1.3;

                }

                // Vertical line separating left and right

                const totalHLeft = Math.max(cyLeft - cy, cyRight - cy);

                ctx.beginPath(); ctx.moveTo(W / 2, cy - 5); ctx.lineTo(W / 2, cy + totalHLeft + 10);

                ctx.stroke();

                return Math.max(cyLeft, cyRight) - cursorY + 10;

            }

            // Standard Vertical Layout (+, -, x)

            // Calculate max length to position the operator

            const allStrs = [...ops.map(String), ...inters.map(String), fullResult];

            const totalLen = Math.max(...allStrs.map(s => s.length));

            for (let i = 0; i < ops.length; i++) {

                ctx.fillText(ops[i], cx, cy);

                if (i === ops.length - 1 && el.op) {

                    ctx.textAlign = 'left';

                    const opOffset = totalLen * (fs * 0.6) + 30;

                    ctx.fillText(el.op, cx - opOffset, cy);

                    ctx.textAlign = 'right';

                }

                cy += fs * 1.3;

            }

            // Horizontal separator line 1

            cy += 8;

            ctx.beginPath(); ctx.moveTo(cx - 240, cy); ctx.lineTo(cx + 20, cy);

            ctx.strokeStyle = ctx.fillStyle; ctx.lineWidth = 4; ctx.stroke();

            cy += 20;

            // Intermediates

            for (let i = 0; i < inters.length; i++) {

                ctx.fillText(inters[i], cx, cy);

                cy += fs * 1.3;

            }

            // Horizontal separator line 2 (if we had intermediates and a final result)

            if (inters.length > 0 && (fullResult || el.result_partial !== undefined)) {

                cy += 8;

                ctx.beginPath(); ctx.moveTo(cx - 240, cy); ctx.lineTo(cx + 20, cy);

                ctx.strokeStyle = ctx.fillStyle; ctx.lineWidth = 4; ctx.stroke();

                cy += 20;

            }

            // ── Result display (3 modes) ──────────────────────────

            if (fullResult) {

                const charW = ctx.measureText('0').width; // monospace char width

                if (el.result_partial !== undefined && el.result_partial !== null) {

                    // MODE 1: Partial reveal — digits appear one by one from right

                    const partial = String(el.result_partial);

                    const totalDigits = fullResult.length;

                    ctx.save();

                    // Draw dim placeholder slots for unwritten digits (left side)

                    const unwrittenCount = totalDigits - partial.length;

                    for (let d = 0; d < unwrittenCount; d++) {

                        const slotX = cx - (totalDigits - d - 1) * charW * 1.1;

                        ctx.fillStyle = 'rgba(255,255,255,0.12)';

                        ctx.fillText('_', slotX, cy);

                    }

                    // Draw the partial result (right-aligned)

                    if (partial.length > 0) {

                        // Glow on the newest digit (leftmost of partial)

                        ctx.shadowColor = '#00FF88';

                        ctx.shadowBlur = 22;

                        ctx.fillStyle = '#00FF88';

                        ctx.fillText(partial, cx, cy);

                    }

                    ctx.restore();

                    cy += fs * 1.3;

                } else if (el.reveal_result) {

                    // MODE 2: Classic reveal — shows '?' then flips to result

                    const REVEAL_AT = el.reveal_at ?? 0.1;

                    const revealed = stepProgress >= REVEAL_AT;

                    if (revealed) {

                        const rp = Math.min((stepProgress - REVEAL_AT) / 0.2, 1.0);

                        ctx.save();

                        ctx.globalAlpha = 0.9 + rp * 0.1;

                        if (rp < 1) { ctx.shadowColor = '#00FF88'; ctx.shadowBlur = 30 * (1 - rp); }

                        ctx.fillStyle = rc('green');

                        ctx.fillText(fullResult, cx, cy);

                        ctx.restore();

                    } else {

                        const pulse = 0.6 + 0.4 * Math.sin(Date.now() / 400);

                        const tw = ctx.measureText('?').width;

                        ctx.save();

                        ctx.strokeStyle = `rgba(255,215,0,${pulse})`;

                        ctx.lineWidth = 2.5;

                        roundRect(cx - tw - 14, cy - 4, tw + 28, fs + 8, 8);

                        ctx.stroke();

                        ctx.fillStyle = `rgba(255,215,0,${0.5 + 0.3 * pulse})`;

                        ctx.fillText('?', cx, cy);

                        ctx.restore();

                    }

                    cy += fs * 1.3;

                } else {

                    // MODE 3: Always visible

                    ctx.fillStyle = rc('green');

                    ctx.fillText(fullResult, cx, cy);

                }

                cy += fs * 1.3;

            }

            ctx.textAlign = 'left';

            return (cy - cursorY) + 10;

        }

        case 'reveal': {

            // {"type":"reveal", "value":"319", "label":"a + b = b + ?", "fontSize":44, "color":"highlight", "align":"center", "reveal_at":0.4}

            const fs = el.fontSize || 44;

            const REVEAL_AT = el.reveal_at ?? 0.45;

            const revealed = stepProgress >= REVEAL_AT;

            const font = `bold ${fs}px ${T.font}`;

            ctx.font = font; ctx.textBaseline = 'top';

            const align = el.align || 'center';

            ctx.textAlign = align;

            const tx = align === 'center' ? W/2 : align === 'right' ? W - MX : MX;

            // Draw label with placeholder if any

            let displayText = el.label || '';

            if (displayText.includes('?') && revealed) {

                displayText = displayText.replace('?', el.value || '?');

            }

            let lineH = 0;

            if (displayText) {

                ctx.fillStyle = rc(el.color || 'highlight');

                const wrapped = wrapText(displayText, W - MX*2, font);

                for (const line of wrapped) {

                    drawRichMathText(ctx, line, tx, cursorY + lineH, fs, rc(el.color || 'highlight'), align, true, 'top');

                    lineH += fs * 1.4;

                }

            } else {

                // Standalone value (no label)

                const revealProg = revealed ? Math.min((stepProgress - REVEAL_AT) / 0.2, 1) : 0;

                if (revealed) {

                    ctx.save();

                    if (revealProg < 1) { ctx.shadowColor = T.hlColor; ctx.shadowBlur = 25 * (1 - revealProg); }

                    drawRichMathText(ctx, el.value || '', tx, cursorY, fs, rc(el.color || 'highlight'), align, true, 'top');

                    ctx.restore();

                } else {

                    const pulse = 0.6 + 0.4 * Math.sin(Date.now() / 400);

                    const tw = ctx.measureText('?').width;

                    const bx = align==='center' ? W/2-tw/2-14 : tx-14;

                    ctx.save();

                    ctx.strokeStyle = `rgba(255,215,0,${pulse})`; ctx.lineWidth = 2.5;

                    roundRect(bx, cursorY-4, tw+28, fs+8, 8); ctx.stroke();

                    ctx.fillStyle = `rgba(255,215,0,${0.5+0.3*pulse})`;

                    ctx.fillText('?', tx, cursorY);

                    ctx.restore();

                }

                lineH = fs + 12;

            }

            ctx.textAlign = 'left';

            return lineH + 6;

        }

        default:

            return 0;

    }

}

// ── Unified Layout Builder ────────────────────────────────────────

function buildUnifiedLayout(currentTime, renderFrom, steps, tSteps) {

    const nonGeoEls = [];

    const geoEls = [];

    let hasImageGen = false; // only allow first image_generation placeholder

    for (let i = renderFrom; i < steps.length; i++) {

        const step = steps[i], ts = tSteps[i];

        if (!ts || currentTime < ts.start) continue;

        const rawP = Math.min((currentTime - ts.start) / Math.max(ts.end - ts.start, 0.1), 1);

        let addedAny = false;

        for (const el of (step.elements || [])) {

            if (el.type === 'point' || el.type === 'segment' || el.type === 'right_angle') {

                geoEls.push({ el, rawP });

                continue;

            }

            // Deduplicate image_generation: only render the first placeholder per screen

            if (el.type === 'image_generation') {

                if (hasImageGen) continue; // skip duplicates

                hasImageGen = true;

            }

            let replaced = false;

            // Deduplicate math_calc by operands and operator

            if (el.type === 'math_calc') {

                const sig = el.op + '|' + (el.operands||[]).join('|');

                for (let j = nonGeoEls.length - 1; j >= 0; j--) {

                    const u = nonGeoEls[j];

                    if (u.el.type === 'math_calc' && u.el.op + '|' + (u.el.operands||[]).join('|') === sig) {

                        nonGeoEls[j] = { el: el, rawP: u.rawP };

                        replaced = true;

                        break;

                    }

                }

            }

            if (!replaced) {

                nonGeoEls.push({ el, rawP });

                addedAny = true;

            }

        }

        if (addedAny) {

            nonGeoEls.push({ el: { type: 'gap' }, rawP: 1 });

        }

    }

    return { nonGeoEls, geoEls };

}

// Ken Burns cho mathnoir: zoom rất chậm quanh tâm khung (1 → 1.035 tuyến
// tính theo stepProgress) + drift nhẹ theo time — trừ mn_chrome (ghim cứng).
// Gọi SAU ctx.save() của element; caller tự restore.
function applyMnKenBurns(rawP) {
    const t = currentFrameTime;
    const s = 1 + 0.035 * Math.max(0, Math.min(1, rawP));
    const dx = 6 * Math.sin(t * 0.13), dy = 4 * Math.sin(t * 0.09);
    ctx.translate(W / 2 + dx, H / 2 + dy);
    ctx.scale(s, s);
    ctx.translate(-W / 2, -H / 2);
}

function renderUnifiedElements(unifiedEls, startY) {

    let cursorY = startY;

    let i = 0;

    while (i < unifiedEls.length) {

        const u = unifiedEls[i];

        const el = u.el;

        if (el.type === 'gap') {

            cursorY += 18; // STEP_GAP

            i++;

            continue;

        }

        const alpha = easeOut(Math.min(u.rawP * 4.0, 1.0)); // Fast fade in

        if (el.type === 'box') {

            const style = (BOX_STYLES[el.style] || BOX_STYLES.subtle)();

            const inner = [];

            let j = i + 1;

            while (j < unifiedEls.length && (unifiedEls[j].el.type === 'text' || unifiedEls[j].el.type === 'list' || unifiedEls[j].el.type === 'math_calc' || unifiedEls[j].el.type === 'reveal')) {

                inner.push(unifiedEls[j]);

                j++;

            }

            // Skip rendering if the box is completely empty (happens when AI duplicates box elements)

            if (inner.length === 0) {

                i++; // MUST increment to avoid infinite loop

                continue;

            }

            const anim = el.animation || 'slide_up';

            let offsetY = 0;

            if (anim === 'slide_up' && u.rawP < 1.0) {

                const p = Math.min(u.rawP * 4.0, 1.0); // Fast slide up

                offsetY = 30 * (1 - easeOutBack(p)); // Use easeOutBack for a little bounce

            }

            let innerH = 0;

            for (const iu of inner) innerH += measureTextHeight(iu.el) + 6;

            const boxPadding = 20;

            const boxH = innerH + boxPadding * 2;

            const boxInset = 30; // extra inset from margins for narrower box

            const bx = MX + boxInset - 10, bw = W - MX * 2 - boxInset * 2 + 20;

            const mnKB = (artStyle === 'mathnoir' && el.template !== 'mn_chrome');

            if (mnKB) { ctx.save(); applyMnKenBurns(u.rawP); }

            ctx.save();

            ctx.globalAlpha = alpha;

            ctx.translate(0, offsetY);

            if (style.glow) { ctx.shadowColor = style.border; ctx.shadowBlur = 20; }
            else if (global.glassEffect) {
                ctx.shadowColor = 'rgba(0, 0, 0, 0.35)';
                ctx.shadowBlur = 24;
                ctx.shadowOffsetY = 6;
            }

            roundRect(bx, cursorY, bw, boxH, 16);

            ctx.fillStyle = style.bg; ctx.fill();

            // Clear shadow for borders and sheen
            ctx.shadowBlur = 0;
            ctx.shadowOffsetY = 0;

            if (style.border) { ctx.strokeStyle = style.border; ctx.lineWidth = 2; ctx.stroke(); }

            // Glassmorphism: frosted top-light sheen + soft inner highlight

            if (global.glassEffect) {

                ctx.save();

                roundRect(bx, cursorY, bw, boxH, 16);

                ctx.clip();

                const sheen = ctx.createLinearGradient(0, cursorY, 0, cursorY + boxH);

                sheen.addColorStop(0, 'rgba(255,255,255,0.16)');

                sheen.addColorStop(0.35, 'rgba(255,255,255,0.04)');

                sheen.addColorStop(1, 'rgba(255,255,255,0.0)');

                ctx.fillStyle = sheen;

                ctx.fillRect(bx, cursorY, bw, boxH);

                // bright top edge highlight

                ctx.strokeStyle = 'rgba(255,255,255,0.45)';

                ctx.lineWidth = 1.5;

                ctx.beginPath();

                ctx.moveTo(bx + 16, cursorY + 1.5);

                ctx.lineTo(bx + bw - 16, cursorY + 1.5);

                ctx.stroke();

                ctx.restore();

            }

            ctx.restore();

            let innerY = cursorY + boxPadding + offsetY;

            for (const iu of inner) {

                ctx.save();

                ctx.globalAlpha = easeOut(Math.min(iu.rawP * 4.0, 1.0));

                innerY += renderElementAtY(iu.el, innerY, iu.rawP);

                ctx.restore();

            }

            if (mnKB) ctx.restore();

            cursorY += boxH + 8;

            i = j;

            continue;

        }

        ctx.save();

        ctx.globalAlpha = alpha;

        if (artStyle === 'mathnoir' && el.template !== 'mn_chrome') applyMnKenBurns(u.rawP);

        cursorY += renderElementAtY(el, cursorY, u.rawP);

        ctx.restore();

        i++;

    }

    return cursorY;

}

// ── Offscreen Canvas Caches for Fast Artistic Rendering ─────────
let watercolorOverlayCanvas = null;
function getWatercolorOverlayCanvas() {
    if (watercolorOverlayCanvas) return watercolorOverlayCanvas;
    const c = createCanvas(W, H);
    const cx = c.getContext('2d');
    cx.fillStyle = 'rgba(215, 205, 185, 0.12)';
    cx.fillRect(0, 0, W, H);
    const vignette = cx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.3, W / 2, H / 2, Math.max(W, H) * 0.7);
    vignette.addColorStop(0, 'rgba(255, 255, 255, 0)');
    vignette.addColorStop(1, 'rgba(190, 175, 150, 0.25)');
    cx.fillStyle = vignette;
    cx.fillRect(0, 0, W, H);
    cx.fillStyle = 'rgba(0, 0, 0, 0.03)';
    for (let j = 0; j < 3000; j++) {
        const rx = Math.random() * W;
        const ry = Math.random() * H;
        const rw = Math.random() * 3 + 1;
        const rh = Math.random() * 3 + 1;
        cx.fillRect(rx, ry, rw, rh);
    }
    watercolorOverlayCanvas = c;
    return watercolorOverlayCanvas;
}

let cartoonHalftoneCanvas = null;
function getCartoonHalftoneCanvas() {
    if (cartoonHalftoneCanvas) return cartoonHalftoneCanvas;
    const c = createCanvas(W, H);
    const cx = c.getContext('2d');
    cx.fillStyle = 'rgba(0, 0, 0, 0.08)';
    const spacing = 20;
    for (let x = spacing / 2; x < W; x += spacing) {
        for (let y = spacing / 2; y < H; y += spacing) {
            const dx = x - W / 2;
            const dy = y - H / 2;
            const dist = Math.sqrt(dx * dx + dy * dy);
            if (dist > Math.min(W, H) * 0.36) {
                const size = Math.min(7, (dist - Math.min(W, H) * 0.36) / 45);
                if (size > 0.6) {
                    cx.beginPath(); cx.arc(x, y, size, 0, Math.PI * 2); cx.fill();
                }
            }
        }
    }
    cartoonHalftoneCanvas = c;
    return cartoonHalftoneCanvas;
}

let sketchOverlayCanvas = null;
function getSketchOverlayCanvas() {
    if (sketchOverlayCanvas) return sketchOverlayCanvas;
    const c = createCanvas(W, H);
    const cx = c.getContext('2d');
    cx.fillStyle = 'rgba(0, 0, 0, 0.05)';
    cx.fillRect(0, 0, W, H);
    const vignette = cx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.4, W / 2, H / 2, Math.max(W, H) * 0.7);
    vignette.addColorStop(0, 'rgba(255, 255, 255, 0)');
    vignette.addColorStop(1, 'rgba(0, 0, 0, 0.12)');
    cx.fillStyle = vignette;
    cx.fillRect(0, 0, W, H);
    cx.strokeStyle = 'rgba(0, 0, 0, 0.02)';
    cx.lineWidth = 1;
    const gridDist = 60;
    for (let x = 0; x < W; x += gridDist) {
        cx.beginPath(); cx.moveTo(x, 0); cx.lineTo(x, H); cx.stroke();
    }
    for (let y = 0; y < H; y += gridDist) {
        cx.beginPath(); cx.moveTo(0, y); cx.lineTo(W, y); cx.stroke();
    }
    cx.strokeStyle = 'rgba(0, 0, 0, 0.16)';
    cx.lineWidth = 1.8;
    cx.beginPath(); cx.moveTo(MX - 15, 38); cx.lineTo(W - MX + 20, 36); cx.stroke();
    cx.beginPath(); cx.moveTo(MX - 10, 42); cx.lineTo(W - MX + 15, 40); cx.stroke();
    cx.beginPath(); cx.moveTo(MX - 8, 25); cx.lineTo(MX - 10, H - 30); cx.stroke();
    cx.beginPath(); cx.moveTo(W - MX + 8, 28); cx.lineTo(W - MX + 6, H - 35); cx.stroke();
    cx.beginPath(); cx.moveTo(MX - 20, H - 38); cx.lineTo(W - MX + 20, H - 40); cx.stroke();
    cx.strokeStyle = 'rgba(0, 0, 0, 0.05)'; cx.lineWidth = 1;
    for (let j = 0; j < 40; j++) {
        const rx = Math.random() * W;
        const ry = Math.random() * H;
        cx.beginPath(); cx.moveTo(rx, ry);
        cx.lineTo(rx + Math.random() * 50 - 25, ry + Math.random() * 50 - 25);
        cx.stroke();
    }
    sketchOverlayCanvas = c;
    return sketchOverlayCanvas;
}

let pixelScanlinesCanvas = null;
function getPixelScanlinesCanvas() {
    if (pixelScanlinesCanvas) return pixelScanlinesCanvas;
    const c = createCanvas(W, H);
    const cx = c.getContext('2d');
    cx.fillStyle = 'rgba(0, 0, 0, 0.08)';
    for (let y = 0; y < H; y += 4) {
        cx.fillRect(0, y, W, 1);
    }
    pixelScanlinesCanvas = c;
    return pixelScanlinesCanvas;
}

let crtScanlinesCanvas = null;
function getCrtScanlinesCanvas() {
    if (crtScanlinesCanvas) return crtScanlinesCanvas;
    const c = createCanvas(W, H);
    const cx = c.getContext('2d');
    cx.fillStyle = 'rgba(0, 0, 0, 0.07)';
    for (let y = 0; y < H; y += 4) {
        cx.fillRect(0, y, W, 2);
    }
    crtScanlinesCanvas = c;
    return crtScanlinesCanvas;
}

// ── PHỤ ĐỀ: khởi tạo engine + gộp dữ liệu step ──────────────────
// subtitle_engine.js là hàm THUẦN theo thời gian (không tích luỹ giữa frame)
// nên worker chunk khởi động lạnh ở frame 900 vẫn vẽ y hệt → không "nhảy" ở
// chỗ nối chunk. Bố cục cụm chữ được cache theo step.id, không tính lại/frame.
let SUB_ENGINE = null;
let SUB_STEPS = null;

if (SUB_CFG) {
    try {
        const { makeSubtitle, loadPresets, getPreset } = require('./subtitle_engine.js');
        const presets = loadPresets(path.join(__dirname, 'subtitle_presets.json'));
        const preset = getPreset(presets, SUB_CFG.preset);
        if (!preset) {
            process.stderr.write('[Subtitle] subtitle_presets.json rỗng → bỏ qua phụ đề\n');
        } else {
            if (SUB_CFG.preset && preset.id !== SUB_CFG.preset) {
                process.stderr.write(`[Subtitle] không có preset "${SUB_CFG.preset}" → dùng "${preset.id}"\n`);
            }
            if (SUB_CFG.accent && /^#[0-9a-fA-F]{6}$/.test(SUB_CFG.accent)) {
                // Màu nhấn theo template (def "subtitle_accent"): từ-đang-đọc
                // + quầng glow (chỉ preset kiểu glow, blur lớn) ăn theo accent.
                const r = parseInt(SUB_CFG.accent.slice(1, 3), 16),
                    g = parseInt(SUB_CFG.accent.slice(3, 5), 16),
                    b = parseInt(SUB_CFG.accent.slice(5, 7), 16);
                preset.color = preset.color || {};
                preset.color.active = SUB_CFG.accent;
                const sh = preset.color.shadow;
                if (sh && Number(sh.blur) >= 18) {
                    const m = /rgba?\([^)]*,\s*([\d.]+)\s*\)/.exec(String(sh.color || ''));
                    sh.color = `rgba(${r},${g},${b},${m ? m[1] : '0.7'})`;
                }
            }
            SUB_ENGINE = makeSubtitle(preset, {
                fontScale: SUB_CFG.fontScale,
                yPct: (SUB_CFG.yPct === undefined ? null : SUB_CFG.yPct),
                maxLines: (SUB_CFG.maxLines === undefined ? null : SUB_CFG.maxLines),
                fallbackFamily: SYSTEM_FONT_STACK,   // Be Vietnam Pro: đủ dấu tiếng Việt
                warn: function (m) { process.stderr.write('[Subtitle] ' + m + '\n'); }
            });
            process.stderr.write(`[Subtitle] preset=${preset.id} fontScale=${SUB_CFG.fontScale || 1}\n`);
        }
    } catch (e) {
        process.stderr.write(`[Subtitle] tắt phụ đề (lỗi khởi tạo): ${e.message}\n`);
        SUB_ENGINE = null;
    }
}

/** Gộp timing.steps + script.steps.voice_text → dữ liệu đầu vào của engine. */
function buildSubSteps() {
    const ts = (timing && timing.steps) || [];
    const ss = (script && script.steps) || [];
    const out = [];
    for (let i = 0; i < ts.length; i++) {
        const t = ts[i] || {};
        const s = ss[i] || {};
        const start = Number(t.start) || 0;
        const end = (t.end !== undefined && t.end !== null) ? Number(t.end)
            : start + (Number(t.duration) || 0);
        out.push({
            id: (t.id !== undefined && t.id !== null) ? t.id : (i + 1),
            start: start,
            end: end,
            duration: Number(t.duration) || Math.max(0, end - start),
            words: Array.isArray(t.words) ? t.words : [],
            voice_text: s.voice_text || '',        // dự phòng khi words rỗng
            // Ghi đè theo từng step (schema.py bỏ qua key lạ nên script vẫn hợp lệ):
            //   "subtitle": false        → step này không có phụ đề (thẻ tiêu đề…)
            //   "subtitle_pos": "top"    → đẩy phụ đề lên trên (step chật ở dưới)
            subtitle: s.subtitle,
            no_subtitle: s.no_subtitle,
            subtitle_pos: s.subtitle_pos,
            subtitle_y_pct: s.subtitle_y_pct,
            //   "subtitle_y_pct_9_16" → né cảnh cao, CHỈ áp cho khung dọc
            //   (script_generator._center_layout tính từ y_9_16 × 1920)
            subtitle_y_pct_9_16: s.subtitle_y_pct_9_16
        });
    }
    return out;
}

function drawSubtitle(t) {
    if (!SUB_ENGINE) return;
    if (!SUB_STEPS) SUB_STEPS = buildSubSteps();
    if (!SUB_STEPS.length) return;
    // Step đang chạy = step cuối cùng đã bắt đầu (totalFrames = ceil(dur*fps) nên
    // frame cuối có thể vượt total_duration một chút → kẹp vào step cuối).
    let cur = null;
    for (let i = 0; i < SUB_STEPS.length; i++) {
        if (t >= SUB_STEPS[i].start - 0.0005) cur = SUB_STEPS[i]; else break;
    }
    if (!cur) return;
    SUB_ENGINE.draw(ctx, W, H, cur, t, FPS);
}

// ── Main render ─────────────────────────────────────────────────

let currentFrameTime = 0;

function renderFrame(currentTime) {

    // Reset canvas state to prevent state leaks / singular matrix corruption from previous frames

    ctx.setTransform(1, 0, 0, 1, 0, 0);

    ctx.globalAlpha = 1.0;

    ctx.shadowBlur = 0;

    ctx.shadowColor = 'rgba(0,0,0,0)';

    ctx.fillStyle = '#000000';

    ctx.strokeStyle = '#000000';

    ctx.lineWidth = 1;

    ctx.lineCap = 'butt';

    ctx.lineJoin = 'miter';

    ctx.setLineDash([]);

    currentFrameTime = currentTime;

    drawBg();

    const steps = script.steps, tSteps = timing.steps;

    const totalDur = timing.total_duration || 30;

    let activeIdx = -1;

    for (let i = 0; i < tSteps.length; i++) if (currentTime >= tSteps[i].start) activeIdx = i;

    // (dots header removed)

    let cursorY = 80;

    let renderFrom = 0;

    for (let i = steps.length - 1; i >= 0; i--) {

        const ts = tSteps[i];

        if (ts && currentTime >= ts.start && steps[i].clear) {

            renderFrom = i;

            break;

        }

    }

    if (renderFrom > 0) {

        drawBg();

    }

    const { nonGeoEls, geoEls } = buildUnifiedLayout(currentTime, renderFrom, steps, tSteps);

    if (geoEls.length > 0) {

        // ── Split layout: text in top portion, geo in fixed bottom zone ──

        const GEO_ZONE_START = Math.round(H * 0.52);

        const GEO_ZONE_H     = H - GEO_ZONE_START - 80;

        ctx.save();

        ctx.beginPath();

        ctx.rect(0, 0, W, GEO_ZONE_START - 10);

        ctx.clip();

        const textStartY = calcCenteredStartY(nonGeoEls, 80, GEO_ZONE_START - 10);

        renderUnifiedElements(nonGeoEls, textStartY);

        ctx.restore();

        ctx.save();

        ctx.strokeStyle = T.geoBorder || '#3a3a5a';

        ctx.lineWidth = 1;

        ctx.setLineDash([8, 6]);

        ctx.beginPath();

        ctx.moveTo(MX, GEO_ZONE_START - 5);

        ctx.lineTo(W - MX, GEO_ZONE_START - 5);

        ctx.stroke();

        ctx.setLineDash([]);

        ctx.restore();

        renderGeometryZone(geoEls, GEO_ZONE_START, GEO_ZONE_H);

    } else {

        const startY = calcCenteredStartY(nonGeoEls, 80, H - 80);

        renderUnifiedElements(nonGeoEls, startY);

    }

    drawHighlights(currentTime);

    // drawProgress removed

    // ── Apply Artistic Post-processing Filters ─────────────────────

    if (artStyle === 'pixel') {
        ctx.save();
        ctx.setTransform(1, 0, 0, 1, 0, 0);

        // CRT Curved Screen Glass Reflection

        const glassGrad = ctx.createLinearGradient(0, 0, W, H);

        glassGrad.addColorStop(0, 'rgba(255, 255, 255, 0.08)');

        glassGrad.addColorStop(0.3, 'rgba(255, 255, 255, 0.03)');

        glassGrad.addColorStop(0.31, 'rgba(255, 255, 255, 0)');

        glassGrad.addColorStop(1, 'rgba(255, 255, 255, 0)');

        ctx.fillStyle = glassGrad;

        ctx.fillRect(0, 0, W, H);

        // Retro arcade green status text

        ctx.fillStyle = 'rgba(0, 255, 0, 0.5)';

        ctx.font = 'bold 20px "JetBrains Mono", monospace';

        ctx.fillText('CYBER SCAN: ACTIVE', MX, H - 40);

        ctx.fillText('READY PLAYER 1', W - MX - 180, H - 40);

        // CRT Scanline filter (Optimized with Offscreen Canvas)
        ctx.drawImage(getCrtScanlinesCanvas(), 0, 0);

        ctx.restore();

    } else if (artStyle === 'watercolor') {

        ctx.save();

        ctx.setTransform(1, 0, 0, 1, 0, 0);

        ctx.globalCompositeOperation = 'multiply';

        ctx.drawImage(getWatercolorOverlayCanvas(), 0, 0);

        ctx.restore();

    } else if (artStyle === 'inkwash') {

        ctx.save();

        ctx.setTransform(1, 0, 0, 1, 0, 0);

        ctx.globalCompositeOperation = 'multiply';

        ctx.fillStyle = 'rgba(139, 90, 43, 0.08)';

        ctx.fillRect(0, 0, W, H);

        // Sumi smoke vignette

        const vignette = ctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.3, W / 2, H / 2, Math.max(W, H) * 0.75);

        vignette.addColorStop(0, 'rgba(255, 255, 255, 0)');

        vignette.addColorStop(1, 'rgba(40, 40, 40, 0.3)');

        ctx.fillStyle = vignette;

        ctx.fillRect(0, 0, W, H);

        // Soft sumi wash fiber strokes

        ctx.fillStyle = 'rgba(0, 0, 0, 0.01)';

        for (let j = 0; j < 10; j++) {

            const ry = Math.random() * H;

            ctx.fillRect(0, ry, W, Math.random() * 20 + 5);

        }

        // 1. Beautiful Sumi ink smoke cloud washes in the background

        const inkClouds = [

            {x: 80, y: 120, r: 350, o: 0.08},

            {x: W - 120, y: H - 200, r: 450, o: 0.07},

            {x: W / 2, y: H * 0.45, r: 500, o: 0.04}

        ];

        inkClouds.forEach(cloud => {

            const grad = ctx.createRadialGradient(cloud.x, cloud.y, 0, cloud.x, cloud.y, cloud.r);

            grad.addColorStop(0, `rgba(47, 62, 70, ${cloud.o})`);

            grad.addColorStop(0.6, `rgba(47, 62, 70, ${cloud.o * 0.4})`);

            grad.addColorStop(1, 'rgba(255,255,255,0)');

            ctx.fillStyle = grad;

            ctx.beginPath(); ctx.arc(cloud.x, cloud.y, cloud.r, 0, Math.PI*2); ctx.fill();

        });

        // 2. Roll parchment border vignette

        const vignette2 = ctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.3, W / 2, H / 2, Math.max(W, H) * 0.72);

        vignette2.addColorStop(0, 'rgba(255, 255, 255, 0)');

        vignette2.addColorStop(1, 'rgba(125, 95, 60, 0.2)');

        ctx.fillStyle = vignette2; ctx.fillRect(0, 0, W, H);

        // 3. Ancient Chinese Calligraphy Red Square Seal in top-right corner

        ctx.globalCompositeOperation = 'source-over';

        ctx.fillStyle = '#b22222'; // Traditional Vermilion seal red

        ctx.fillRect(W - MX - 40, 45, 45, 45);

        ctx.strokeStyle = '#efe9db'; ctx.lineWidth = 2.5;

        ctx.strokeRect(W - MX - 37, 48, 39, 39);

        // Calligraphy squiggles in seal

        ctx.beginPath();

        ctx.moveTo(W - MX - 28, 54); ctx.lineTo(W - MX - 28, 80);

        ctx.moveTo(W - MX - 18, 52); ctx.lineTo(W - MX - 18, 78);

        ctx.stroke();

        // 4. Wooden scroll borders (Hanging roll wrapper - Kakemono)

        ctx.fillStyle = '#2b1c12'; // Dark polished mahogany scroll bars

        ctx.fillRect(0, 0, W, 22);

        ctx.fillRect(0, H - 22, W, 22);

        ctx.restore();

    } else if (artStyle === 'sketch') {

        ctx.save();

        ctx.setTransform(1, 0, 0, 1, 0, 0);

        ctx.globalCompositeOperation = 'multiply';

        ctx.drawImage(getSketchOverlayCanvas(), 0, 0);

        ctx.restore();

    } else if (artStyle === 'cartoon') {

        ctx.save();

        ctx.setTransform(1, 0, 0, 1, 0, 0);

        // Draw pre-rendered halftone shading dots (Optimized)
        ctx.drawImage(getCartoonHalftoneCanvas(), 0, 0);

        // 2. Thick 8px comic book border outline

        ctx.strokeStyle = '#000000'; ctx.lineWidth = 10;

        ctx.strokeRect(MX - 10, 40, W - MX * 2 + 20, H - 80);

        // 3. Exclamation Pop Starburst Badge in bottom corner!

        ctx.fillStyle = '#ffdf00'; ctx.strokeStyle = '#000000'; ctx.lineWidth = 4;

        const bx = W - MX - 50, by = H - 120, r = 35;

        ctx.beginPath();

        for (let i = 0; i < 16; i++) {

            const angle = (i / 16) * Math.PI * 2;

            const dist = i % 2 === 0 ? r : r * 0.65;

            const px = bx + Math.cos(angle) * dist;

            const py = by + Math.sin(angle) * dist;

            if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);

        }

        ctx.closePath(); ctx.fill(); ctx.stroke();

        ctx.fillStyle = '#000'; ctx.font = '900 18px "Impact", sans-serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';

        ctx.fillText('POP!', bx, by);

        ctx.restore();

    } else if (artStyle === 'cyberpunk') {

        ctx.save();

        ctx.setTransform(1, 0, 0, 1, 0, 0);

        // 1. Retro-future perspective glowing wireframe grid at the bottom

        ctx.strokeStyle = 'rgba(0, 255, 255, 0.12)'; ctx.lineWidth = 1.5;

        const gridY = H - 280;

        for (let x = MX; x <= W - MX; x += 60) {

            ctx.beginPath();

            ctx.moveTo(x, H - 30);

            ctx.lineTo(W / 2 + (x - W / 2) * 0.18, gridY);

            ctx.stroke();

        }

        for (let y = gridY; y < H; y += 35) {

            ctx.beginPath();

            const ratio = (y - gridY) / (H - gridY);

            const wDiff = (W - MX * 2) * (1 - ratio * 0.8);

            ctx.moveTo(W / 2 - wDiff / 2, y);

            ctx.lineTo(W / 2 + wDiff / 2, y);

            ctx.stroke();

        }

        // 2. High-tech HUD Corner Brackets

        ctx.strokeStyle = '#00ffff'; ctx.lineWidth = 3.5;

        const gap = 20; const len = 35;

        // Top-Left

        ctx.beginPath(); ctx.moveTo(MX - gap + len, 50); ctx.lineTo(MX - gap, 50); ctx.lineTo(MX - gap, 50 + len); ctx.stroke();

        // Top-Right

        ctx.beginPath(); ctx.moveTo(W - MX + gap - len, 50); ctx.lineTo(W - MX + gap, 50); ctx.lineTo(W - MX + gap, 50 + len); ctx.stroke();

        // Bottom-Left

        ctx.beginPath(); ctx.moveTo(MX - gap + len, H - 50); ctx.lineTo(MX - gap, H - 50); ctx.lineTo(MX - gap, H - 50 - len); ctx.stroke();

        // Bottom-Right

        ctx.beginPath(); ctx.moveTo(W - MX + gap - len, H - 50); ctx.lineTo(W - MX + gap, H - 50); ctx.lineTo(W - MX + gap, H - 50 - len); ctx.stroke();

        // 3. Digital neon chromatic overlay scanlines

        const vignette = ctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.4, W / 2, H / 2, Math.max(W, H) * 0.85);

        vignette.addColorStop(0, 'rgba(0, 255, 255, 0)');

        vignette.addColorStop(1, 'rgba(255, 0, 127, 0.14)');

        ctx.fillStyle = vignette; ctx.fillRect(0, 0, W, H);

        ctx.fillStyle = 'rgba(0, 255, 255, 0.05)';

        for (let y = 0; y < H; y += 8) {

            ctx.fillRect(0, y, W, 1);

        }

        ctx.restore();

    } else if (artStyle === 'pastel') {

        ctx.save();

        ctx.setTransform(1, 0, 0, 1, 0, 0);

        // 1. Organic, beautiful fluid pastel blobs

        const blobs = [

            {x: W * 0.15, y: H * 0.22, r: 500, c1: 'rgba(255, 181, 167, 0.28)', c2: 'rgba(255, 202, 212, 0)'},

            {x: W * 0.85, y: H * 0.65, r: 550, c1: 'rgba(181, 226, 250, 0.28)', c2: 'rgba(181, 242, 234, 0)'},

            {x: W * 0.35, y: H * 0.88, r: 450, c1: 'rgba(240, 230, 255, 0.25)', c2: 'rgba(255, 255, 255, 0)'}

        ];

        blobs.forEach(b => {

            const g = ctx.createRadialGradient(b.x, b.y, 0, b.x, b.y, b.r);

            g.addColorStop(0, b.c1);

            g.addColorStop(1, b.c2);

            ctx.fillStyle = g;

            ctx.beginPath(); ctx.arc(b.x, b.y, b.r, 0, Math.PI*2); ctx.fill();

        });

        // 2. Soft pastel borders

        ctx.strokeStyle = 'rgba(255, 255, 255, 0.6)'; ctx.lineWidth = 12;

        ctx.strokeRect(6, 6, W - 12, H - 12);

        ctx.restore();

    } else if (artStyle === 'aurora') {

        // Nền SÁNG premium: mesh blobs pastel trôi chậm + bokeh + vệt sáng chéo.
        ctx.save();
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        const t = (typeof currentFrameTime === 'number' ? currentFrameTime : 0);
        const AB = [
            {x: 0.15, y: 0.12, r: 430, c: '191,219,254', a: 0.55},
            {x: 0.85, y: 0.24, r: 390, c: '221,214,254', a: 0.50},
            {x: 0.50, y: 0.55, r: 540, c: '251,207,232', a: 0.34},
            {x: 0.18, y: 0.85, r: 410, c: '187,247,208', a: 0.40},
            {x: 0.88, y: 0.80, r: 370, c: '254,215,170', a: 0.34},
        ];
        AB.forEach((b, i) => {
            const wob = Math.sin(t * 0.2 + i * 2.1);
            const bx = b.x * W + wob * 30, by = b.y * H + Math.cos(t * 0.16 + i) * 24;
            const g = ctx.createRadialGradient(bx, by, 0, bx, by, b.r);
            g.addColorStop(0, 'rgba(' + b.c + ',' + b.a + ')');
            g.addColorStop(1, 'rgba(' + b.c + ',0)');
            ctx.fillStyle = g;
            ctx.beginPath(); ctx.arc(bx, by, b.r, 0, Math.PI * 2); ctx.fill();
        });
        // bokeh nổi nhẹ
        for (let i = 0; i < 24; i++) {
            const bx = ((i * 233) % W);
            const by = (((i * 541) % H) + t * 10) % H;
            const fl = 0.05 + 0.09 * Math.abs(Math.sin(t * 0.7 + i * 1.3));
            const r = (i % 5 === 0) ? 24 : (i % 3 === 0 ? 13 : 7);
            ctx.fillStyle = 'rgba(255,255,255,' + fl + ')';
            ctx.beginPath(); ctx.arc(bx, by, r, 0, Math.PI * 2); ctx.fill();
            ctx.strokeStyle = 'rgba(148,163,216,' + (fl * 0.9) + ')'; ctx.lineWidth = 1;
            ctx.beginPath(); ctx.arc(bx, by, r, 0, Math.PI * 2); ctx.stroke();
        }
        // vệt sáng chéo quét chậm
        const swp = ((t * 0.06) % 1.4) - 0.2;
        const g2 = ctx.createLinearGradient(W * (swp - 0.18), 0, W * (swp + 0.18), H * 0.5);
        g2.addColorStop(0, 'rgba(255,255,255,0)');
        g2.addColorStop(0.5, 'rgba(255,255,255,0.33)');
        g2.addColorStop(1, 'rgba(255,255,255,0)');
        ctx.save(); ctx.rotate(-0.18); ctx.fillStyle = g2;
        ctx.fillRect(-W * 0.3, -H * 0.2, W * 1.8, H * 1.6); ctx.restore();
        ctx.restore();

    } else if (artStyle === 'mathnoir') {

        // Đen tuyền manim: chỉ 1 quầng sáng rất nhẹ giữa khung + vignette —
        // sạch tuyệt đối, để nét trắng mảnh tự toả sáng.
        ctx.save();
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        const t = (typeof currentFrameTime === 'number' ? currentFrameTime : 0);
        const mg = ctx.createRadialGradient(
            W / 2, H * 0.42, 0,
            W / 2, H * 0.42, Math.max(W, H) * 0.55);
        mg.addColorStop(0, 'rgba(255,255,255,' + (0.028 + 0.006 * Math.sin(t * 0.4)) + ')');
        mg.addColorStop(1, 'rgba(255,255,255,0)');
        ctx.fillStyle = mg;
        ctx.fillRect(0, 0, W, H);
        const mv = ctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.45, W / 2, H / 2, Math.max(W, H) * 0.85);
        mv.addColorStop(0, 'rgba(0,0,0,0)');
        mv.addColorStop(1, 'rgba(0,0,0,0.5)');
        ctx.fillStyle = mv; ctx.fillRect(0, 0, W, H);
        // Bụi li ti trôi chậm lên-phải: vị trí deterministic theo index
        // (fract(sin(i)*43758)), wrap quanh mép — mờ đến mức gần vô thức.
        const mnFract = v => v - Math.floor(v);
        for (let i = 0; i < 14; i++) {
            const r1 = mnFract(Math.sin(i * 127.3) * 43758.5453);
            const r2 = mnFract(Math.sin(i * 311.7) * 43758.5453);
            const r3 = mnFract(Math.sin(i * 74.7) * 43758.5453);
            const spd = 6 + 4 * r3;                                    // 6-10 px/s
            const px = mnFract(r1 + t * spd * 0.6 / W) * W;            // dạt phải
            const py = mnFract(r2 - t * spd / H) * H;                  // trôi lên
            ctx.fillStyle = 'rgba(232,232,234,' + (0.04 + 0.06 * r2).toFixed(3) + ')';
            ctx.beginPath();
            ctx.arc(px, py, 1 + 1.2 * r3, 0, Math.PI * 2);
            ctx.fill();
        }
        ctx.restore();

    } else if (artStyle === 'warmpaper') {

        // Giấy ấm: lưới kem nhạt + 2 mảng glow cam/hồng đào + vignette rất nhẹ.
        ctx.save();
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        const t = (typeof currentFrameTime === 'number' ? currentFrameTime : 0);
        const wg = [
            { x: 0.8, y: 0.16, r: 560, c: '250,176,105', a: 0.16 },
            { x: 0.15, y: 0.78, r: 620, c: '255,205,150', a: 0.13 },
            { x: 0.55, y: 0.5, r: 700, c: '255,230,200', a: 0.10 },
        ];
        wg.forEach((b, i) => {
            const bx = b.x * W + Math.sin(t * 0.1 + i * 2) * 24;
            const by = b.y * H + Math.cos(t * 0.08 + i) * 20;
            const g = ctx.createRadialGradient(bx, by, 0, bx, by, b.r);
            g.addColorStop(0, 'rgba(' + b.c + ',' + b.a + ')');
            g.addColorStop(1, 'rgba(' + b.c + ',0)');
            ctx.fillStyle = g;
            ctx.beginPath(); ctx.arc(bx, by, b.r, 0, Math.PI * 2); ctx.fill();
        });
        ctx.strokeStyle = 'rgba(180,140,90,0.07)';
        ctx.lineWidth = 1;
        const wgs = 96;
        for (let x = 0; x < W; x += wgs) {
            ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
        }
        for (let y = 0; y < H; y += wgs) {
            ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
        }
        const wv = ctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.5, W / 2, H / 2, Math.max(W, H) * 0.85);
        wv.addColorStop(0, 'rgba(120,80,40,0)');
        wv.addColorStop(1, 'rgba(120,80,40,0.10)');
        ctx.fillStyle = wv; ctx.fillRect(0, 0, W, H);
        ctx.restore();

    } else if (artStyle === 'techdark') {

        // Than chì editorial: lưới chéo mờ + 2 mảng glow màu ấm/lạnh + vignette.
        ctx.save();
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        const t = (typeof currentFrameTime === 'number' ? currentFrameTime : 0);
        const glows = [
            { x: 0.82, y: 0.18, r: 620, c: '251,146,60', a: 0.07 },
            { x: 0.12, y: 0.62, r: 560, c: '52,211,153', a: 0.05 },
            { x: 0.55, y: 0.92, r: 520, c: '34,211,238', a: 0.045 },
        ];
        glows.forEach((b, i) => {
            const bx = b.x * W + Math.sin(t * 0.12 + i * 2) * 30;
            const by = b.y * H + Math.cos(t * 0.1 + i) * 24;
            const g = ctx.createRadialGradient(bx, by, 0, bx, by, b.r);
            g.addColorStop(0, 'rgba(' + b.c + ',' + b.a + ')');
            g.addColorStop(1, 'rgba(' + b.c + ',0)');
            ctx.fillStyle = g;
            ctx.beginPath(); ctx.arc(bx, by, b.r, 0, Math.PI * 2); ctx.fill();
        });
        // lưới chéo mờ (xoay nhẹ quanh tâm)
        ctx.save();
        ctx.translate(W / 2, H / 2);
        ctx.rotate(-0.18);
        ctx.strokeStyle = 'rgba(255,255,255,0.035)';
        ctx.lineWidth = 1;
        const span = Math.max(W, H) * 1.5, gsz = 120;
        for (let x = -span; x < span; x += gsz) {
            ctx.beginPath(); ctx.moveTo(x, -span); ctx.lineTo(x, span); ctx.stroke();
        }
        for (let y = -span; y < span; y += gsz) {
            ctx.beginPath(); ctx.moveTo(-span, y); ctx.lineTo(span, y); ctx.stroke();
        }
        ctx.restore();
        // vignette đậm mép
        const vg = ctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.4, W / 2, H / 2, Math.max(W, H) * 0.82);
        vg.addColorStop(0, 'rgba(0,0,0,0)');
        vg.addColorStop(1, 'rgba(0,0,0,0.42)');
        ctx.fillStyle = vg; ctx.fillRect(0, 0, W, H);
        ctx.restore();

    } else if (artStyle === 'neonsketch') {

        // Blueprint neon: lưới xanh rêu + mảng glow olive trôi chậm + vạch
        // neon mảnh trên/dưới — nền cho nhân vật que neon vẽ tay.
        ctx.save();
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        const t = (typeof currentFrameTime === 'number' ? currentFrameTime : 0);
        // mảng glow olive
        const GB = [
            { x: 0.5, y: 0.3, r: 620, a: 0.10 },
            { x: 0.2, y: 0.75, r: 480, a: 0.07 },
            { x: 0.85, y: 0.6, r: 430, a: 0.06 },
        ];
        GB.forEach((b, i) => {
            const bx = b.x * W + Math.sin(t * 0.15 + i * 2) * 26;
            const by = b.y * H + Math.cos(t * 0.12 + i) * 20;
            const g = ctx.createRadialGradient(bx, by, 0, bx, by, b.r);
            g.addColorStop(0, 'rgba(140,170,50,' + b.a + ')');
            g.addColorStop(1, 'rgba(140,170,50,0)');
            ctx.fillStyle = g;
            ctx.beginPath(); ctx.arc(bx, by, b.r, 0, Math.PI * 2); ctx.fill();
        });
        // lưới blueprint
        ctx.strokeStyle = 'rgba(163,230,53,0.075)';
        ctx.lineWidth = 1;
        const gs = 64;
        for (let x = 0; x < W; x += gs) {
            ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
        }
        for (let y = 0; y < H; y += gs) {
            ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
        }
        // vạch neon mảnh: trên (vàng→xanh) + dưới trái (cyan)
        const tl = ctx.createLinearGradient(MX, 0, W * 0.7, 0);
        tl.addColorStop(0, '#fde047'); tl.addColorStop(1, 'rgba(163,230,53,0.15)');
        ctx.fillStyle = tl;
        ctx.shadowColor = '#fde047'; ctx.shadowBlur = 10;
        ctx.fillRect(MX, 64, W * 0.62 - MX, 4);
        ctx.shadowColor = '#38bdf8';
        ctx.fillStyle = 'rgba(56,189,248,0.9)';
        ctx.fillRect(MX, H - 68, 190, 4);
        ctx.shadowBlur = 0;
        // vignette tối mép
        const vg = ctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.45, W / 2, H / 2, Math.max(W, H) * 0.8);
        vg.addColorStop(0, 'rgba(0,0,0,0)');
        vg.addColorStop(1, 'rgba(0,0,0,0.34)');
        ctx.fillStyle = vg; ctx.fillRect(0, 0, W, H);
        ctx.restore();

    } else if (artStyle === 'sketchnote') {

        ctx.save();

        ctx.setTransform(1, 0, 0, 1, 0, 0);

        // 1. Grid pattern representing school notebook

        ctx.strokeStyle = 'rgba(30, 41, 59, 0.04)';

        ctx.lineWidth = 1.2;

        const gridS = 40;

        for (let x = 0; x < W; x += gridS) {

            ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();

        }

        for (let y = 0; y < H; y += gridS) {

            ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();

        }

        // 2. High-quality paper grain noise textures

        ctx.fillStyle = 'rgba(0, 0, 0, 0.015)';

        for (let j = 0; j < 2500; j++) {

            const rx = Math.random() * W;

            const ry = Math.random() * H;

            ctx.fillRect(rx, ry, Math.random() * 2 + 1, Math.random() * 2 + 1);

        }

        // 3. Cute hand-drawn margin separator line on the left side

        ctx.strokeStyle = 'rgba(220, 38, 38, 0.15)';

        ctx.lineWidth = 2.5;

        ctx.beginPath();

        ctx.moveTo(MX - 18, 0);

        ctx.bezierCurveTo(MX - 22, H * 0.3, MX - 14, H * 0.7, MX - 20, H);

        ctx.stroke();

        ctx.restore();

    }

    // ── PHỤ ĐỀ — vẽ SAU CÙNG: sau elements, sau mọi lớp wash của phong cách.
    // Nhờ vậy phụ đề KHÔNG bị vignette của mathnoir làm tối, không bị lớp
    // watercolor/sketch nhân màu, và KHÔNG dính Ken Burns (applyMnKenBurns chỉ
    // sống trong save/restore của renderUnifiedElements).
    // Trạng thái đặt TƯỜNG MINH chứ không tin vào restore(): custom_js do AI
    // sinh có thể để lệch ngăn xếp save/restore → transform/alpha rò rỉ sang đây.
    if (SUB_ENGINE) {

        ctx.setTransform(1, 0, 0, 1, 0, 0);

        ctx.globalAlpha = 1;

        ctx.globalCompositeOperation = 'source-over';

        ctx.shadowBlur = 0;

        ctx.shadowColor = 'rgba(0,0,0,0)';

        ctx.shadowOffsetX = 0;

        ctx.shadowOffsetY = 0;

        ctx.setLineDash([]);

        ctx.filter = 'none';

        ctx.save();

        try { drawSubtitle(currentTime); } finally { ctx.restore(); }

    }

}

/**

 * Estimate total height of a unified element list (pre-render pass).

 * Used to vertically center content when it doesn't fill the screen.

 */

function estimateTotalHeight(els) {

    let h = 0;

    let i = 0;

    while (i < els.length) {

        const el = els[i].el;

        if (el.type === 'gap') { h += 18; i++; continue; }

        if (el.type === 'box') {

            let j = i + 1;

            let innerH = 0;

            while (j < els.length && ['text','math_calc','reveal'].includes(els[j].el.type)) {

                innerH += estimateElementHeight(els[j].el);

                j++;

            }

            h += innerH + 40 + 8; // padding + gap

            i = j;

            continue;

        }

        h += estimateElementHeight(el);

        i++;

    }

    return h;

}

function estimateElementHeight(el) {

    if (!el) return 0;

    switch (el.type) {

        case 'text':    return measureTextHeight(el) + 6;

        case 'list':    return measureTextHeight(el) + 8;

        case 'timeline': return measureTextHeight(el) + 8;

        case 'math_calc': return measureTextHeight(el) + 10;

        case 'reveal':  return (el.fontSize || 44) * 1.4 + 6;

        case 'line':    return 18;

        case 'icon':    return (el.size || 64) + 10;

        case 'arrow':   return 30;

        case 'image': {

          if (el.src && IMAGE_CACHE[el.src]) {

              const img = IMAGE_CACHE[el.src];

              const availW = W - MX * 2;

              const maxH = Math.min(Math.round(availW * 0.75), Math.round(H * 0.5));

              const ratio = Math.min(availW / img.width, maxH / img.height);

              return Math.round(img.height * ratio) + 24;

          }

          return Math.min(Math.round((W - MX * 2) * 0.75), Math.round(H * 0.5)) + 24;

        }

        case 'image_generation': return 380 + 24; // placeholder height

        case 'gap':     return 18;

        case 'custom_js': {

          const baseH = (el.height !== undefined && el.height !== null) ? el.height : (() => {

              const isPortrait = H > W;

              const sc = isPortrait ? (W / 360) : (H / 600);

              const frameH = isPortrait ? (340 * sc) : (200 * sc);

              return frameH + 20 + 6;

          })();

          const scaleFactor = (el.fontSize || 40) / 40;

          return baseH * scaleFactor;

        }

        default:        return 0;

    }

}

/**

 * Calculate the optimal startY to vertically center content.

 * Keeps a minimum top margin of minY.

 * Only centers if content height < 60% of available height (otherwise top-align).

 */

function calcCenteredStartY(els, minY, maxY) {

    const available = maxY - minY;

    const totalH = estimateTotalHeight(els);

    const topAlignThreshold = (H > W) ? 0.90 : 0.75;

    if (totalH >= available * topAlignThreshold) return minY; // content fills enough space — top align

    // Center in available space, with minimum top margin

    const centered = minY + (available - totalH) / 2;

    const maxClampFactor = (H > W) ? 0.32 : 0.18;

    return Math.max(minY, Math.min(centered, minY + available * maxClampFactor)); // clamp: allow vertical layouts to go down to 32% for balanced centering

}

function renderGeometryZone(geoElsObj, startY, zoneH) {

    if (geoElsObj.length === 0) return 0;

    zoneH = zoneH || 400;

    // geoElsObj is array of {el, rawP}

    const pad = 40;

    const boxW = W - MX * 2;

    ctx.save();

    // Draw zone background

    roundRect(MX, startY, boxW, zoneH, 16);

    ctx.fillStyle = T.geoBg || '#1a1a2e'; 

    ctx.fill();

    ctx.strokeStyle = T.geoBorder || '#3a3a5a';

    ctx.lineWidth = 2;

    ctx.stroke();

    // Mapping normalized (0.0 - 1.0) coords to zone coords

    // Use the inner area with padding

    const innerW = boxW - pad * 2;

    const innerH = zoneH - pad * 2;

    const mapX = (x) => MX + pad + x * innerW;

    const mapY = (y) => startY + pad + y * innerH;

    // Build point lookup

    const pts = {};

    for (const g of geoElsObj) {

        if (g.el.type === 'point') {

            pts[g.el.id] = { x: mapX(g.el.x), y: mapY(g.el.y), el: g.el, rawP: g.rawP };

        }

    }

    // 1. Draw segments

    for (const g of geoElsObj) {

        if (g.el.type === 'segment') {

            const p1 = pts[g.el.from], p2 = pts[g.el.to];

            if (p1 && p2) {

                ctx.globalAlpha = easeOut(Math.min(g.rawP * 2, 1));

                ctx.beginPath();

                ctx.moveTo(p1.x, p1.y);

                ctx.lineTo(p2.x, p2.y);

                ctx.strokeStyle = g.el.color === 'highlight' ? T.highlight

                                : g.el.color === 'red'       ? '#ef4444'

                                : g.el.color === 'green'     ? '#22c55e'

                                : (g.el.color || '#ffffff');

                ctx.lineWidth = 5;

                ctx.lineCap = 'round';

                ctx.stroke();

            }

        }

    }

    // 2. Draw right angles

    for (const g of geoElsObj) {

        if (g.el.type === 'right_angle') {

            const v = pts[g.el.vertex], p1 = pts[g.el.from], p2 = pts[g.el.to];

            if (v && p1 && p2) {

                ctx.globalAlpha = easeOut(Math.min(g.rawP * 2, 1));

                // Unit vectors

                const dx1 = p1.x - v.x, dy1 = p1.y - v.y;

                const len1 = Math.hypot(dx1, dy1);

                const u1x = dx1 / len1, u1y = dy1 / len1;

                const dx2 = p2.x - v.x, dy2 = p2.y - v.y;

                const len2 = Math.hypot(dx2, dy2);

                const u2x = dx2 / len2, u2y = dy2 / len2;

                const size = Math.min(innerW, innerH) * 0.06; // proportional

                ctx.beginPath();

                ctx.moveTo(v.x + u1x * size, v.y + u1y * size);

                ctx.lineTo(v.x + u1x * size + u2x * size, v.y + u1y * size + u2y * size);

                ctx.lineTo(v.x + u2x * size, v.y + u2y * size);

                ctx.strokeStyle = T.highlight || '#eab308';

                ctx.lineWidth = 4;

                ctx.lineJoin = 'round';

                ctx.stroke();

            }

        }

    }

    // 3. Draw points & labels

    for (const id in pts) {

        const p = pts[id];

        ctx.globalAlpha = easeOut(Math.min(p.rawP * 2, 1));

        const pColor = p.el.color === 'highlight' ? T.highlight

                     : p.el.color === 'red'       ? '#ef4444'

                     : p.el.color === 'green'      ? '#22c55e'

                     : '#ffffff';

        // Outer glow

        ctx.beginPath();

        ctx.arc(p.x, p.y, 10, 0, Math.PI * 2);

        ctx.fillStyle = pColor + '40';

        ctx.fill();

        ctx.beginPath();

        ctx.arc(p.x, p.y, 6, 0, Math.PI * 2);

        ctx.fillStyle = pColor;

        ctx.fill();

        if (p.el.label) {

            ctx.fillStyle = pColor;

            ctx.font = 'bold 28px ' + T.font;

            ctx.textAlign = 'center';

            ctx.textBaseline = 'bottom';

            ctx.fillText(p.el.label, p.x, p.y - 14);

        }

    }

    ctx.restore();

    return zoneH + 20;

}

function drawHighlights(currentTime) {

    const activeWord = getActiveWord(currentTime);

    if (!activeWord) return;

    const steps = script.steps, tSteps = timing.steps;

    let renderFrom = 0;

    for (let i = steps.length - 1; i >= 0; i--) {

        const ts = tSteps[i];

        if (ts && currentTime >= ts.start && steps[i].clear) { renderFrom = i; break; }

    }

    const { nonGeoEls } = buildUnifiedLayout(currentTime, renderFrom, steps, tSteps);

    let cursorY = 80;

    _measureAndHighlightUnified(nonGeoEls, cursorY, activeWord);

}

function _measureAndHighlightUnified(unifiedEls, startY, activeWord) {

    let cursorY = startY;

    let i = 0;

    while (i < unifiedEls.length) {

        const u = unifiedEls[i];

        const el = u.el;

        if (el.type === 'gap') {

            cursorY += 18;

            i++;

            continue;

        }

        if (el.type === 'box') {

            const inner = [];

            let j = i + 1;

            while (j < unifiedEls.length && (unifiedEls[j].el.type === 'text' || unifiedEls[j].el.type === 'list' || unifiedEls[j].el.type === 'math_calc' || unifiedEls[j].el.type === 'reveal')) {

                inner.push(unifiedEls[j]);

                j++;

            }

            const pad = 20;

            let iy = cursorY + pad;

            let boxH = pad * 2;

            for (const iu of inner) boxH += _measureElH(iu.el) + 6;

            for (const iu of inner) {

                const consumed = _highlightEl(iu.el, iy, activeWord);

                iy += consumed;

            }

            cursorY += boxH + 8;

            i = j;

            continue;

        }

        const consumed = _highlightEl(el, cursorY, activeWord);

        cursorY += consumed || _measureElH(el) + 6;

        i++;

    }

    return cursorY;

}

function _measureElH(el) {

    const contentW = W - MX * 2;

    if (el.type === 'math_calc') {

        const fs = el.fontSize || 48;

        const lines = (el.operands || []).length + (el.result ? 1 : 0);

        return lines * (fs * 1.3) + 40 + 6;

    }

    if (el.type === 'text') {

        const fs = el.fontSize || 40;

        const font = `${el.bold ? 'bold ' : ''}${fs}px ${T.font}`;

        const contentWFixed = W - MX * 2 - 60;

        let h = 0;

        for (const raw of (el.text || '').split('\n')) {

            h += wrapText(raw, contentWFixed, font).length * fs * 1.4;

        }

        return h + 6;

    }

    if (el.type === 'list') {

        const fs = el.fontSize || 36;

        const font = `${el.bold ? 'bold ' : ''}${fs}px ${T.font}`;

        ctx.font = font;

        const bullet = el.bullet || '•';

        const bw = ctx.measureText(bullet + ' ').width;

        const contentWFixed = W - MX * 2 - 60;

        let h = 0;

        for (const item of (el.items || [])) {

            h += wrapText(item, contentWFixed - bw, font).length * fs * 1.4 + 10;

        }

        return h + 6;

    }

    if (el.type === 'timeline') {

        const fs = el.fontSize || 32, font = `${fs}px ${T.font}`;

        const items = el.items || [];

        const isHoriz = true; // render timeline ngang cho mọi tỷ lệ màn hình

        if (isHoriz) {

            const itemW = (W - MX * 2) / Math.max(1, items.length);

            let maxH = 0;

            ctx.font = font;

            for (const item of items) {

                let lineH = wrapText(item.event || '', itemW - 20, font).length * fs * 1.4;

                maxH = Math.max(maxH, lineH);

            }

            return maxH + fs + 80;

        } else {

            const lineX = MX + 40;

            let totalH = 0;

            ctx.font = font;

            for (const item of items) {

                totalH += fs * 1.4 + 10;

                totalH += wrapText(item.event || '', W - lineX - 30 - MX, font).length * fs * 1.4;

                totalH += 30;

            }

            return totalH;

        }

    }

    if (el.type === 'custom_js') {

        const isPortrait = H > W;

        const sc = isPortrait ? (W / 360) : (H / 600);

        const frameH = isPortrait ? (340 * sc) : (200 * sc);

        return frameH + 20 + 6;

    }

    if (el.type === 'icon') return (el.size || 64) + 10;

    if (el.type === 'line') return 18;

    if (el.type === 'arrow') return 30;

    if (el.type === 'image') {

        if (el.src && IMAGE_CACHE[el.src]) {

            const img = IMAGE_CACHE[el.src];

            const maxW = el.width || (W - MX * 2);

            const maxH = Math.min(el.height || 600, 600);

            const ratio = Math.min(maxW / img.width, maxH / img.height);

            return Math.round(img.height * ratio) + 24;

        }

        return (el.height || 600) + 24;

    }

    return 0;

}

/** Try to find & highlight active word inside a single element. Returns height consumed. */

function _highlightEl(el, y, activeWord) {

    const h = _measureElH(el);

    if (el.type === 'math_calc') {

        const fs = el.fontSize || 48;

        const cx = W / 2 + 80;

        let cy = y + 10;

        const ops = el.operands || [];

        for (let k = 0; k < ops.length; k++) {

            const opNorm = normalizeWord(ops[k]);

            if (opNorm === activeWord.norm || activeWord.norm.includes(opNorm) || opNorm.includes(activeWord.norm)) {

                // Measure text width with monospace font

                ctx.font = `bold ${fs}px 'Courier New', Consolas, monospace`;

                const tw = ctx.measureText(ops[k]).width;

                drawHighlightBox(cx - tw, cy, tw, fs, '#FFD700');

            }

            cy += fs * 1.3;

        }

        // Result highlight

        cy += 28; // separator line

        if (el.result) {

            const resNorm = normalizeWord(el.result);

            if (resNorm === activeWord.norm || activeWord.norm.includes(resNorm) || resNorm.includes(activeWord.norm)) {

                ctx.font = `bold ${fs}px 'Courier New', Consolas, monospace`;

                const tw = ctx.measureText(el.result).width;

                drawHighlightBox(cx - tw, cy, tw, fs, '#00FF88');

            }

        }

        return h;

    }

    if (el.type === 'text') {

        const fs = el.fontSize || 40;

        const font = `${el.bold ? 'bold ' : ''}${fs}px ${T.font}`;

        const align = el.align || 'left';

        ctx.font = font;

        const contentWFixed = W - MX * 2 - 60;

        let lineY = y;

        for (const raw of (el.text || '').split('\n')) {

            const wrapped = wrapText(raw, contentWFixed, font);

            for (const line of wrapped) {

                // Check if active word appears in this line

                const lineNorm = normalizeWord(line);

                const wordsInLine = line.split(' ');

                let xOff = align === 'center' ? W/2 - measureMathAwareText(line, font)/2

                         : align === 'right'  ? W - MX - measureMathAwareText(line, font)

                         : MX;

                for (const w of wordsInLine) {

                    const wNorm = normalizeWord(w);

                    const ww = measureMathAwareText(w, font);

                    if (wNorm && wNorm === activeWord.norm) {

                        drawHighlightBox(xOff, lineY, ww, fs * 0.9, T.hlColor);

                    }

                    xOff += ww + measureMathAwareText(' ', font);

                }

                lineY += fs * 1.4;

            }

        }

        return h;

    }

    if (el.type === 'list') {

        const fs = el.fontSize || 36;

        const font = `${el.bold ? 'bold ' : ''}${fs}px ${T.font}`;

        const align = el.align || 'center';

        ctx.font = font;

        const bullet = el.bullet || '•';

        const bulletW = ctx.measureText(bullet + ' ').width;

        const contentWFixed = W - MX * 2 - 60;

        let maxW = 0;

        for (const item of (el.items || [])) {

            for (const line of wrapText(item, contentWFixed - bulletW, font)) {

                maxW = Math.max(maxW, ctx.measureText(line).width);

            }

        }

        const startX = (align === 'center') ? (W / 2 - (bulletW + maxW) / 2) : MX;

        let lineY = y;

        for (const item of (el.items || [])) {

            for (const line of wrapText(item, contentWFixed - bulletW, font)) {

                const wordsInLine = line.split(' ');

                let xOff = startX + bulletW;

                for (const w of wordsInLine) {

                    const wNorm = normalizeWord(w);

                    const ww = ctx.measureText(w).width;

                    if (wNorm && wNorm === activeWord.norm) {

                        drawHighlightBox(xOff, lineY, ww, fs * 0.9, T.hlColor);

                    }

                    xOff += ww + ctx.measureText(' ').width;

                }

                lineY += fs * 1.4;

            }

            lineY += 10;

        }

        return h;

    }

    if (el.type === 'timeline') {

        const fs = el.fontSize || 32, font = `${fs}px ${T.font}`;

        const items = el.items || [];

        const isHoriz = true; // render timeline ngang cho mọi tỷ lệ màn hình

        if (isHoriz) {

            const lineY = y + fs + 20;

            const itemW = (W - MX * 2) / Math.max(1, items.length);

            ctx.font = font;

            for (let i = 0; i < items.length; i++) {

                const item = items[i];

                const x = items.length === 1 ? W/2 : MX + itemW/2 + i * itemW;

                let textY = lineY + 20;

                const lines = wrapText(item.event || '', itemW - 20, font);

                for (const line of lines) {

                    const wordsInLine = line.split(' ');

                    let xOff = x - ctx.measureText(line).width / 2;

                    for (const w of wordsInLine) {

                        const wNorm = normalizeWord(w);

                        const ww = ctx.measureText(w).width;

                        if (wNorm && wNorm === activeWord.norm) {

                            drawHighlightBox(xOff, textY, ww, fs * 0.9, T.hlColor);

                        }

                        xOff += ww + ctx.measureText(' ').width;

                    }

                    textY += fs * 1.4;

                }

            }

        } else {

            const lineX = MX + 40;

            let curY = y;

            ctx.font = font;

            for (let i = 0; i < items.length; i++) {

                const item = items[i];

                let textY = curY + fs * 1.4 + 10;

                const lines = wrapText(item.event || '', W - lineX - 30 - MX, font);

                for (const line of lines) {

                    const wordsInLine = line.split(' ');

                    let xOff = lineX + 30;

                    for (const w of wordsInLine) {

                        const wNorm = normalizeWord(w);

                        const ww = ctx.measureText(w).width;

                        if (wNorm && wNorm === activeWord.norm) {

                            drawHighlightBox(xOff, textY, ww, fs * 0.9, T.hlColor);

                        }

                        xOff += ww + ctx.measureText(' ').width;

                    }

                    textY += fs * 1.4;

                }

                curY += (fs * 1.4 + 10) + (lines.length * fs * 1.4) + 30;

            }

        }

        return h;

    }

    return h;

}

// ── Main loop ───────────────────────────────────────────────────

const MODE = args.mode || 'pipe'; // 'pipe' (fast, direct to ffmpeg) or 'frames' (PNG files)

const IMAGE_CACHE = {};

global.IMAGE_CACHE = IMAGE_CACHE;

try { global.Image = require('canvas').Image; } catch(e) {}


(async () => {

    const IMAGE_MAX_BYTES = 20 * 1024 * 1024;

    function resolveGalleryImage(src) {
        if (typeof src !== 'string' || !src.startsWith('gallery:')) {
            throw new Error(`image_asset_error: unsupported image source '${String(src).slice(0, 120)}'`);
        }
        const relative = src.slice('gallery:'.length);
        if (!/^[A-Za-z0-9][A-Za-z0-9._-]*(?:\/[A-Za-z0-9][A-Za-z0-9._-]*)*$/.test(relative)) {
            throw new Error(`image_asset_error: invalid gallery path '${relative}'`);
        }
        const lower = relative.toLowerCase();
        if (!(lower.endsWith('.png') || lower.endsWith('.jpg') || lower.endsWith('.jpeg'))) {
            throw new Error(`image_asset_error: unsupported image extension '${relative}'`);
        }
        const configuredRoot = process.env.TUBECRAFT_GALLERY_DIR || path.join(process.cwd(), 'data', 'gallery');
        if (!fs.existsSync(configuredRoot)) {
            throw new Error('image_asset_error: gallery directory is unavailable');
        }
        const galleryRoot = fs.realpathSync(configuredRoot);
        const candidates = [path.resolve(galleryRoot, ...relative.split('/'))];
        if (!relative.includes('/')) {
            candidates.push(path.resolve(galleryRoot, 'items', relative));
        }
        for (const candidate of candidates) {
            if (!fs.existsSync(candidate)) continue;
            const resolved = fs.realpathSync(candidate);
            const withinGallery = path.relative(galleryRoot, resolved);
            if (
                withinGallery.startsWith('..' + path.sep)
                || withinGallery === '..'
                || path.isAbsolute(withinGallery)
            ) {
                throw new Error('image_asset_error: gallery path escapes its root');
            }
            const stat = fs.statSync(resolved);
            if (!stat.isFile()) {
                throw new Error('image_asset_error: gallery asset is not a file');
            }
            if (stat.size > IMAGE_MAX_BYTES) {
                throw new Error('image_asset_error: gallery asset is too large');
            }
            return resolved;
        }
        throw new Error(`image_asset_error: gallery asset not found '${relative}'`);
    }

    async function preloadOne(src) {
        if (!src || IMAGE_CACHE[src] || !loadImage) return;
        const localPath = resolveGalleryImage(src);
        process.stderr.write(`[Renderer] Loading gallery image: ${src}\n`);
        const img = await loadImage(localPath);
        IMAGE_CACHE[src] = img;
        process.stderr.write(`[Renderer] Image loaded OK: ${localPath}\n`);
    }

    // Preload only declarative local gallery assets. Trusted scene code is not
    // scanned for URLs: parameters must not become a second file/network ingress.

    for (const step of script.steps || []) {

        for (const el of step.elements || []) {

            if (el.type === 'image' && el.src) {

                await preloadOne(el.src);

            }

        }

    }

    // Preload Twemoji PNGs for every emoji used in the script so drawEmoji can
    // render full-color emoji (this was defined but never invoked → emojis were
    // silently falling back to monochrome font glyphs).
    try { await preloadEmojis(script); } catch (e) {
        process.stderr.write(`[Emoji] Preload failed: ${e.message}\n`);
    }

    // ── Kho sprite của template (ui.sprite) ──────────────────────────────
    // Nhân vật/hình vẽ sẵn dạng PNG trong gói template — AI chỉ gọi tên,
    // không phải vẽ. Quét: <TUBECRAFT_TEMPLATE_CACHE>/<pack>/sprites/*.png (kho
    // online) + <app>/assets/sprites/<bộ>/*.png (đóng gói kèm app).
    global.SPRITES = {};
    try {
        const spriteRoots = [];
        if (process.env.TUBECRAFT_TEMPLATE_CACHE) spriteRoots.push(process.env.TUBECRAFT_TEMPLATE_CACHE);
        spriteRoots.push(path.join(__dirname, '..', 'assets', 'sprites'));
        for (const root of spriteRoots) {
            if (!fs.existsSync(root)) continue;
            for (const sub of fs.readdirSync(root)) {
                for (const dir of [path.join(root, sub, 'sprites'), path.join(root, sub)]) {
                    let files = [];
                    try { files = fs.readdirSync(dir); } catch (e) { continue; }
                    for (const f of files) {
                        if (!f.endsWith('.png')) continue;
                        const key = f.slice(0, -4);
                        if (global.SPRITES[key]) continue;
                        try { global.SPRITES[key] = await loadImage(path.join(dir, f)); } catch (e) {}
                    }
                }
            }
        }
        const nSpr = Object.keys(global.SPRITES).length;
        if (nSpr) process.stderr.write(`[Sprites] loaded ${nSpr}\n`);
    } catch (e) {
        process.stderr.write(`[Sprites] scan failed: ${e.message}\n`);
    }

    const totalDur = timing.total_duration || 30;

    const totalFrames = Math.ceil(totalDur * FPS);

    const startF = parseInt(args.startFrame || '0');

    const endF = parseInt(args.endFrame || String(totalFrames));

    process.stderr.write(`[Renderer v5] rendering range: ${startF} to ${endF} (total: ${totalFrames} frames), ${FPS}fps, ${totalDur}s, mode=${MODE}\n`);

    // ── PREVIEW MODE: render MỘT frame PNG tại previewTime rồi thoát ──
    if (MODE === 'preview') {
        const t = parseFloat(args.previewTime || String(totalDur * 0.9));
        renderFrame(t);
        const outFile = args.outputFile || path.join(outputDir, 'preview.png');
        fs.writeFileSync(outFile, canvas.toBuffer('image/png'));
        console.log(JSON.stringify({ type: 'done', status: 'success', preview: outFile, time: t }));
        return;
    }

    if (MODE === 'pipe') {

        // ── PIPE MODE: spawn ffmpeg, pipe raw RGBA pixels directly ──

        const audioPath = args.audio || '';

        const outputFile = args.outputFile || path.join(outputDir, 'output.mp4');

        const { spawn } = require('child_process');

        // Build ffmpeg command

        const ffArgs = [

            '-y',

            '-f', 'rawvideo',

            '-pix_fmt', 'bgra',

            '-s', `${W}x${H}`,

            '-r', String(FPS),

            '-i', 'pipe:0',           // video from stdin

        ];

        // Add audio if available

        if (audioPath && fs.existsSync(audioPath)) {

            ffArgs.push('-i', audioPath);

            ffArgs.push('-c:a', 'aac', '-b:a', '128k');

        }

        const codec = args.codec || 'libx264';

        const preset = args.preset || 'medium';

        const extraArgs = args.ffmpegExtra ? args.ffmpegExtra.split(' ') : [];

        ffArgs.push(

            '-c:v', codec,

            '-preset', preset,

            ...extraArgs,

            '-pix_fmt', 'yuv420p',

            '-shortest',

            outputFile

        );

        const ffmpeg = spawn('ffmpeg', ffArgs, { stdio: ['pipe', 'pipe', 'pipe'] });

        ffmpeg.stderr.on('data', (d) => {

            process.stderr.write(`[FFmpeg] ${d.toString()}`);

        });

        let ffmpegDone = new Promise((resolve, reject) => {

            ffmpeg.on('close', (code) => {

                if (code === 0) resolve();

                else reject(new Error(`FFmpeg exited with code ${code}`));

            });

            ffmpeg.on('error', reject);

        });

        // Write with backpressure: wait for drain if buffer is full

        function writeFrame(buf) {

            return new Promise((resolve, reject) => {

                const ok = ffmpeg.stdin.write(buf);

                if (ok) {

                    resolve();

                    return;

                }

                // A GPU encoder/driver can remain alive while no longer consuming
                // stdin. Without a deadline this leaves Node, the export dialog and
                // the final file stuck forever. Fail the pipe so Python can use its
                // existing frames + CPU fallback path.
                let settled = false;

                const cleanup = () => {

                    clearTimeout(timer);

                    ffmpeg.stdin.off('drain', onDrain);

                    ffmpeg.stdin.off('error', onError);

                };

                const finish = (error) => {

                    if (settled) return;

                    settled = true;

                    cleanup();

                    if (error) reject(error);

                    else resolve();

                };

                const onDrain = () => finish();

                const onError = (error) => finish(error);

                const timer = setTimeout(() => {

                    finish(new Error('FFmpeg stopped consuming frames for 30 seconds'));

                    try { ffmpeg.kill('SIGKILL'); } catch (e) {}

                }, 30000);

                ffmpeg.stdin.once('drain', onDrain);

                ffmpeg.stdin.once('error', onError);

            });

        }

        // Render frames and pipe raw pixel data

        let pipeError = null;

        ffmpeg.stdin.on('error', (err) => { pipeError = err; });

        for (let f = startF; f < endF; f++) {

            if (pipeError) {

                process.stderr.write(`[Renderer] Pipe broken at frame ${f}: ${pipeError.message}\n`);

                break;

            }

            renderFrame(f / FPS);

            // node-canvas 'raw' outputs BGRA natively — ffmpeg now expects bgra, no swap needed

            const buf = canvas.toBuffer('raw');

            try { await writeFrame(buf); } catch(e) { pipeError = e; break; }

            if (f % 30 === 0 || f === endF - 1) {

                const chunkTotal = endF - startF;

                const chunkCurrent = f - startF;

                const pct = Math.round((chunkCurrent / chunkTotal) * 100);

                console.log(JSON.stringify({

                    type: 'progress',

                    percent: pct,

                    frame: f,

                    startFrame: startF,

                    endFrame: endF,

                    total: totalFrames,

                    message: `Pipe ${f}/${totalFrames} (${pct}%)`

                }));

            }

        }

        ffmpeg.stdin.end();

        try { await ffmpegDone; } catch(e) {

            process.stderr.write(`[Renderer] FFmpeg error: ${e.message}\n`);

            // Report error so Python can fallback to CPU

            console.log(JSON.stringify({ type: 'error', message: `FFmpeg pipe failed: ${e.message}` }));

            process.exit(1);

        }

        console.log(JSON.stringify({ type: 'done', status: 'success', totalFrames, outputFile }));

    } else {

        // ── FRAMES MODE: write JPEG files (much faster than PNG) ──

        for (let f = startF; f < endF; f++) {

            renderFrame(f / FPS);

            const num = String(f).padStart(6, '0');

            // Use JPEG instead of PNG: ~3x faster to write, GPU encoder reads equally fast

            fs.writeFileSync(path.join(outputDir, `frame_${num}.jpg`), canvas.toBuffer('image/jpeg', { quality: 0.92 }));

            if (f % 30 === 0 || f === endF - 1) {

                const chunkTotal = endF - startF;

                const chunkCurrent = f - startF;

                const pct = Math.round((chunkCurrent / chunkTotal) * 100);

                console.log(JSON.stringify({
                    type: 'progress',
                    percent: pct,
                    frame: f,
                    startFrame: startF,
                    endFrame: endF,
                    total: totalFrames,
                    message: `Frame ${f}/${totalFrames} (${pct}%)`
                }));

            }

        }

        console.log(JSON.stringify({ type: 'done', status: 'success', totalFrames }));

    }

})();
