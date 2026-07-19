"""core/scenes_td_1.py — Bộ scene techdark #1: td_chrome, td_cards, td_window.

Phong cách video giải thích công nghệ premium: nền than chì (renderer lo),
card viền mảnh accent, tag chip mono, chữ trắng đậm. Xem td_spec.md.
"""
import json, math
from core.custom_scenes import scene; ACCENT = {"cyan": "#22d3ee", "green": "#34d399", "orange": "#fb923c", "yellow": "#fbbf24", "red": "#f87171", "purple": "#a78bfa", "blue": "#38bdf8"}
def _hex_rgba(hex_color, alpha):
    h = hex_color.lstrip("#"); b = int(h[4:6], 16); g = int(h[2:4], 16); r = int(h[0:2], 16)
    return "rgba(%d,%d,%d,%s)" % (r, g, b, alpha)

def _ac(name, fallback="cyan"):
    return ACCENT.get(name, ACCENT[fallback])

_JS_AC = "var AC=" + json.dumps(ACCENT, ensure_ascii=False) + ";"
for k, v in ACCENT.items():
    pass
v = v; k = k

_JS_AB = "var AB=" + json.dumps({k: _hex_rgba(v, 0.55)}, ensure_ascii=False) + ";"
def td_chrome(series="Tên series", ep=1, total=10, clock="00:00", chap_no=1, chap="MỞ ĐẦU", chaps=5, color="orange"):
    ep = int(ep); total = int(total); chap_no = int(chap_no); chaps = max(1, int(chaps)); ac = _ac(color, "orange"); top_txt = "【%s】 · %02d/%02d · %s" % (str(series), ep, total, str(clock)); num_txt = "0%d" % chap_no if chap_no < 10 else str(chap_no); frac = max(0.0, min(1.0, (chap_no - 0.5) / chaps))
    
    el = scene(["var TT=" + json.dumps(top_txt, ensure_ascii=False) + ";",
    
    "var CH=" + json.dumps(str(chap), ensure_ascii=False) + ";", "var NUM=" + json.dumps(num_txt, ensure_ascii=False) + ";", "var ACC=" + json.dumps(ac) + ";",
    
    "var FRAC=" + json.dumps(round(frac, 5)) + ", CHAPS=" + str(chaps) + ";", "ctx.save();", "/* ── TOP: dòng meta series căn giữa ── */", "ctx.globalAlpha=CL(P*2.2);", "ctx.font='26px Consolas, monospace';ctx.fillStyle='#8b949e';", "ctx.textAlign='center';ctx.textBaseline='top';", "ctx.fillText(TT,W/2,cursorY+10);", "ctx.globalAlpha=1;", "/* ── BOTTOM: chương hiện tại (kẹp theo H để hợp mọi khung) ── */", "var by=Math.min(cursorY+1740,H-120);", "var be=CL(P*2.2-0.15);", "ctx.globalAlpha=be;", "ctx.fillStyle=ACC;",
    
    "ctx.fillRect(MX,by-26,4,32);", "ctx.textAlign='left';ctx.textBaseline='middle';", "ctx.font='bold 26px Consolas, monospace';ctx.fillStyle=ACC;", "ctx.fillText(NUM,MX+18,by-9);", "var nw=ctx.measureText(NUM).width;", "ctx.font='26px Segoe UI, sans-serif';ctx.fillStyle='#f5f7f9';", "ctx.fillText(CH,MX+18+nw+14,by-9);", "ctx.globalAlpha=1;", "/* ── thanh progress ngang full ── */", "var py=by+34, bw=W-MX*2;", "ctx.fillStyle='rgba(255,255,255,0.14)';", "ctx.fillRect(MX,py,bw,4);", "/* đoạn đã qua: gradient nhiều màu theo vị trí */", "var pe=EZ(CL(P*1.6-0.2));", "var fw=bw*FRAC*pe;", "if(fw>0){", "  var g=ctx.createLinearGradient(MX,0,W-MX,0);", "  g.addColorStop(0,'#22d3ee');g.addColorStop(0.34,'#34d399');", "  g.addColorStop(0.67,'#fbbf24');g.addColorStop(1,'#fb923c');", "  ctx.fillStyle=g;ctx.fillRect(MX,py,fw,4);", "}", "/* vạch chia chương */", "for(var i=1;i<CHAPS;i++){", "  var tx=MX+bw*i/CHAPS;", "  ctx.fillStyle='rgba(255,255,255,0.32)';", "  ctx.fillRect(tx-1,py-4,2,12);", "}", "/* con trỏ hiện tại: chấm trắng glow */", "var dx=MX+bw*FRAC*pe;", "var pu=0.75+0.25*Math.sin(time*3);", "ctx.shadowColor=ACC;ctx.shadowBlur=14*pu;", "ctx.fillStyle='#ffffff';", "ctx.beginPath();ctx.arc(dx,py+2,6,0,Math.PI*2);ctx.fill();", "ctx.shadowBlur=0;", "ctx.restore();"], 1800)
    el["x_9_16"] = 0.0; el["y_9_16"] = 0.03125; el["x_16_9"] = 0.0; el["y_16_9"] = 0.03125; return el

def td_cards(title="", items=None, cols=2, color="cyan"):
    items = (items or [{"tag": "INPUT 1", "label": "User prompt", "color": "cyan", "icon": "💬"},
        {"tag": "INPUT 2", "label": "System prompt", "color": "yellow", "icon": "⚙️"}])[:6]; cols = max(1, min(3, int(cols))); norm = []
    for it in items:
        norm.append({"tag": str(it.get("tag", "")), "label": str(it.get("label", "")), "icon": str(it.get("icon", "")), "c": _ac(str(it.get("color", color))), "b": _hex_rgba(_ac(str(it.get("color", color))), 0.55)})
    rows = int(math.ceil(len(norm) / float(cols)))
    
    title_h = 62 if title else 0; height = title_h + rows * 150 + 20
    return scene(["var ITEMS=" + json.dumps(norm, ensure_ascii=False) + ";", "var TITLE=" + json.dumps(str(title), ensure_ascii=False) + ";",
    
    "var COLS=" + str(cols) + ";", "var y0=cursorY+10;", "ctx.save();", "if(TITLE){", "  ctx.globalAlpha=CL(P*2.5);", "  ctx.font='bold 32px Segoe UI, sans-serif';ctx.fillStyle='#f5f7f9';", "  ctx.textAlign='center';ctx.textBaseline='middle';", "  ctx.fillText(TITLE,W/2,y0+18);", "  ctx.globalAlpha=1;", "  y0+=" + str(title_h) + ";", "}", "var cw=(W-120-24*(COLS-1))/COLS;", "ITEMS.forEach(function(it,i){", "  var e=EZ(CL(P*2-i*0.12));if(e<=0)return;", "  var col=i%COLS, row=Math.floor(i/COLS);", "  var x=60+col*(cw+24);", "  var y=y0+row*150+18*(1-e);", "  ctx.globalAlpha=e;", "  ctx.fillStyle='rgba(16,21,26,0.85)';RR(x,y,cw,128,14);ctx.fill();", "  ctx.strokeStyle=it.b;ctx.lineWidth=1.5;RR(x,y,cw,128,14);ctx.stroke();", "  /* tag chip mono accent */", "  ctx.textAlign='left';ctx.textBaseline='middle';", "  ctx.font='bold 22px Consolas, monospace';ctx.fillStyle=it.c;", "  ctx.fillText(it.tag,x+24,y+34);", "  /* icon emoji bên phải */", "  var iw=0;", "  if(it.icon){", "    ctx.font='38px sans-serif';ctx.textAlign='center';", "    ctx.fillText(it.icon,x+cw-46,y+64);", "    iw=64;", "  }", "  /* label trắng bold, wrap 2 dòng nếu dài */", "  ctx.textAlign='left';", "  var maxw=cw-48-iw;", "  var f='bold 30px Segoe UI, sans-serif';", "  var ls=wrapText(it.label,maxw,f);", "  if(ls.length>1){f='bold 26px Segoe UI, sans-serif';ls=wrapText(it.label,maxw,f);}", "  ctx.font=f;ctx.fillStyle='#f5f7f9';", "  if(ls.length<=1){ctx.fillText(ls[0]||'',x+24,y+84);}", "  else{ctx.fillText(ls[0],x+24,y+74);ctx.fillText(ls[1],x+24,y+106);}", "  ctx.globalAlpha=1;", "});", "ctx.restore();"], height)

def td_window(title="Tool request", heading="Tools are not magic", body="Sau khi kết nối tool, Claude có thể yêu cầu hành động.", code="", color="green"):
    ac = _ac(color, "green")
    # ``sanitize_params`` deliberately converts quotation marks for the
    # legacy factories which interpolate text into JS.  This factory writes
    # the code sample through json.dumps, so restore them for its *displayed*
    # code snippet.  It keeps the original application's example readable
    # (request_tool("search_code")) without reopening a JS injection path.
    code = str(code).replace("”", '"').replace("“", '"').replace("’", "'").replace("‘", "'")
    return scene(["var TI=" + json.dumps(str(title), ensure_ascii=False) + ";", "var HD=" + json.dumps(str(heading), ensure_ascii=False) + ";", "var BD=" + json.dumps(str(body), ensure_ascii=False) + ";", "var CD=" + json.dumps(str(code), ensure_ascii=False) + ";", "var ACC=" + json.dumps(ac) + ";", "var ACB=" + json.dumps(_hex_rgba(ac, 0.55)) + ";",
    
    "var x=80, w=W-160, h=560;", "var e=EZ(CL(P*1.8));", "var y=cursorY+14+16*(1-e);", "ctx.save();ctx.globalAlpha=e;", "/* thân cửa sổ */", "ctx.fillStyle='rgba(16,21,26,0.85)';RR(x,y,w,h,14);ctx.fill();", "ctx.strokeStyle=ACB;ctx.lineWidth=1.5;RR(x,y,w,h,14);ctx.stroke();", "/* thanh title 64px: 3 chấm + title mono */", "ctx.strokeStyle='rgba(255,255,255,0.09)';ctx.lineWidth=1;", "ctx.beginPath();ctx.moveTo(x,y+64);ctx.lineTo(x+w,y+64);ctx.stroke();", "ctx.fillStyle='#f87171';ctx.beginPath();ctx.arc(x+34,y+32,8,0,Math.PI*2);ctx.fill();", "ctx.fillStyle='#fbbf24';ctx.beginPath();ctx.arc(x+62,y+32,8,0,Math.PI*2);ctx.fill();", "ctx.fillStyle='#34d399';ctx.beginPath();ctx.arc(x+90,y+32,8,0,Math.PI*2);ctx.fill();", "ctx.font='24px Consolas, monospace';ctx.fillStyle='#9aa3ad';", "ctx.textAlign='left';ctx.textBaseline='middle';", "ctx.fillText(TI,x+118,y+33);", "/* heading trắng bold 40px (tự co nếu dài) */", "var hf=40;ctx.font='bold '+hf+'px Segoe UI, sans-serif';",
    
    "while(ctx.measureText(HD).width>w-80&&hf>28){hf-=2;ctx.font='bold '+hf+'px Segoe UI, sans-serif';}", "ctx.fillStyle='#f5f7f9';",
    
    "ctx.fillText(HD,x+40,y+128);", "/* gạch accent nhỏ dưới heading làm điểm nhấn */", "ctx.fillStyle=ACC;ctx.shadowColor=ACC;ctx.shadowBlur=10;", "ctx.fillRect(x+40,y+156,64*EZ(CL(P*2-0.3)),4);", "ctx.shadowBlur=0;", "/* body muted wrap ~3-4 dòng */", "var bf='28px Segoe UI, sans-serif';", "var bl=wrapText(BD,w-80,bf);", "ctx.font=bf;ctx.fillStyle='#9aa3ad';", "bl.slice(0,4).forEach(function(l,i){", "  var le=CL(P*2.4-0.5-i*0.15);", "  ctx.globalAlpha=e*le;", "  ctx.fillText(l,x+40,y+190+i*42);", "});", "ctx.globalAlpha=e;", "/* khối code gõ dần */", "if(CD){", "  var bx=x+40, bw2=w-80, bh=72, by2=y+h-112;", "  ctx.fillStyle='#0d1117';RR(bx,by2,bw2,bh,10);ctx.fill();", "  ctx.strokeStyle='rgba(255,255,255,0.10)';ctx.lineWidth=1;RR(bx,by2,bw2,bh,10);ctx.stroke();", "  var tp=CL(P*1.8-0.45);", "  var nch=Math.floor(CD.length*tp);", "  var ts=CD.substring(0,nch);", "  ctx.font='28px Consolas, monospace';ctx.fillStyle='#e6edf3';", "  ctx.fillText(ts,bx+24,by2+37);", "  if(Math.floor(time*2.5)%2===0){", "    var tw=ctx.measureText(ts).width;", "    ctx.fillStyle=ACC;", "    ctx.fillText('\\u258c',bx+24+tw+2,by2+37);", "  }", "}", "ctx.restore();"], 600)

SCENES = {"td_chrome": {"fn": td_chrome, "doc": 'td_chrome {"series":"Tên series","ep":3,"total":19,"clock":"03:57","chap_no":2,"chap":"CƠ CHẾ","chaps":5,"color":"orange"} — khung series: dòng meta trên cùng + tên chương và thanh progress đa màu dưới cùng (element ĐẦU TIÊN của mọi step)', "demo": {"series": "MỔ XẺ CÔNG NGHỆ", "ep": 3, "total": 19, "clock": "03:57", "chap_no": 2, "chap": "CƠ CHẾ", "chaps": 5, "color": "orange"}}, "td_cards": {"fn": td_cards, "doc": 'td_cards {"title":"","items":[{"tag":"INPUT 1","label":"User prompt","color":"cyan","icon":"💬"}],"cols":2} — lưới 1-6 card viền màu: tag chip mono + label trắng + icon emoji, reveal trượt stagger', "demo": {"title": "Mỗi vòng Claude thấy gì", "cols": 2, "items": [{"tag": "INPUT 1", "label": "User prompt", "color": "cyan", "icon": "💬"},
    {"tag": "INPUT 2", "label": "System prompt", "color": "yellow", "icon": "⚙️"},
    {"tag": "INPUT 3", "label": "Định nghĩa tool", "color": "purple", "icon": "🧩"},
    {"tag": "INPUT 4", "label": "Lịch sử hội thoại đầy đủ của phiên", "color": "green", "icon": "🗂️"}]}}, "td_window": {"fn": td_window, "doc": 'td_window {"title":"Tool request","heading":"Tools are not magic","body":"...","code":"request_tool(\\"search_code\\")","color":"green"} — cửa sổ app 3 chấm: heading lớn + body muted + khối code gõ dần có con trỏ nhấp nháy', "demo": {"title": "Tool request", "heading": "Tools are not magic", "body": "Sau khi kết nối tool, Claude không tự chạy gì cả — nó chỉ phát ra yêu cầu hành động, hệ thống của bạn mới là bên thực thi và trả kết quả về.", "code": 'request_tool("search_code")', "color": "green"}}}; v = None; k = None
