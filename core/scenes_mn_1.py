"""core/scenes_mn_1.py — Bộ scene mathnoir #1: mn_chrome, mn_unit_circle, mn_outro.

Phong cách manim/3Blue1Brown: nền đen tuyền (renderer lo), nét trắng mảnh
lw3 tự vẽ dần, chữ nhỏ gọn, tối giản tuyệt đối — không card, không neon.
Accent (vàng/xanh) chỉ dùng cho ĐÚNG 1 phần tử mỗi cảnh. Xem mn_spec.md.
"""
import json, random
from core.custom_scenes import scene; INK = "#e8e8ea"; MUTED = "#9a9aa0"; FAINT = "#6f6f76"; AXIS = "rgba(232,232,234,0.45)"; DASH = "rgba(232,232,234,0.35)"; ACCENT = {"yellow": "#facc15", "blue": "#60a5fa"}
def _acc(name):
    return ACCENT.get(str(name), ACCENT["yellow"])

def mn_chrome(brand="Tên Kênh", progress=0.3):
    try:
        progress = max(0.0, min(1.0, float(progress)))
        while 1:
            el = scene(["var BR=" + json.dumps(str(brand), ensure_ascii=False) + ";", "var PRG=" + json.dumps(round(progress, 5)) + ";", "ctx.save();", "var e=CL(P*2.2);", "ctx.globalAlpha=e;", "/* tren-phai: brand rat mo */", "ctx.font='24px Segoe UI, sans-serif';ctx.fillStyle='" + FAINT + "';", "ctx.textAlign='right';ctx.textBaseline='middle';", "ctx.fillText(BR,W-40,cursorY+34);", "/* day: hairline progress (kẹp theo H cho mọi khung) */", "var py=Math.min(cursorY+1744,H-56), bw=W-80;", "ctx.fillStyle='rgba(255,255,255,0.10)';", "ctx.fillRect(40,py,bw,2);", "var fw=bw*PRG*EZ(CL(P*1.6-0.1));", "ctx.fillStyle='" + INK + "';", "if(fw>0)ctx.fillRect(40,py,fw,2);", "ctx.beginPath();ctx.arc(40+fw,py+1,5,0,Math.PI*2);ctx.fill();", "ctx.globalAlpha=1;ctx.restore();"], 1800)
            el["x_9_16"] = 0.0
            el["y_9_16"] = 0.03125
            el["x_16_9"] = 0.0
            el["y_16_9"] = 0.03125
            return el
    except:
        pass

def mn_unit_circle(title="", deg=52, show_sin_cos=True, accent="yellow", seed=0):
    try:
        deg = max(1.0, min(360.0, float(deg)))
        while 1:
            ac = _acc(accent)
            _r = random.Random(int(seed) if seed else 12_345)
            jR = round(330 * _r.uniform(0.8, 1.06), 1)
            jAX = round(jR + _r.uniform(44, min(70.0, 408 - jR)), 1)
            jQR = round(_r.uniform(32, 52), 1)
            jCY = round(_r.uniform(max(jAX + 95, 435.0), min(990 - jAX, 640.0)), 1)
            jGap = _r.uniform(72, 110)
            jDR = round(7 * jR / 330 * _r.uniform(0.9, 1.2), 1)
            jCX = round(_r.uniform(jAX + 30, 851 - jAX), 1)
            jNX = round(min(935.0, jCX + jAX + 12 + jGap), 1)
            jSQ = round(14 * jR / 330, 1)
            return scene(["var TI=" + json.dumps(str(title), ensure_ascii=False) + ";", "var DEG=" + json.dumps(round(deg, 3)) + ";", "var SC=" + ("true" if show_sin_cos else "false") + ";", "var ACC=" + json.dumps(ac) + ";", "ctx.save();", "ctx.lineCap='round';ctx.lineJoin='round';", "ctx.textAlign='center';ctx.textBaseline='middle';", "if(TI){", "  ctx.globalAlpha=CL(P*2.5);", "  ctx.font='600 34px Segoe UI, sans-serif';ctx.fillStyle='#8b8b92';", "  ctx.fillText(TI,W/2,cursorY+40);",
    
    "  ctx.globalAlpha=1;", "}", "var cx=" + str(jCX) + ", cy=cursorY+" + str(jCY) + ", R=" + str(jR) + ", AX=" + str(jAX) + ";", "/* ── truc x/y mui ten + nhan 1/-1 ── */", "var ea=EZ(CL(P*2.2));", "ctx.globalAlpha=ea;", "ctx.strokeStyle='" + AXIS + "';ctx.lineWidth=2;",
    
    "ctx.beginPath();ctx.moveTo(cx-AX,cy);ctx.lineTo(cx+AX,cy);ctx.stroke();", "ctx.beginPath();ctx.moveTo(cx,cy-AX);ctx.lineTo(cx,cy+AX);ctx.stroke();", "ctx.fillStyle='" + AXIS + "';", "ctx.beginPath();ctx.moveTo(cx+AX+12,cy);ctx.lineTo(cx+AX-2,cy-6);ctx.lineTo(cx+AX-2,cy+6);ctx.closePath();ctx.fill();", "ctx.beginPath();ctx.moveTo(cx,cy-AX-12);ctx.lineTo(cx-6,cy-AX+2);ctx.lineTo(cx+6,cy-AX+2);ctx.closePath();ctx.fill();", "/* tick nho tai giao diem vong tron voi truc */", "ctx.strokeStyle='" + AXIS + "';", "ctx.beginPath();ctx.moveTo(cx+R,cy-7);ctx.lineTo(cx+R,cy+7);ctx.stroke();", "ctx.beginPath();ctx.moveTo(cx-R,cy-7);ctx.lineTo(cx-R,cy+7);ctx.stroke();", "ctx.beginPath();ctx.moveTo(cx-7,cy-R);ctx.lineTo(cx+7,cy-R);ctx.stroke();", "ctx.beginPath();ctx.moveTo(cx-7,cy+R);ctx.lineTo(cx+7,cy+R);ctx.stroke();", "ctx.font='400 30px Segoe UI, sans-serif';ctx.fillStyle='" + MUTED + "';", "ctx.fillText('1',cx+R+16,cy+36);", "ctx.fillText('\\u22121',cx-R-18,cy+36);", "ctx.fillText('1',cx-32,cy-R-4);", "ctx.fillText('\\u22121',cx-40,cy+R+6);", "ctx.globalAlpha=1;", "/* ── vong tron VE DAN (nguoc chieu kim dong ho tu goc 0) ── */", "var e=EZ(CL(P*1.4));", "if(e>0.003){", "  ctx.strokeStyle='" + INK + "';ctx.lineWidth=3;",
    
    "  ctx.beginPath();ctx.arc(cx,cy,R,0,-Math.PI*2*e,true);ctx.stroke();", "}", "/* cham trang nho troi cham quanh vong tron (idle theo time) */", "if(e>0.95){", "  var ta=time*0.5;", "  ctx.globalAlpha=0.4;ctx.fillStyle='#fff';", "  ctx.beginPath();ctx.arc(cx+R*Math.cos(ta),cy-R*Math.sin(ta),3.5,0,Math.PI*2);ctx.fill();", "  ctx.globalAlpha=1;", "}", "/* ── ban kinh quay 0 -> deg ── */", "var e2=EZ(CL(P*1.2-0.2));", "var ang=DEG*e2, a=ang*Math.PI/180;", "var px=cx+R*Math.cos(a), py=cy-R*Math.sin(a);", "if(e2>0.003){", "  /* fill tam giac vuong */", "  ctx.fillStyle='rgba(255,255,255,0.06)';", "  ctx.beginPath();ctx.moveTo(cx,cy);ctx.lineTo(px,cy);ctx.lineTo(px,py);ctx.closePath();ctx.fill();", "  /* vuong goc nho tai chan duong cao */", "  var sx=(px>=cx?-" + str(jSQ) + ":" + str(jSQ) + "), sy=(py<=cy?-" + str(jSQ) + ":" + str(jSQ) + ");", "  if(Math.abs(px-cx)>" + str(round(jSQ + 12, 1)) + "&&Math.abs(py-cy)>" + str(round(jSQ + 12, 1)) + "){", "    ctx.strokeStyle='" + AXIS + "';ctx.lineWidth=2;", "    ctx.beginPath();ctx.moveTo(px+sx,cy);ctx.lineTo(px+sx,cy+sy);ctx.lineTo(px,cy+sy);ctx.stroke();", "  }", "  /* net dut giong ngang sang truc y — REVEAL MUON (P2 giua step), dash troi theo time */", "  var lg2=CL(P2*3-1.5);", "  if(lg2>0.003){", "    ctx.globalAlpha=lg2;", "    ctx.strokeStyle='" + DASH + "';ctx.lineWidth=2;", "    ctx.setLineDash([8,8]);ctx.lineDashOffset=-time*8;", "    ctx.beginPath();ctx.moveTo(px,py);ctx.lineTo(cx,py);ctx.stroke();", "    ctx.setLineDash([]);ctx.lineDashOffset=0;", "    ctx.globalAlpha=1;", "  }",
    
    "  /* canh dung (sin) — PHAN TU ACCENT DUY NHAT, glow tho nhe theo time */", "  ctx.strokeStyle=ACC;ctx.lineWidth=3;", "  ctx.shadowColor=ACC;ctx.shadowBlur=6+4*Math.sin(time*1.6);", "  ctx.beginPath();ctx.moveTo(px,cy);ctx.lineTo(px,py);ctx.stroke();", "  ctx.shadowBlur=0;", "  /* canh huyen = ban kinh quay */", "  ctx.strokeStyle='" + INK + "';ctx.lineWidth=3;", "  ctx.beginPath();ctx.moveTo(cx,cy);ctx.lineTo(px,py);ctx.stroke();", "  /* cung goc nho */", "  ctx.strokeStyle='" + AXIS + "';ctx.lineWidth=2;", "  ctx.beginPath();ctx.arc(cx,cy," + str(jQR) + ",0,-a,true);ctx.stroke();", "  /* nhan */", "  ctx.font='400 30px Segoe UI, sans-serif';ctx.fillStyle='" + MUTED + "';", "  var ha=a/2;", "  ctx.fillText('x',cx+" + str(round(jQR + 26, 1)) + "*Math.cos(ha),cy-" + str(round(jQR + 26, 1)) + "*Math.sin(ha));",
    
    "  if(SC){", "    var la=CL(P*1.6-0.55);", "    ctx.globalAlpha=la;", "    /* sin canh truc y, cos duoi truc x */", "    ctx.fillText('sin',cx-52,(cy+py)/2);", "    ctx.fillText('cos',(cx+px)/2,cy+38);", "    /* 1 giua canh huyen (lech vuong goc ra ngoai) */", "    ctx.fillText('1',(cx+px)/2-26*Math.sin(a),(cy+py)/2-26*Math.cos(a));", "    /* y canh dung */", "    ctx.fillText('y',px+(px>=cx?30:-30),(cy+py)/2);", "    /* toa do diem — REVEAL MUON (P2 ~65% step), nhan muted nho */", "    var la2=CL(P2*4-2.6);", "    if(la2>0.003){", "      ctx.globalAlpha=la2*0.9;", "      ctx.font='400 26px Segoe UI, sans-serif';ctx.fillStyle='" + MUTED + "';", "      var ax3=Math.max(96,Math.min(W-96,cx+(R+58)*Math.cos(a)));", "      var ay3=Math.max(cursorY+26,Math.min(cy+AX-10,cy-(R+58)*Math.sin(a)));", "      ctx.fillText('(cos x, sin x)',ax3,ay3);", "    }", "    ctx.globalAlpha=1;",
    
    "  }", "  /* cham diem tren vong tron: halo + glow khi dang quay */", "  ctx.fillStyle='rgba(255,255,255,0.25)';", "  ctx.beginPath();ctx.arc(px,py," + str(round(jDR * 2, 1)) + ",0,Math.PI*2);ctx.fill();", "  if(e2<0.999){ctx.shadowColor='rgba(255,255,255,0.35)';ctx.shadowBlur=8;}", "  ctx.fillStyle='#fff';", "  ctx.beginPath();ctx.arc(px,py," + str(jDR) + ",0,Math.PI*2);ctx.fill();",
    
    "  ctx.shadowBlur=0;", "  /* ── SO DO LON ben phai, dem tang theo e2 ── */", "  ctx.globalAlpha=CL(P*1.4-0.25);", "  ctx.font='bold 110px Segoe UI, sans-serif';ctx.fillStyle='" + INK + "';", "  ctx.fillText(Math.round(ang)+'\\u00b0'," + str(jNX) + ",cy);", "  ctx.globalAlpha=1;", "}", "ctx.restore();"], 1000)
    except:
        pass

def mn_outro(brand="Tên Kênh", line="Toán không khó — chỉ cần nhìn thấy nó.", cta="ĐĂNG KÝ"):
    return scene(["var BR=" + json.dumps(str(brand), ensure_ascii=False) + ";", "var LN=" + json.dumps(str(line), ensure_ascii=False) + ";", "var CTA=" + json.dumps(str(cta), ensure_ascii=False) + ";", "ctx.save();", "ctx.textAlign='center';ctx.textBaseline='middle';", "ctx.lineCap='round';ctx.lineJoin='round';", "/* hairline ngang 300px, no ra tu giua */", "var e1=EZ(CL(P*2));", "ctx.fillStyle='rgba(255,255,255,0.3)';", "ctx.fillRect(W/2-150*e1,cursorY+40,300*e1,2);", "/* brand — tự co font khi tiêu đề dài (kẻo tràn mép) */", "var e2=EZ(CL(P*2-0.15));", "ctx.globalAlpha=e2;", "var bf=64;ctx.font='bold '+bf+'px Segoe UI, sans-serif';", "while(ctx.measureText(BR).width>W-120&&bf>30){bf-=4;ctx.font='bold '+bf+'px Segoe UI, sans-serif';}", "ctx.fillStyle='" + INK + "';", "ctx.fillText(BR,W/2,cursorY+120+14*(1-e2));", "/* line muted */", "var e3=EZ(CL(P*2-0.3));", "ctx.globalAlpha=e3;", "ctx.font='400 32px Segoe UI, sans-serif';ctx.fillStyle='" + MUTED + "';", "ctx.fillText(LN,W/2,cursorY+190+14*(1-e3));",
    
    "ctx.globalAlpha=1;", "/* nut outline: RR 320x86 bo 43, vien VE NET DAN */", "var bw=320, bh=86, bx=W/2-bw/2, by=cursorY+300;", "var be=EZ(CL(P*1.4-0.35));",
    
    "if(be>0.003){", "  var per=2*(bw-2*43)+2*Math.PI*43+2;", "  ctx.strokeStyle='#ffffff';ctx.lineWidth=2;", "  ctx.setLineDash([per]);ctx.lineDashOffset=per*(1-be);",
    
    "  RR(bx,by,bw,bh,43);ctx.stroke();", "  ctx.setLineDash([]);", "  /* sau khi vien xong: nhip dao outline <-> filled moi 2.4s */", "  var fa=0;", "  if(be>=0.999){", "    var k=Math.floor(time/2.4)%2, u=(time%2.4)/2.4;", "    var w=CL(u*5);", "    fa=(k===1)?w:(1-w);", "  }", "  if(fa>0.003){", "    ctx.globalAlpha=fa;", "    ctx.fillStyle='#ffffff';RR(bx,by,bw,bh,43);ctx.fill();", "    ctx.globalAlpha=1;", "  }", "  ctx.font='bold 32px Segoe UI, sans-serif';", "  ctx.globalAlpha=be*(1-fa);", "  ctx.fillStyle='#ffffff';ctx.fillText(CTA,W/2,by+bh/2+1);", "  ctx.globalAlpha=fa;", "  if(fa>0.003){ctx.fillStyle='#060607';ctx.fillText(CTA,W/2,by+bh/2+1);}", "  ctx.globalAlpha=1;", "}", "ctx.restore();"], 560)

def mn_title(kicker="", word="", sub="", title=""):
    wd = str(word or title or "").strip() or "TOÁN HỌC"; K = json.dumps(str(kicker or ""), ensure_ascii=False); Wd = json.dumps(wd.upper(), ensure_ascii=False); Sb = json.dumps(str(sub or ""), ensure_ascii=False)
    return scene(["var KK=" + K + ", WD=" + Wd + ", SB=" + Sb + ";", "var cx=W/2;",
    
    "ctx.save();", "ctx.textAlign='center';ctx.textBaseline='alphabetic';", "/* kicker mo nho */",
    
    "var ek=CL(P*2.2);", "ctx.globalAlpha=ek;", "ctx.font='600 36px Consolas, monospace';", "ctx.fillStyle='" + MUTED + "';", "if(KK)ctx.fillText(KK,cx,cursorY+64+12*(1-ek));", "/* chu khong lo glow TRANG viet dan bang clip ngang */", "var ew=EZ(CL(P*1.7-0.12));", "if(ew>0.002){", "  var fs=170;", "  ctx.font='800 '+fs+'px Segoe UI, sans-serif';", "  while(ctx.measureText(WD).width>W-140&&fs>62){fs-=6;ctx.font='800 '+fs+'px Segoe UI, sans-serif';}", "  var wy=cursorY+150+fs*0.82, ww=ctx.measureText(WD).width;", "  ctx.save();", "  ctx.beginPath();ctx.rect(cx-ww/2-60,wy-fs*1.15,(ww+120)*ew,fs*1.55);ctx.clip();", "  var sc=0.965+0.035*ew;", "  ctx.translate(cx,wy-fs*0.35);ctx.scale(sc,sc);ctx.translate(-cx,-(wy-fs*0.35));",
    
    "  ctx.globalAlpha=Math.min(1,ew*1.6);", "  ctx.shadowColor='rgba(244,244,246,0.5)';ctx.shadowBlur=40;", "  ctx.fillStyle='#f4f4f6';",
    
    "  ctx.fillText(WD,cx,wy);", "  ctx.shadowBlur=22;ctx.fillText(WD,cx,wy);", "  ctx.shadowBlur=0;", "  ctx.restore();", "  /* gach chan trang manh no ra tu giua */", "  var eu=EZ(CL(P*2-0.65));", "  if(eu>0.002){", "    ctx.globalAlpha=1;", "    ctx.strokeStyle='rgba(232,232,234,0.85)';ctx.lineWidth=4;ctx.lineCap='round';", "    var uw=Math.min(ww*0.92,W-220);", "    ctx.beginPath();ctx.moveTo(cx-(uw/2)*eu,wy+52);ctx.lineTo(cx+(uw/2)*eu,wy+52);ctx.stroke();", "  }", "  /* sub muted */", "  var es=CL(P*2-1.1);", "  if(SB&&es>0.002){", "    ctx.globalAlpha=es;", "    ctx.font='400 40px Segoe UI, sans-serif';", "    ctx.fillStyle='" + MUTED + "';", "    ctx.fillText(SB,cx,wy+132+10*(1-es));", "  }", "}", "ctx.globalAlpha=1;ctx.restore();"], 560)

SCENES = {"mn_title": {"fn": mn_title, "doc": 'mn_title {"kicker":"TẬP 1","word":"VÒNG TRÒN","sub":"Từ tam giác đến vũ trụ"} — INTRO mở video (CHỈ dùng ở step 1): kicker mờ + TÊN CHỦ ĐỀ khổng lồ glow trắng viết dần + gạch chân + câu phụ; đơn sắc trắng-đen, word ngắn 1-3 từ', "demo": {"kicker": "TẬP 1", "word": "VÒNG TRÒN", "sub": "Từ tam giác đến vũ trụ"}}, "mn_chrome": {"fn": mn_chrome, "doc": 'mn_chrome {"brand":"Tên Kênh","progress":0.3} — khung kênh tối giản: brand mờ trên-phải + hairline progress trắng mảnh dưới đáy có chấm nhỏ (element ĐẦU TIÊN của mọi step)', "demo": {"brand": "HÌNH HỌC KỂ CHUYỆN", "progress": 0.42}}, "mn_unit_circle": {"fn": mn_unit_circle, "doc": 'mn_unit_circle {"title":"","deg":52,"show_sin_cos":true,"accent":"yellow"} — vòng tròn đơn vị tự vẽ nét: bán kính quay tới deg°, tam giác vuông sin/cos (cạnh sin accent), nét đứt gióng, số độ lớn đếm tăng bên phải', "demo": {"title": "Vòng tròn đơn vị", "deg": 52, "show_sin_cos": True, "accent": "yellow"}}, "mn_outro": {"fn": mn_outro, "doc": 'mn_outro {"brand":"Tên Kênh","line":"...","cta":"ĐĂNG KÝ"} — kết tối giản: hairline + brand trắng lớn + câu tagline muted + nút viền tròn tự vẽ nét rồi nhấp đảo outline↔filled', "demo": {"brand": "HÌNH HỌC KỂ CHUYỆN", "line": "Toán không khó — chỉ cần nhìn thấy nó.", "cta": "ĐĂNG KÝ"}}}
