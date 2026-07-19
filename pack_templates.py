"""pack_templates.py — Định nghĩa các template được đóng gói sẵn trong app.

Runtime đọc trực tiếp ``PACKS`` để mọi template hoạt động hoàn toàn cục bộ.
Phần publisher phía dưới chỉ là công cụ tùy chọn dành cho người phát triển.

Chạy:  python pack_templates.py

Nó sẽ, cho mỗi PACK khai báo dưới đây:
  1. Lấy thumbnail đã render sẵn ở samples/templates/<id>{,_16x9,_1x1}.png
     (thiếu thì tự render bằng core.templates.render_thumbnail).
  2. Ghi <pack_id>/pack.json (chỉ dữ liệu trình bày — client không chạy JS).
  3. Upload pack.json + thumbnail lên R2: t2studio/templates/<pack_id>/...
  4. Cập nhật t2studio/templates/index.json (danh mục gói).

Upload dùng wrangler (phiên `wrangler login`), cwd = server/worker.
"""
import json, subprocess, sys, tempfile
from pathlib import Path; BASE = Path(__file__).resolve().parent; WORKER = BASE / "server" / "worker"; SAMPLES = BASE / "samples" / "templates"; R2_BUCKET = "tubecli"; R2_PREFIX = "t2studio/templates"
_AURORA_EXEMPLARS = [{"when": "bản tin số liệu — biểu đồ cột có trục + callout đỉnh + KPI + gauge", "code": "ctx.save();\nfunction EZ(t){return 1-Math.pow(1-t,3);}\nvar P=Math.max(0,Math.min(1,stepProgress*3.2));\nvar cx=W/2, x=80, y=cursorY+8, w=W-160;\nui.glass(x,y,w,880,{accent:'#2563eb'});\nui.chip(cx,y+70,'BẢN TIN KINH TẾ',{color:'#2563eb',size:24});\nui.title(cx,y+156,'Xuất khẩu tăng kỷ lục',{size:54,from:'#2563eb',to:'#0284c7'});\n/* hero: biểu đồ cột THẬT — trục đáy, cột mọc dần, callout neo vào đỉnh */\nvar vals=[0.35,0.5,0.42,0.66,0.9], bw=92, gap=42,\n    bx=cx-(vals.length*(bw+gap)-gap)/2, base=y+620;\nctx.strokeStyle='rgba(30,45,90,0.25)'; ctx.lineWidth=2;\nctx.beginPath(); ctx.moveTo(x+70,base); ctx.lineTo(x+w-70,base); ctx.stroke();\nfor(var i=0;i<vals.length;i++){\n  var p=EZ(Math.max(0,Math.min(1,P*1.6-i*0.12)));\n  var bh=340*vals[i]*p;\n  var g=ctx.createLinearGradient(0,base-bh,0,base);\n  g.addColorStop(0,'#2563eb'); g.addColorStop(1,'#93c5fd');\n  ctx.fillStyle=g;\n  ctx.beginPath(); ctx.roundRect(bx+i*(bw+gap),base-bh,bw,bh,12); ctx.fill();\n}\nvar px=bx+4*(bw+gap)+bw/2, ph=340*0.9*EZ(Math.max(0,Math.min(1,P*1.6-0.48)));\nui.chip(px,base-ph-38,'12,8 tỷ USD',{color:'#d97706',size:26});\nui.divider(x+70,x+w-70,y+664);\nui.kpi(cx-200,y+800,'+28%','so với quý trước',{color:'green',size:72});\nui.ring(cx+230,y+770,72,0.78*P,{color:'#2563eb',text:'78%'});\nctx.restore();\nreturn 900;"},
    {"when": "so sánh 2 phương án — 2 thẻ kính cao đối xứng + bar + KPI + huy hiệu VS", "code": "ctx.save();\nfunction EZ(t){return 1-Math.pow(1-t,3);}\nvar P=Math.max(0,Math.min(1,stepProgress*3.2)), sl=EZ(P);\nvar cx=W/2, y=cursorY+8, cw=(W-200)/2;\nvar lx=90-(1-sl)*60, rx=cx+10+(1-sl)*60;\nui.glass(lx,y,cw,880,{accent:'red'});\nui.glass(rx,y,cw,880,{accent:'green'});\nui.icon(lx+cw/2,y+170,'🐢',72,{color:'red'});\nui.icon(rx+cw/2,y+170,'⚡',72,{color:'green'});\nui.title(lx+cw/2,y+330,'Cách cũ',{size:44,from:'red',to:'red'});\nui.title(rx+cw/2,y+330,'Cách mới',{size:44,from:'green',to:'green'});\nui.bar(lx+50,y+400,cw-100,18,0.35*P,{color:'red'});\nui.bar(rx+50,y+400,cw-100,18,0.9*P,{color:'green'});\nui.kpi(lx+cw/2,y+580,'6 giờ','xử lý thủ công',{color:'red',size:64});\nui.kpi(rx+cw/2,y+580,'20 phút','tự động hoá',{color:'green',size:64});\nui.chip(lx+cw/2,y+740,'Tốn nhân lực',{color:'red',size:26});\nui.chip(rx+cw/2,y+740,'Chạy 24/7',{color:'green',size:26});\n/* huy hiệu VS nổi giữa hai thẻ */\nctx.fillStyle='#d97706';\nctx.beginPath(); ctx.arc(cx,y+440,44,0,Math.PI*2); ctx.fill();\nctx.fillStyle='#ffffff'; ctx.font='bold 34px sans-serif';\nctx.textAlign='center'; ctx.textBaseline='middle';\nctx.fillText('VS',cx,y+442);\nctx.restore();\nreturn 900;"},
    {"when": "quy trình nhiều bước — luồng hạt nối trạm icon dọc thẻ cao + KPI chốt", "code": "ctx.save();\nfunction EZ(t){return 1-Math.pow(1-t,3);}\nvar P=Math.max(0,Math.min(1,stepProgress*3.2));\nvar cx=W/2, x=80, y=cursorY+8, w=W-160;\nui.glass(x,y,w,880,{accent:'#0284c7'});\nui.chip(cx,y+70,'QUY TRÌNH',{color:'#0284c7',size:24});\nui.title(cx,y+156,'4 bước tự động hoá',{size:54,from:'#0284c7',to:'#2563eb'});\nvar pts=[[x+140,y+320],[x+w-140,y+430],[x+140,y+560],[x+w-140,y+660]];\nui.flow(pts,{color:'#0284c7',n:4});\nvar icons=['📥','🧠','⚙️','🚀'],\n    labs=['Thu thập dữ liệu','Phân tích','Xử lý tự động','Bứt phá'];\nfor(var i=0;i<4;i++){\n  var ap=EZ(Math.max(0,Math.min(1,P*1.8-i*0.18)));\n  if(ap<=0)continue;\n  ctx.save(); ctx.globalAlpha=ap;\n  ui.icon(pts[i][0],pts[i][1],icons[i],58,{color:'#0284c7'});\n  var tx=pts[i][0]+(pts[i][0]<cx?190:-190);\n  ui.chip(tx,pts[i][1],labs[i],{color:'#0284c7',size:26});\n  ctx.restore();\n}\nui.divider(x+70,x+w-70,y+720);\nui.kpi(cx,y+810,'x3','tốc độ ra bài',{color:'#d97706',size:68});\nctx.restore();\nreturn 900;"}]; _KEEP = ("palette", "exemplars", "variations", "scene_first", "scene_prefix", "chrome_scene", "chrome_params", "no_headline", "head_anchor", "body_anchor", "center_body", "subtitle_accent", "id", "name", "emoji", "desc", "vibe", "art_style", "title_color", "text_color", "font_family", "effect", "topic", "ai_hint", "effects")

PACKS = [{"pack_id": "tech-news", "name": "Tin Công Nghệ", "version": 6, "template_ids": ["tech_news"], "defs": {"tech_news": {"id": "tech_news", "name": "Tin Công Nghệ", "emoji": "📡", "desc": "Tin công nghệ, ra mắt sản phẩm, breaking news", "vibe": "Nền tối lưới neon, badge BREAKING, node nối cyan–xanh lá", "art_style": "cyberpunk", "title_color": "#38bdf8", "text_color": "", "font_family": "", "effect": "breaking_news", "topic": "Sự Kiện Công Nghệ", "ai_hint": "TECH-NEWS / product-launch channel. Energetic 'breaking news' tone, neon cyan/blue/emerald on a dark grid. OPEN every episode by LAYERING scenes: news_backdrop (full-bleed) + breaking_pill (badge) + gradient_title (strike old->new headline). For content steps prefer code_typing, web_window, data_river, edge_globe, metric_grid, versus_split. Fast, futuristic, hype.", "effects": ["news_backdrop", "gradient_title", "big_word", "code_typing", "web_window", "data_river"]}}},
    {"pack_id": "ai-hotlist", "name": "AI Hotlist", "version": 3, "template_ids": ["ai_hotlist"], "defs": {"ai_hotlist": {"id": "ai_hotlist", "name": "AI Hotlist", "emoji": "🔥", "desc": "Xếp hạng, top-list, review & so sánh AI / công nghệ", "vibe": "Nền tinh vân aurora + thẻ kính bảng xếp hạng TOP (y hệt edu)", "art_style": "default", "title_color": "#a78bfa", "text_color": "", "font_family": "", "effect": "hotlist_board", "topic": "AI Hotlist — Top 5", "ai_hint": "AI-REVIEW / HOTLIST / RANKING channel (like a tech leaderboard). EVERY step MUST start with 'cosmic_backdrop' as the FIRST element (nebula/aurora bg). Intro step: cosmic_backdrop + 'hotlist_board' (the TOP 1..5 list with a bold title). Each ranking step: cosmic_backdrop + 'rank_card' (#N HẠNG N badge, big name, short desc, a 🔥 hot-score metric). Use 'glass_duel' for A-vs-B compares, 'glass_list' for grouped points, 'big_word' for punchy hooks, 'cosmic_caption' for the closing line. Countdown/leaderboard energy, opinionated, hype. Violet/blue nebula palette.", "effects": ["cosmic_backdrop", "hotlist_board", "rank_card", "glass_duel", "glass_list", "big_word"]}}},
    {"pack_id": "light-news", "name": "Bản Tin Sáng", "version": 6, "template_ids": ["light_news"], "defs": {"light_news": {"id": "light_news", "name": "Bản Tin Sáng", "emoji": "🗞️", "desc": "Tin tức tông SÁNG: bản tin buổi sáng, editorial sạch sẽ", "vibe": "Nền aurora pastel mesh, thẻ kính trắng, chữ mực tối tự động", "art_style": "aurora", "title_color": "", "text_color": "", "font_family": "", "effect": "timeline_road", "topic": "Bản Tin Sáng", "ai_hint": "BRIGHT morning-NEWS channel (clean, airy, trustworthy editorial). The style is LIGHT and the renderer auto-adapts all colors — do NOT add any backdrop scene and do NOT force hex colors. Frame steps like news segments: timeline_road for developments (journey_path/stairs_steps), versus_split for before-vs-after, metric_grid for figures, web_window for sources/sites, data_river for flows, check_sweep for fact-checks. Vary scenes across steps AND across episodes. Premium newsroom energy, concise headlines.", "effects": ["journey_path", "metric_grid", "versus_split", "web_window", "data_river", "stairs_steps", "check_sweep", "orbit_cycle"], "palette": ["#2563eb", "#0284c7", "#f59e0b"], "exemplars": _AURORA_EXEMPLARS}}},
    {"pack_id": "light-tech", "name": "Công Nghệ Sáng", "version": 6, "template_ids": ["tech_light"], "defs": {"tech_light": {"id": "tech_light", "name": "Công Nghệ Sáng", "emoji": "💠", "desc": "Công nghệ tông SÁNG: specs, review, ra mắt sản phẩm", "vibe": "Nền aurora pastel mesh, thẻ kính trắng, accent đậm rõ", "art_style": "aurora", "title_color": "", "text_color": "", "font_family": "", "effect": "metric_grid", "topic": "Công Nghệ Sáng", "ai_hint": "BRIGHT TECH channel (product launches, specs, reviews — Apple-keynote-clean). The style is LIGHT and the renderer auto-adapts all colors — do NOT add any backdrop scene and do NOT force hex colors. Prefer metric_grid for specs/numbers, versus_split for A-vs-B, check_sweep for feature checklists, web_window/code_typing for product demos, donut_percent for shares. Minimal, premium, crisp.", "effects": ["metric_grid", "phone_hero", "code_typing", "web_window", "data_river", "versus_split", "check_sweep", "neuro_stream"], "palette": ["#7c3aed", "#0284c7", "#16a34a"], "exemplars": _AURORA_EXEMPLARS}}},
    {"pack_id": "neon-sketch", "name": "Neon Doodle", "version": 7, "template_ids": ["neon_sketch"], "sprite_dir": "assets/sprites/neon", "defs": {"neon_sketch": {"id": "neon_sketch", "name": "Neon Doodle", "emoji": "✍️", "desc": "Nhân vật que neon sống động trên nền blueprint — storytelling creator/tech", "vibe": "Đen ánh rêu + lưới blueprint, nhân vật sprite vẽ tay, panel terminal", "art_style": "neonsketch", "title_color": "", "head_anchor": 0.14, "body_anchor": 0.335,
    
    "center_body": True, "subtitle_accent": "#a3e635",
    
    "text_color": "", "font_family": "", "effect": "neon_sprite_panel", "topic": "NEON DOODLE", "ai_hint": "NEON DOODLE storytelling channel on a dark blueprint grid. HERO RULE (MANDATORY): every content step uses the named local scene neon_sprite_panel. Set its sprite param to the matching meaning: think (question/confusion/why), idea (solution/tip/insight), run (speed/urgency/action), fall (mistake/barrier/failure), climb (step-by-step progress), lift (hard work/heavy effort), laptop (working/coding/creating), point (explaining/presenting a list), celebrate (win/result), or flag (milestone/goal). NEVER use the same sprite in consecutive steps. Put the step's real data in the scene's short kicker, title, and rows params. Headlines are ALL-CAPS 2-4 words per line. Flat neon-terminal look — no pastel. Colors: yellow #fde047 highlights, lime #a3e635 borders/positive, red #f87171 warnings, cyan #38bdf8 sparingly. Return template+params only; never JavaScript.", "effects": ["neon_sprite_panel", "big_word", "code_typing", "web_window", "metric_grid", "versus_split", "journey_path", "stairs_steps"],
    "variations": ["ui.sprite('think') + panel of question rows", "ui.sprite('fall') + red warning rows", "ui.sprite('idea') + solution chips grid", "ui.sprite('run') + racing progress bars", "ui.sprite('laptop') + terminal code lines typing", "ui.sprite('point') + bordered list board", "ui.sprite('climb') + staircase milestone boxes", "ui.sprite('lift') + effort gauge bars", "ui.sprite('celebrate') + result KPI numbers", "ui.sprite('flag') + milestone boxes row"], "palette": ["#fde047", "#a3e635", "#f87171"], "exemplars": [{"when": "nhân vật chạy (tốc độ/hành động) + panel terminal 3 hàng thanh sáng SET", "code": "ctx.save();\nfunction EZ(t){return 1-Math.pow(1-t,3);}\nvar P=Math.max(0,Math.min(1,stepProgress*3));\nvar cx=W/2, y=cursorY+8;\n/* hero: sprite nhân vật — chọn tên đúng nghĩa của step */\nui.sprite('run', cx, y+280, 460, {seed:1});\n/* panel terminal: 3 hàng label + thanh sáng + SET */\nvar px=110, pw=W-220, py=y+560;\nui.glass(px,py,pw,320,{});\nvar rows=[['NHANH',0.92,'#a3e635'],['CHẬM',0.55,'#38bdf8'],['CẢM XÚC',0.74,'#f87171']];\nctx.font='700 28px Consolas, monospace'; ctx.textAlign='left';\nfor(var i=0;i<3;i++){\n  var ry=py+66+i*94, p=EZ(Math.max(0,Math.min(1,P*2-i*0.25)));\n  ctx.fillStyle='#dbe5d0'; ctx.fillText(rows[i][0],px+44,ry-14);\n  ctx.fillStyle='rgba(255,255,255,0.10)';\n  ctx.beginPath(); ctx.roundRect(px+44,ry,pw-220,14,7); ctx.fill();\n  ctx.shadowColor=rows[i][2]; ctx.shadowBlur=14; ctx.fillStyle=rows[i][2];\n  ctx.beginPath(); ctx.roundRect(px+44,ry,(pw-220)*rows[i][1]*p,14,7); ctx.fill();\n  ctx.shadowBlur=0;\n  ctx.fillStyle='#93a58a'; ctx.textAlign='right';\n  ctx.fillText('SET',px+pw-40,ry+12); ctx.textAlign='left';\n}\nctx.restore();\nreturn 880;"},
    {"when": "nhân vật ngã (rào cản/thất bại) + lưới chip + hàng cảnh báo đỏ", "code": "ctx.save();\nfunction EZ(t){return 1-Math.pow(1-t,3);}\nvar P=Math.max(0,Math.min(1,stepProgress*3));\nvar cx=W/2, y=cursorY+8;\nui.sprite('fall', cx, y+280, 460, {seed:2});\n/* panel: 2x2 chip viền + hàng cảnh báo đỏ */\nvar px=110, pw=W-220, py=y+560;\nui.glass(px,py,pw,320,{});\nvar items=['CẮT GHÉP','THÊM CHỮ','HIỆU ỨNG','NHÌN XỊN'];\nctx.font='700 28px Consolas, monospace'; ctx.textAlign='center'; ctx.textBaseline='middle';\nfor(var i=0;i<4;i++){\n  var bx=px+40+(i%2)*((pw-100)/2+20), by=py+40+Math.floor(i/2)*72;\n  var bw=(pw-100)/2, ap=EZ(Math.max(0,Math.min(1,P*2-i*0.15)));\n  ctx.globalAlpha=ap;\n  ctx.fillStyle='rgba(163,230,53,0.07)';\n  ctx.beginPath(); ctx.roundRect(bx,by,bw,56,6); ctx.fill();\n  ctx.strokeStyle='rgba(163,230,53,0.55)'; ctx.lineWidth=1.5;\n  ctx.beginPath(); ctx.roundRect(bx,by,bw,56,6); ctx.stroke();\n  ctx.fillStyle='#d9e7c8'; ctx.fillText(items[i],bx+bw/2,by+29);\n  ctx.globalAlpha=1;\n}\nvar wy=py+206;\nctx.fillStyle='rgba(248,113,113,0.12)';\nctx.beginPath(); ctx.roundRect(px+40,wy,pw-80,62,6); ctx.fill();\nctx.shadowColor='#f87171'; ctx.shadowBlur=10;\nctx.strokeStyle='rgba(248,113,113,0.7)'; ctx.lineWidth=1.5;\nctx.beginPath(); ctx.roundRect(px+40,wy,pw-80,62,6); ctx.stroke();\nctx.shadowBlur=0;\nctx.fillStyle='#f87171'; ctx.fillText('RÀO CẢN EDIT',px+pw/2,wy+32);\nctx.restore();\nreturn 880;"},
    {"when": "nhân vật cắm cờ (mốc/thành quả) + 3 hộp mốc + footer mono", "code": "ctx.save();\nfunction EZ(t){return 1-Math.pow(1-t,3);}\nvar P=Math.max(0,Math.min(1,stepProgress*3));\nvar cx=W/2, y=cursorY+8;\nui.sprite('flag', cx, y+280, 470, {seed:3});\n/* panel: 3 hộp mốc + footer mono trái/phải */\nvar px=110, pw=W-220, py=y+570;\nui.glass(px,py,pw,300,{});\nvar boxes=['VIDEO 01','SERIES','KÊNH'], bw=(pw-120)/3;\nctx.font='700 28px Consolas, monospace'; ctx.textAlign='center'; ctx.textBaseline='middle';\nfor(var i=0;i<3;i++){\n  var bx=px+40+i*(bw+20), ap=EZ(Math.max(0,Math.min(1,P*2-i*0.2)));\n  ctx.globalAlpha=ap;\n  ctx.strokeStyle='rgba(163,230,53,0.6)'; ctx.lineWidth=1.5;\n  ctx.beginPath(); ctx.roundRect(bx,py+52,bw,110,6); ctx.stroke();\n  ctx.fillStyle='#d9e7c8'; ctx.fillText(boxes[i],bx+bw/2,py+107);\n  ctx.globalAlpha=1;\n}\nctx.font='700 24px Consolas, monospace';\nctx.fillStyle='#93a58a'; ctx.textAlign='left';\nctx.fillText('START SMALL',px+44,py+238);\nctx.textAlign='right';\nctx.fillStyle='#d9e7c8'; ctx.fillText('XÂY DẦN THÀNH KÊNH',px+pw-44,py+238);\nctx.restore();\nreturn 880;"}]}}},
    {"pack_id": "tech-explainer", "name": "Tech Decode", "version": 5, "min_app": "0.1.30", "template_ids": ["tech_explainer"], "defs": {"tech_explainer": {"id": "tech_explainer", "name": "Tech Decode", "emoji": "🔬", "desc": "Giải thích kỹ thuật chuyên sâu — sơ đồ editorial than chì, khung series + chương", "vibe": "Than chì + lưới chéo, linh kiện viền màu theo chương, phụ đề vàng", "art_style": "techdark", "title_color": "", "text_color": "", "font_family": "", "effect": "td_title_hero", "topic": "TECH DECODE", "scene_first": True, "ai_hint": "TECH DEEP-DIVE explainer channel (charcoal editorial, diagonal grid — think premium mechanism-breakdown video essays). SCENE-FIRST: every step is assembled from the td_* scenes below.\nSTEP STRUCTURE (elements in this order):\n(1) td_chrome — REQUIRED first element of EVERY step. Keep series/ep/total/clock IDENTICAL across the episode (series = channel-style episode title, clock = fake mm:ss). Group steps into 3-5 chapters: chap_no/chap (SHORT UPPERCASE chapter name)/chaps; chapter color rotates cyan → green → yellow → orange → red.\n(2) ONE headline text element — ALL-CAPS, ≤6 words.\n(3) ONE content td_* scene whose MEANING matches the step, with REAL params from the narration (params text in the OUTPUT LANGUAGE). NEVER reuse a content scene within an episode.\nStep 1 uses td_title_hero as content scene. Last step uses td_outro (fill ask/follow/save/quote/tags with real channel CTA).\nOUTRO RULE: the outro's brand/name = a real channel name ONLY if the user's input provides one; otherwise use the VIDEO TITLE. Never show or speak the template name anywhere — narration included.\nSCENE CATALOG (name + params example + purpose):\n", "effects": ["td_cards", "td_window", "td_pipeline", "td_turn_ring", "td_hex_chain", "td_shield", "td_sandbox", "td_context_gauge", "td_state_board", "td_versus_cross", "td_step_chain", "td_chat_rail"], "variations": ["td_cards — inventory/components grid", "td_pipeline — 5-stage process with active step", "td_versus_cross — wrong way crossed out vs right way", "td_turn_ring — cycle/loop + numbered breakdown", "td_window — concept card + code line", "td_hex_chain — multi-round progression", "td_shield — policy with allow/confirm/deny", "td_state_board — evolving state + constraints", "td_sandbox — controlled execution box", "td_context_gauge — capacity % + composition", "td_step_chain — 4-step cause-effect chain", "td_chat_rail — simple vs complex comparison"], "palette": ["#fbbf24", "#22d3ee", "#34d399"]}}},
    {"pack_id": "paper-explainer", "name": "Paper Brief", "version": 4, "min_app": "0.1.36", "template_ids": ["paper_explainer"], "defs": {"paper_explainer": {"id": "paper_explainer", "name": "Paper Brief", "emoji": "📜", "desc": "Bình luận công nghệ nền giấy kem — chip chương, card trắng, timeline màu", "vibe": "Kem ấm + lưới nhạt, chữ đen đậm nhấn cam/xanh, watermark kênh", "art_style": "warmpaper", "title_color": "", "text_color": "", "font_family": "", "effect": "wp_title_stack", "topic": "PAPER BRIEF", "scene_first": True, "scene_prefix": "wp_", "chrome_scene": "wp_chrome", "chrome_params": {"color": "orange"}, "no_headline": True, "body_anchor": 0.09,
    "ai_hint": "WARM-PAPER tech commentary channel (cream poster look — bold black type with orange/blue accent words, white rounded cards, colored chapter chips). SCENE-FIRST: every step is assembled from the wp_* scenes below.\nSTEP STRUCTURE (elements in this order):\n(1) wp_chrome — REQUIRED first element of EVERY step: set brand = the REAL series/channel name for THIS video (derive it from the episode topic — NEVER the template name), IDENTICAL across the episode.\n(2) ONE content wp_* scene whose MEANING matches the step. Each scene carries its own tag (SHORT UPPERCASE chapter word) + title (bold headline ≤7 words) params — put the step headline THERE; do NOT add a separate text element. Fill all params with REAL narration content in the OUTPUT LANGUAGE. NEVER reuse a content scene within an episode.\nStep 1 uses wp_title_stack (typographic hook, 3-4 short punchy lines alternating ink/orange/blue). Last step uses wp_outro (brand + call-to-action buttons).\nOUTRO RULE: the outro's brand/name = a real channel name ONLY if the user's input provides one; otherwise use the VIDEO TITLE. Never show or speak the template name anywhere — narration included.\nChapter tag colors rotate: blue → orange → green → red.\nSCENE CATALOG (name + params example + purpose):\n", "effects": ["wp_title_stack", "wp_timeline", "wp_rules", "wp_duo_cards", "wp_layer_table", "wp_grid", "wp_before_after", "wp_news_card"], "variations": ["wp_news_card — headline news with window card + strikethrough", "wp_timeline — dated events lighting up in sequence", "wp_duo_cards — two opposing philosophies, active/dim", "wp_layer_table — side-by-side comparison table", "wp_rules — numbered hard rules with active row", "wp_grid — provider/component grid with checkmarks", "wp_before_after — old architecture vs new architecture", "wp_title_stack — big typographic conclusion stack"], "palette": ["#e8590c", "#1c7ed6", "#2f9e44"]}}},
    {"pack_id": "math-noir", "name": "Math Noir", "version": 9, "min_app": "0.1.49", "template_ids": ["math_noir"], "defs": {"math_noir": {"id": "math_noir", "name": "Math Noir", "emoji": "📐", "desc": "Toán học kiểu manim — đen tuyền, nét trắng mảnh tự vẽ, mượt và tối giản", "vibe": "Đen tuyệt đối, hình học tự vẽ nét, sin/cos, đồ thị, công thức", "art_style": "mathnoir", "title_color": "", "text_color": "", "font_family": "", "effect": "mn_unit_circle", "topic": "MATH NOIR", "scene_first": True, "scene_prefix": "mn_",
    
    "chrome_scene": "mn_chrome",
    
    "chrome_params": {}, "no_headline": True, "body_anchor": 0.1,
    "center_body": True, "ai_hint": "MINIMALIST MATH channel in the manim/3Blue1Brown style: pure black, thin elegant white strokes that DRAW THEMSELVES, tiny gray labels, at most ONE accent-colored element per scene. SCENE-FIRST: every step is assembled from the mn_* scenes below.\nSTEP STRUCTURE (elements in this order):\n(1) mn_chrome — REQUIRED first element of EVERY step: brand = the REAL series/channel name for THIS video (derive from the topic, NEVER the template name); progress = step_index/total (0..1).\n(2) EXACTLY ONE content mn_* scene — never two. THE SCENE MUST LITERALLY VISUALIZE what the narration says: exponent rules → mn_formula/mn_steps_math/mn_equation_duel; a number's nature → mn_big_symbol/mn_zoom_lens/mn_number_line; counting/multiplication → mn_grid_cells (rows×cols IS the multiplication). TOPIC-LOCKED scenes — mn_unit_circle, mn_sine_trace, mn_graph, mn_number_line, mn_triangle_anatomy, mn_integral_area, mn_venn, mn_pendulum, mn_spiral, mn_light_trail — are ONLY valid when the narration is genuinely about that topic; the system verifies this and REPLACES any mismatched scene with a plain formula card, so picking a pretty-but-unrelated scene just makes the video uglier. When no topical scene fits, mn_formula/mn_steps_math/mn_definition_card/mn_grid_cells/mn_big_symbol always work.\nEvery content scene has a `title` param — put a SHORT caption there (≤6 words, OUTPUT LANGUAGE); do NOT add a separate text element.\nNARRATION TEACHES, never summarizes: each step walks the viewer through ONE idea with a concrete, everyday image or example; short spoken sentences; end the step with its single takeaway line. Prefer 'here is WHY' over 'here is THAT'.\nMath notation: prefer unicode (x², √, ½, π, θ, ±, ⁿ). If you write x^2, a^(m-n), x_1 or sqrt(x), the system auto-converts to proper international notation — NEVER leave ^, _ or sqrt() visible in your intent. voice_text spells numbers as words; canvas params show digits and symbols. Fill every angle/formula/label with the REAL math of that step's narration. NEVER reuse a content scene within an episode (mn_formula and mn_steps_math may appear twice if the math needs it).\nStep 1 = INTRO TITLE CARD: mn_title — word = the topic in 1-3 UPPERCASE words (becomes a huge glowing white title), sub = one short punchy hook line, kicker = LEAVE EMPTY (the system fills \"TẬP N\" automatically for real series episodes — NEVER invent an episode number yourself). Do NOT use mn_big_symbol or any scene outside this channel's mn_* catalog as the intro — only mn_* scene names are valid anywhere in this channel; anything else is auto-replaced. Last step: mn_outro.\nOUTRO RULE: the outro's brand/name = a real channel name ONLY if the user's input provides one; otherwise use the VIDEO TITLE. Never show or speak the template name anywhere — narration included.\nSCENE CATALOG (name + params example + purpose):\n", "effects": ["mn_title", "mn_unit_circle", "mn_sine_trace", "mn_graph", "mn_shape_grid", "mn_formula", "mn_number_line", "mn_triangle_anatomy", "mn_transform", "mn_steps_math", "mn_big_symbol", "mn_integral_area", "mn_venn", "mn_pendulum", "mn_spiral", "mn_light_trail", "mn_grid_cells", "mn_equation_duel", "mn_definition_card", "mn_zoom_lens"], "exemplars": [{"when": "proof structure: a finite list of cases gets crossed out, one accent unknown appears outside, a formula ties it together, one conclusion line (style of 'infinitely many primes')", "code": "var P=Math.min(1,stepProgress*2.2);var Q=Math.min(1,stepProgress);\nvar bx=120,by=cursorY+80,bw=620,bh=190;\nmnk.box(bx,by,bw,bh,{dash:true,label:'danh sách hữu hạn',e:mnk.seq(P,0,6)});\nvar nums=['2','3','5','7'];\nfor(var i=0;i<4;i++){var cx0=bx+40+i*145;\n  mnk.box(cx0,by+72,112,82,{e:mnk.seq(P,1,6)});\n  mnk.label(cx0+56,by+113,nums[i],{size:40,muted:false,e:mnk.seq(P,1,6)});\n  mnk.cross(cx0,by+72,112,82,{e:mnk.seq(P,3,6)});}\nvar qx=bx+bw+70;\nmnk.box(qx,by+72,92,82,{dash:true,accent:true,e:mnk.seq(P,4,6)});\nmnk.label(qx+46,by+113,'?',{size:40,accent:true,muted:false,e:mnk.seq(P,4,6)});\nmnk.label(qx+46,by+192,'ước nguyên tố mới',{size:23,e:mnk.seq(P,4,6)});\nmnk.connect(qx+20,by+160,W/2+180,by+292,{e:mnk.seq(P,4,6)});\nmnk.formula(W/2,by+320,'N = 2 × 3 × 5 × 7 + 1',{size:54,accent:'N',e:mnk.seq(P,2,6)});\nmnk.label(W/2,by+430,'⇒ có vô hạn số nguyên tố',{size:34,muted:false,e:Math.max(0,Math.min(1,Q*3-1.8))});\nmnk.pulse(qx+46,by+113,66);"},
    {"when": "two-sided comparison: split screen, a mini diagram + verdict box on each side (style of 'science accepts data, math demands proof')", "code": "var P=Math.min(1,stepProgress*2.2);var Q=Math.min(1,stepProgress);\nvar y0=cursorY+50,h=600;\nmnk.split({left:'Khoa học thực nghiệm',right:'Toán học',y0:y0,h:h,e:mnk.seq(P,0,5)});\nmnk.glyph('dots_curve',W*0.27,y0+250,300,{e:mnk.seq(P,1,5)});\nmnk.box(W*0.27-160,y0+420,320,62,{e:mnk.seq(P,2,5)});\nmnk.label(W*0.27,y0+451,'chấp nhận rộng rãi',{size:27,muted:false,e:mnk.seq(P,2,5)});\nmnk.glyph('segment',W*0.73,y0+170,250,{e:mnk.seq(P,3,5)});\nmnk.label(W*0.73,y0+232,'tỷ tỷ trường hợp — hữu hạn',{size:23,e:mnk.seq(P,3,5)});\nmnk.arrow(W*0.62,y0+320,W*0.85,y0+320,{e:mnk.seq(P,4,5)});\nmnk.glyph('infinity',W*0.90,y0+320,56,{e:mnk.seq(P,4,5)});\nmnk.label(W*0.73,y0+372,'vô hạn số chẵn',{size:23,e:mnk.seq(P,4,5)});\nmnk.box(W*0.73-140,y0+430,280,62,{dash:true,e:Math.max(0,Math.min(1,Q*3-1.6))});\nmnk.label(W*0.73,y0+461,'giả thuyết',{size:27,muted:false,e:Math.max(0,Math.min(1,Q*3-1.6))});"},
    {"when": "several small cases/axioms as mini glyphs converging on one focus point (style of 'four postulates point at the fifth')", "code": "var P=Math.min(1,stepProgress*2.2);var Q=Math.min(1,stepProgress);\nvar y0=cursorY+130;var kinds=['line_pts','segment','circle_r','right_angle'];\nvar tags=['I','II','III','IV'];\nfor(var i=0;i<4;i++){var gx=150+i*260;\n  mnk.glyph(kinds[i],gx,y0,140,{e:mnk.seq(P,i,6)});\n  mnk.label(gx,y0+118,tags[i],{size:28,e:mnk.seq(P,i,6)});\n  mnk.connect(gx,y0+150,W/2,y0+540,{e:mnk.seq(P,4,6)});}\nmnk.glyph('parallel',W/2,y0+600,360,{e:mnk.seq(P,5,6)});\nmnk.label(W/2,y0+512,'P',{size:30,muted:false,e:mnk.seq(P,5,6)});\nmnk.pulse(W/2,y0+560,50);"},
    {"when": "real-world applications row: 3 mini icons (bars/ecg/network/clock...) each with a bold name + muted sub-label, one accent takeaway line (style of 'same math powers music, medicine, networks')", "code": "var P=Math.min(1,stepProgress*2.2);var Q=Math.min(1,stepProgress);\nvar y0=cursorY+170;var xs=[W*0.18,W*0.5,W*0.82];\nvar kinds=['bars','ecg','network'];\nvar names=['Nén nhạc','Ảnh y tế','Mạng di động'];\nvar subs=['điện thoại','chụp bên trong cơ thể','truyền dữ liệu'];\nfor(var i=0;i<3;i++){\n  mnk.glyph(kinds[i],xs[i],y0,170,{e:mnk.seq(P,i,4)});\n  mnk.label(xs[i],y0+150,names[i],{size:34,muted:false,bold:true,e:mnk.seq(P,i,4)});\n  mnk.label(xs[i],y0+196,subs[i],{size:25,e:mnk.seq(P,i,4)});\n}\nmnk.label(W/2,y0+330,'cùng chạy trên một phép toán',{size:28,accent:true,e:Math.max(0,Math.min(1,Q*3-1.7))});"},
    {"when": "case-by-case check table: rows of equations tested one by one with check/cross/marker glyphs, faint dashed separators, the odd case boxed in accent (style of 'zero works with +,-,x but breaks at division')", "code": "var P=Math.min(1,stepProgress*2.2);var Q=Math.min(1,stepProgress);\nvar y0=cursorY+90,rh=132,lx=180,cx=W/2+40;\nvar rows=[['check','7 + 0 = 7'],['check','7 − 0 = 7'],['check','7 × 0 = 0'],['q','7 ÷ 0 = ?']];\nfor(var i=0;i<4;i++){var ry=y0+i*rh,e=mnk.seq(P,i,5);\n  if(rows[i][0]==='check')mnk.glyph('check',lx,ry,60,{e:e});\n  else mnk.label(lx,ry+6,'?',{size:44,accent:true,muted:false,e:e});\n  mnk.formula(cx,ry+16,rows[i][1],{size:48,e:e});\n  if(i<3){ctx.save();ctx.globalAlpha=e;ctx.strokeStyle='rgba(232,232,234,0.22)';ctx.lineWidth=1.5;ctx.setLineDash([8,8]);ctx.beginPath();ctx.moveTo(130,ry+rh*0.58);ctx.lineTo(W-130,ry+rh*0.58);ctx.stroke();ctx.setLineDash([]);ctx.restore();}\n}\nmnk.box(cx-270,y0+3*rh-38,540,88,{dash:true,accent:true,e:Math.max(0,Math.min(1,Q*3-1.7))});\nmnk.pulse(cx,y0+3*rh+6,70);"}], "variations": ["BESPOKE mnk composition — build THIS step's own diagram from mnk.* (dashed boxes, crossed items, labels, connectors, glyphs) like the exemplars", "mn_big_symbol — one huge glowing symbol (π, 0, ∞)", "mn_unit_circle — angle/sin/cos on the unit circle", "mn_definition_card — elegant term + definition typography", "mn_sine_trace — rotating circle tracing a sine wave", "mn_integral_area — area under a curve sweeping in", "mn_equation_duel — controversial expression, two answers", "mn_graph — function curve with sliding tangent", "mn_spiral — golden spiral + Fibonacci squares", "mn_formula — one big formula writing itself", "mn_pendulum — swinging pendulum with trail", "mn_steps_math — line-by-line derivation", "mn_grid_cells — matrix grid with one hot cell", "mn_number_line — points and intervals on a number line", "mn_zoom_lens — magnifier revealing a detail", "mn_triangle_anatomy — triangle with angles/height/area", "mn_light_trail — glowing projectile trajectory", "mn_venn — two overlapping sets", "mn_transform — one shape morphing into another", "mn_shape_grid — grid of self-drawing geometry glyphs"], "palette": ["#e8e8ea", "#facc15", "#60a5fa"]}}}]
def wrangler(*args, capture=False):
    cmd = ["npx", "wrangler", *args]
    if capture:
        r = subprocess.run(
            cmd,
            cwd=str(WORKER),
            capture_output=True,
            shell=sys.platform == "win32",
        )
        return r.returncode, r.stdout
    r = subprocess.run(cmd, cwd=str(WORKER), shell=sys.platform == "win32")
    return r.returncode, b""

def r2_put(key: str, file: Path):
    code, _ = wrangler("r2", "object", "put", f"{R2_BUCKET}/{key}", f"--file={file}")
    if code != 0:
        raise RuntimeError(f"upload lỗi: {key}")
    print(f"  ↑ {key}")

def r2_get_json(key: str):
    code, out = wrangler("r2", "object", "get", f"{R2_BUCKET}/{key}", "--pipe", capture=True)
    if code != 0 or not out:
        return None
    try:
        return json.loads(out.decode("utf-8"))
    except Exception:
        return None

_SUFFIX = {"9:16": "", "16:9": "_16x9", "1:1": "_1x1"}
def ensure_thumb(tid: str, tdef: dict, force: bool=True):
    from core import preview_demo as PD

    SAMPLES.mkdir(parents=True, exist_ok=True)
    for aspect, suffix in _SUFFIX.items():
        p = SAMPLES / f"{tid}{suffix}.png"
        if p.exists() and p.stat().st_size > 0 and not force:
            continue
        PD.render_preview_png(tid, str(p), aspect, tdef=tdef)
    g = SAMPLES / f"{tid}.gif"
    if not force and g.exists() and g.stat().st_size > 0:
        return
    PD.render_preview_gif(tid, str(g), "9:16", tdef=tdef)

def build_and_upload(pack: dict):
    pid = pack["pack_id"]
    print(f"== Gói {pid} v{pack['version']} ==")
    tmp = Path(tempfile.mkdtemp(prefix=f"pack_{pid}_"))
    templates = []
    has_gif = False
    for tid in pack["template_ids"]:
        d = pack["defs"][tid]
        ensure_thumb(tid, d, force=False)
        t_entry = {k: d[k] for k in _KEEP if k in d}
        for suffix in ("", "_16x9", "_1x1"):
            src = SAMPLES / f"{tid}{suffix}.png"
            if not src.exists():
                if suffix == "":
                    raise RuntimeError(f"Thiếu thumbnail {src}")
                continue
            dst = tmp / f"{tid}{suffix}.png"
            dst.write_bytes(src.read_bytes())
        gif = SAMPLES / f"{tid}.gif"
        if gif.exists() and gif.stat().st_size > 0:
            (tmp / f"{tid}.gif").write_bytes(gif.read_bytes())
            t_entry["has_gif"] = True
            has_gif = True
        templates.append(t_entry)

    sprite_names = []
    sd = pack.get("sprite_dir")
    if sd:
        sd = Path(sd)
        if not sd.is_absolute():
            sd = BASE / sd
        for f in sorted(sd.glob("*.png")):
            sprite_names.append(f.name)
            r2_put(f"{R2_PREFIX}/{pid}/sprites/{f.name}", f)
    
    manifest = {
        "pack_id": pid,
        "name": pack["name"],
        "version": pack["version"],
        "templates": templates,
    }
    if pack.get("min_app"):
        manifest["min_app"] = pack["min_app"]
    if sprite_names:
        manifest["sprites"] = sprite_names
    (tmp / "pack.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for f in sorted(tmp.glob("*.png")) + sorted(tmp.glob("*.gif")):
        r2_put(f"{R2_PREFIX}/{pid}/{f.name}", f)
    r2_put(f"{R2_PREFIX}/{pid}/pack.json", tmp / "pack.json")
    
    entry = {
        "pack_id": pid,
        "name": pack["name"],
        "version": pack["version"],
        "count": len(templates),
        "templates": [t["id"] for t in templates],
    }
    if has_gif:
        entry["has_gif"] = True
    if pack.get("min_app"):
        entry["min_app"] = pack["min_app"]
    return entry

def main():
    try:
        from core.custom_scenes import td_prompt_doc

        for pack in PACKS:
            for d in pack.get("defs", {}).values():
                if not d.get("scene_first"):
                    continue
                d["ai_hint"] = d["ai_hint"] + td_prompt_doc(d.get("scene_prefix", "td_"))
    except Exception as e:
        print(f"⚠ không nối được td_prompt_doc: {e}")

    index = r2_get_json(f"{R2_PREFIX}/index.json") or {"packs": []}
    by_id = {p["pack_id"]: p for p in index.get("packs", [])}
    for pack in PACKS:
        entry = build_and_upload(pack)
        by_id[entry["pack_id"]] = entry
    index["packs"] = list(by_id.values())

    tmp = Path(tempfile.mkdtemp()) / "index.json"
    tmp.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    r2_put(f"{R2_PREFIX}/index.json", tmp)
    print("\n✅ Kho mẫu cập nhật:")
    print(json.dumps(index, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    sys.path.insert(0, str(BASE))
    main()
