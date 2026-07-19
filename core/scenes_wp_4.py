"""core/scenes_wp_4.py — Bộ scene warmpaper #4: wp_grid, wp_before_after, wp_news_card.

Phong cách poster tin công nghệ nền kem ấm (renderer lo nền: kem + lưới nhạt
+ glow cam). Chữ đen ấm #211a12, card trắng bo tròn bóng mềm, chip tag màu.
Xem wp_spec.md. KHÔNG chữ trắng trên nền sáng, KHÔNG glow neon.
"""
import json
from core.custom_scenes import scene; _WP = "var AC={orange:'#e8590c',red:'#d9480f',blue:'#1c7ed6',green:'#2f9e44',gray:'#adb5bd'};var INK='#211a12',GRY='#8a7a66',MONO='#b0a08c',SOFT='rgba(160,110,60,0.18)';function HA(h,a){return 'rgba('+parseInt(h.slice(1,3),16)+','+parseInt(h.slice(3,5),16)+','+parseInt(h.slice(5,7),16)+','+a+')';}function SH(on){if(on){ctx.shadowColor='rgba(160,110,60,0.18)';ctx.shadowBlur=18;ctx.shadowOffsetY=6;}else{ctx.shadowColor='rgba(0,0,0,0)';ctx.shadowBlur=0;ctx.shadowOffsetY=0;}}function CHIP(t,acc,cy){ctx.font='bold 30px Segoe UI, sans-serif';var w=ctx.measureText(t).width+44,x=W/2-w/2;ctx.fillStyle=HA(acc,0.12);RR(x,cy,w,56,10);ctx.fill();ctx.strokeStyle=HA(acc,0.45);ctx.lineWidth=1.5;RR(x,cy,w,56,10);ctx.stroke();ctx.fillStyle=acc;ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(t,W/2,cy+30);}function TITLE(t,ty){var f=64;ctx.font='bold 64px Segoe UI, sans-serif';var ls=[t];if(ctx.measureText(t).width>W-140){f=54;ls=wrapText(t,W-140,'bold 54px Segoe UI').slice(0,2);}var lh=f+14;ctx.fillStyle=INK;ctx.textAlign='center';ctx.textBaseline='middle';ctx.font='bold '+f+'px Segoe UI, sans-serif';ls.forEach(function(l,i){ctx.fillText(l,W/2,ty+lh/2+i*lh);});return ty+ls.length*lh;}function HASCK(t){return !!t&&t.charAt(0)==='\\u2713';}function NOCK(t){if(HASCK(t)){t=t.slice(1);while(t.length&&t.charAt(0)===' '){t=t.slice(1);}}return t;}function CKM(x,y,s,c){ctx.save();ctx.strokeStyle=c;ctx.lineWidth=Math.max(3,s*0.2);ctx.lineCap='round';ctx.lineJoin='round';ctx.beginPath();ctx.moveTo(x-s*0.45,y+s*0.02);ctx.lineTo(x-s*0.08,y+s*0.36);ctx.lineTo(x+s*0.5,y-s*0.34);ctx.stroke();ctx.restore();}"; ACCENT = {"orange": "#e8590c", "red": "#d9480f", "blue": "#1c7ed6", "green": "#2f9e44", "gray": "#adb5bd"}
def _title_h(title):
    if len(str(title)) * 33 > 940:
        return 136
    
    return 78

def wp_grid(tag="HỆ SINH THÁI", color="blue", title="7 nhà cùng lên chuyến", en="SANDBOX PROVIDERS · 7", items=None, check="✓ đã kết nối", footer="FILESYSTEM · 4 kho: S3 · Azure · GCS · R2"):
    if not items:
        items = [{"name": "Vercel"},
        {"name": "Modal"},
        {"name": "Cloudflare"},
        {"name": "E2B"},
        {"name": "Blaxel"},
        {"name": "Daytona"},
        {"name": "Runloop"}]
    norm = []
    for it in items[:8]:
        norm.append({"n": str(it.get("name", "")) if isinstance(it, dict) else str(it)})
    rows = max(1, (len(norm) + 3) // 4); gy = 84 + _title_h(title) + 18 + (54 if en else 0) + 26
    
    height = gy + rows * 150 + (rows - 1) * 22 + (92 if footer else 0) + 34
    return scene([_WP,
    
    "var TAG=" + json.dumps(str(tag), ensure_ascii=False) + ";", "var TT=" + json.dumps(str(title), ensure_ascii=False) + ";", "var EN=" + json.dumps(str(en or ""), ensure_ascii=False) + ";", "var ITEMS=" + json.dumps(norm, ensure_ascii=False) + ";",
    
    "var CHK=" + json.dumps(str(check or ""), ensure_ascii=False) + ";", "var FT=" + json.dumps(str(footer or ""), ensure_ascii=False) + ";", "var ACC=AC[" + json.dumps(str(color)) + "]||AC.blue;", "var y0=cursorY;",
    
    "ctx.save();", "/* ── header: chip + tiêu đề + dòng EN mono ── */", "var hp=EZ(CL(P*2.2));", "ctx.globalAlpha=hp;", "CHIP(TAG,ACC,y0);", "var tb=TITLE(TT,y0+84);", "var gy=tb+18;", "if(EN){ctx.fillStyle=MONO;ctx.font='bold 30px Consolas, monospace';", "  ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(EN,W/2,gy+20);gy+=54;}", "gy+=26;", "ctx.globalAlpha=1;", "/* ── lưới card 225×150: hàng 1 tối đa 4, hàng sau căn giữa ── */", "var cw=225,chh=150,gap=12,n=ITEMS.length;",
    
    "ITEMS.forEach(function(it,i){", "  var t=CL(P*2.6-0.35-i*0.12);if(t<=0)return;", "  var e=EB(t);", "  var row=Math.floor(i/4),idx=i%4;", "  var cnt=Math.min(4,n-row*4);", "  var x0=W/2-(cnt*cw+(cnt-1)*gap)/2;", "  var cx=x0+idx*(cw+gap),cy=gy+row*(chh+22);", "  ctx.save();", "  ctx.globalAlpha=CL(t*1.6);", "  ctx.translate(cx+cw/2,cy+chh/2);ctx.scale(0.75+0.25*e,0.75+0.25*e);", "  SH(true);ctx.fillStyle='rgba(255,255,255,0.92)';RR(-cw/2,-chh/2,cw,chh,18);ctx.fill();SH(false);", "  ctx.strokeStyle=SOFT;ctx.lineWidth=1.5;RR(-cw/2,-chh/2,cw,chh,18);ctx.stroke();", "  ctx.textAlign='center';ctx.textBaseline='middle';", "  var f=34;ctx.font='bold '+f+'px Consolas, monospace';",
    
    "  while(ctx.measureText(it.n).width>cw-28&&f>22){f-=1;ctx.font='bold '+f+'px Consolas, monospace';}", "  ctx.fillStyle=AC.blue;ctx.fillText(it.n,0,CHK?-16:0);", "  if(CHK){", "    var hc=HASCK(CHK),ct2=NOCK(CHK);", "    ctx.fillStyle=AC.green;ctx.font='24px Segoe UI, sans-serif';", "    var tw2=ctx.measureText(ct2).width,offs=hc?15:0;", "    ctx.fillText(ct2,offs,30);", "    if(hc){CKM(offs-tw2/2-18,30,19,AC.green);}", "  }", "  ctx.restore();",
    
    "});", "/* ── footer: card ngang mờ chữ mono xám ── */", "if(FT){", "  var fp=CL(P*2.2-1.2);", "  if(fp>0){", "    var rows=Math.ceil(n/4);", "    var fy=gy+rows*(chh+22)+6;", "    ctx.globalAlpha=fp;", "    ctx.fillStyle='rgba(255,255,255,0.45)';RR(70,fy,W-140,64,16);ctx.fill();", "    ctx.strokeStyle=SOFT;ctx.lineWidth=1.5;RR(70,fy,W-140,64,16);ctx.stroke();", "    var f2=26;ctx.font='bold '+f2+'px Consolas, monospace';", "    while(ctx.measureText(FT).width>W-190&&f2>18){f2-=1;ctx.font='bold '+f2+'px Consolas, monospace';}", "    ctx.fillStyle=GRY;ctx.textAlign='center';ctx.textBaseline='middle';", "    ctx.fillText(FT,W/2,fy+33);", "  }", "}", "ctx.globalAlpha=1;ctx.restore();"], height)

def wp_before_after(tag="KIẾN TRÚC", color="blue", title="Não và tay, tách hẳn", old=None, new=None):
    d_old = {"head": "OLD · GỘP CHUNG", "sub": "não và sandbox dính nhau", "boxes": ["SERVER", "SANDBOX: harness + file + khoá"], "warn": "sandbox sập là não đi theo"}
    if isinstance(old, dict):
        d_old.update(old)
    d_new = {"head": "NEW · TÁCH RIÊNG", "sub": "não chạy chỗ tin cậy, sandbox chỉ chạy code", "left": ["SECRETS", "AGENT LOOP", "MCP · TOOLS"], "left_title": "TRUSTED HARNESS", "right": ["chạy code", "lưu file"], "right_title": "SANDBOX", "ok": "khoá không bao giờ vào sandbox"}
    if isinstance(new, dict):
        d_new.update(new)
    if not d_old.get("boxes"):
        d_old["boxes"] = []
    od = {
        "h": str(d_old.get("head", "")),
        "s": str(d_old.get("sub", "")),
        "b": [str(x) for x in d_old.get("boxes", [])][:3],
        "w": str(d_old.get("warn", "")),
    }
    
    if not d_new.get("left"):
        d_new["left"] = []
    if not d_new.get("right"):
        d_new["right"] = []
    nw = {
        "h": str(d_new.get("head", "")),
        "s": str(d_new.get("sub", "")),
        "lt": str(d_new.get("left_title", "")),
        "li": [str(x) for x in d_new.get("left", [])][:4],
        "rt": str(d_new.get("right_title", "")),
        "ri": [str(x) for x in d_new.get("right", [])][:4],
        "ok": str(d_new.get("ok", "")),
    }
    nb = max(1, len(od["b"]))
    
    oh = 130 + nb * 84 - 18 + (84 if od["w"] else 0) + 30
    
    nmax = max(len(nw["li"]), len(nw["ri"]), 1); col_h = 72 + nmax * 72; nh = 126 + col_h + (82 if nw["ok"] else 0) + 30; height = 84 + _title_h(title) + 40 + oh + 66 + nh + 24
    return scene([_WP, "var TAG=" + json.dumps(str(tag), ensure_ascii=False) + ";",
    
    "var TT=" + json.dumps(str(title), ensure_ascii=False) + ";", "var OD=" + json.dumps(od, ensure_ascii=False) + ";", "var NW=" + json.dumps(nw, ensure_ascii=False) + ";", "var ACC=AC[" + json.dumps(str(color)) + "]||AC.blue;", "var y0=cursorY;", "ctx.save();", "/* ── header ── */", "var hp=EZ(CL(P*2.2));", "ctx.globalAlpha=hp;",
    
    "CHIP(TAG,ACC,y0);", "var tb=TITLE(TT,y0+84);", "ctx.globalAlpha=1;", "var px=70,pw=W-140;", "/* ── panel OLD mờ 0.55 ── */", "var oy=tb+40,nb=OD.b.length;", "var oh=130+nb*84-18+(OD.w?84:0)+30;", "var op=CL(P*2-0.25);", "if(op>0){", "  var oe=EZ(op);", "  ctx.save();ctx.translate(0,14*(1-oe));", "  ctx.globalAlpha=0.55*op;", "  SH(true);ctx.fillStyle='rgba(255,255,255,0.92)';RR(px,oy,pw,oh,22);ctx.fill();SH(false);", "  ctx.strokeStyle=SOFT;ctx.lineWidth=1.5;RR(px,oy,pw,oh,22);ctx.stroke();", "  ctx.textAlign='center';ctx.textBaseline='middle';", "  ctx.fillStyle=AC.orange;ctx.font='bold 30px Consolas, monospace';", "  ctx.fillText(OD.h,W/2,oy+50);", "  ctx.fillStyle=GRY;ctx.font='24px Segoe UI, sans-serif';", "  ctx.fillText(OD.s,W/2,oy+92);", "  var bx=px+56,bw=pw-112;", "  OD.b.forEach(function(b,i){", "    var byy=oy+130+i*84;", "    ctx.setLineDash([9,7]);ctx.strokeStyle=MONO;ctx.lineWidth=2;", "    RR(bx,byy,bw,66,12);ctx.stroke();ctx.setLineDash([]);", "    ctx.fillStyle=INK;var f=26;ctx.font=f+'px Segoe UI, sans-serif';", "    while(ctx.measureText(b).width>bw-40&&f>19){f-=1;ctx.font=f+'px Segoe UI, sans-serif';}", "    ctx.fillText(b,W/2,byy+34);", "  });", "  if(OD.w){", "    var wy2=oy+130+nb*84-18+26;", "    ctx.fillStyle=HA(AC.red,0.12);RR(bx,wy2,bw,58,12);ctx.fill();", "    var wtx=OD.w;", "    var f2=28;ctx.font='bold '+f2+'px Segoe UI, sans-serif';", "    while(ctx.measureText(wtx).width>bw-110&&f2>20){f2-=1;ctx.font='bold '+f2+'px Segoe UI, sans-serif';}", "    var wtw=ctx.measureText(wtx).width;", "    ctx.fillStyle=AC.red;ctx.fillText(wtx,W/2+16,wy2+30);", "    /* tam giác cảnh báo vector */",
    
    "    var txx=W/2+16-wtw/2-28,tyy=wy2+30;", "    ctx.beginPath();ctx.moveTo(txx,tyy-13);ctx.lineTo(txx+13,tyy+10);ctx.lineTo(txx-13,tyy+10);", "    ctx.closePath();ctx.strokeStyle=AC.red;ctx.lineWidth=3;ctx.lineJoin='round';ctx.stroke();", "    ctx.fillStyle=AC.red;ctx.fillRect(txx-1.5,tyy-6,3,10);", "    ctx.beginPath();ctx.arc(txx,tyy+7,2,0,Math.PI*2);ctx.fill();", "  }", "  ctx.restore();", "}", "/* ── mũi tên ▼ xám giữa ── */", "var ap=CL(P*2-0.55);", "if(ap>0){", "  var ae=EZ(ap);", "  ctx.globalAlpha=ap;", "  ctx.fillStyle='#a4917a';ctx.font='44px Segoe UI, sans-serif';", "  ctx.textAlign='center';ctx.textBaseline='middle';", "  ctx.fillText('\\u25bc',W/2,oy+oh+33-10*(1-ae));", "  ctx.globalAlpha=1;", "}", "/* ── panel NEW: head + 2 cột + thanh ok ── */", "var ny=oy+oh+66;", "var nmax=Math.max(NW.li.length,NW.ri.length,1);", "var colH=72+nmax*72;", "var nh=126+colH+(NW.ok?82:0)+30;", "var np2=CL(P*2-0.7);", "if(np2>0){", "  var ne=EZ(np2);", "  ctx.save();ctx.translate(0,16*(1-ne));", "  ctx.globalAlpha=np2;", "  SH(true);ctx.fillStyle='rgba(255,255,255,0.92)';RR(px,ny,pw,nh,22);ctx.fill();SH(false);", "  ctx.strokeStyle=SOFT;ctx.lineWidth=1.5;RR(px,ny,pw,nh,22);ctx.stroke();", "  ctx.textAlign='center';ctx.textBaseline='middle';", "  ctx.fillStyle=AC.blue;ctx.font='bold 30px Consolas, monospace';", "  ctx.fillText(NW.h,W/2,ny+50);", "  ctx.fillStyle=GRY;ctx.font='24px Segoe UI, sans-serif';", "  ctx.fillText(NW.s,W/2,ny+92);", "  var gp=26,cw2=(pw-gp*3)/2,cy2=ny+126;", "  var cols=[{x:px+gp,t:NW.lt,it:NW.li,c:AC.blue},", "            {x:px+gp*2+cw2,t:NW.rt,it:NW.ri,c:AC.green}];", "  cols.forEach(function(co,ci){", "    var t=CL(P*2.4-1.0-ci*0.2);if(t<=0)return;", "    ctx.globalAlpha=np2*t;", "    ctx.fillStyle=HA(co.c,0.10);RR(co.x,cy2,cw2,colH,16);ctx.fill();", "    ctx.strokeStyle=HA(co.c,0.30);ctx.lineWidth=1.5;RR(co.x,cy2,cw2,colH,16);ctx.stroke();", "    ctx.fillStyle=co.c;var ctf=24;ctx.font='bold '+ctf+'px Consolas, monospace';", "    while(ctx.measureText(co.t).width>cw2-30&&ctf>16){ctf-=1;ctx.font='bold '+ctf+'px Consolas, monospace';}", "    ctx.fillText(co.t,co.x+cw2/2,cy2+38);", "    co.it.forEach(function(s,i){", "      var it2=CL(P*3-1.5-ci*0.2-i*0.15);if(it2<=0)return;", "      var iy=cy2+68+i*72;", "      ctx.globalAlpha=np2*t*it2;", "      ctx.fillStyle='rgba(255,255,255,0.92)';RR(co.x+16,iy,cw2-32,58,12);ctx.fill();", "      ctx.strokeStyle=SOFT;ctx.lineWidth=1.5;RR(co.x+16,iy,cw2-32,58,12);ctx.stroke();", "      ctx.fillStyle=INK;var f3=26;ctx.font=f3+'px Segoe UI, sans-serif';",
    
    "      while(ctx.measureText(s).width>cw2-64&&f3>18){f3-=1;ctx.font=f3+'px Segoe UI, sans-serif';}", "      ctx.fillText(s,co.x+cw2/2,iy+30);", "    });", "  });", "  if(NW.ok){", "    var okp=CL(P*2.6-1.55);", "    if(okp>0){",
    
    "      ctx.globalAlpha=np2*okp;", "      var oky=cy2+colH+24;",
    
    "      ctx.fillStyle=HA(AC.green,0.12);RR(px+gp,oky,pw-gp*2,58,12);ctx.fill();", "      var ot=NOCK(NW.ok);", "      var f4=28;ctx.font='bold '+f4+'px Segoe UI, sans-serif';", "      while(ctx.measureText(ot).width>pw-gp*2-100&&f4>20){f4-=1;ctx.font='bold '+f4+'px Segoe UI, sans-serif';}", "      var otw=ctx.measureText(ot).width;", "      ctx.fillStyle=AC.green;ctx.fillText(ot,W/2+15,oky+30);", "      CKM(W/2+15-otw/2-24,oky+30,22,AC.green);", "    }", "  }", "  ctx.restore();", "}", "ctx.globalAlpha=1;ctx.restore();"], height)
    
def wp_news_card(chip_left="OpenAI · 2026.04.15", chip_right="Agents SDK v0.14", title="Harness mở nguồn thật", win=None, cross=None, foot="não điều phối agent", foot2="nguồn công khai"):
    d_win = {"bar": "OPEN SOURCE · MODEL-NATIVE", "word": "HARNESS", "sub": "não điều phối agent · loop · tools · memory", "badge": "✓ SOURCE AVAILABLE"}
    if isinstance(win, dict):
        d_win.update(win)
    d_cross = {"old": "closeAI", "new": "OpenAI", "note": "lần này mở thật"}
    if isinstance(cross, dict):
        d_cross.update(cross)
    
    wn = {"bar": str(d_win.get("bar", "")), "word": str(d_win.get("word", "")), "sub": str(d_win.get("sub", "")), "badge": str(d_win.get("badge", ""))}
    
    cr = {"o": str(d_cross.get("old", "")), "n": str(d_cross.get("new", "")), "t": str(d_cross.get("note", ""))}; tl = 2 if len(str(title)) * 41 > 940 else 1; tbot = 104 + tl * 96; sy = tbot + 44 + 400 + 42; height = sy + 104 + 74 + (64 if foot2 else 0) + 46
    return scene([_WP, "var CL1=" + json.dumps(str(chip_left), ensure_ascii=False) + ";", "var CR1=" + json.dumps(str(chip_right), ensure_ascii=False) + ";", "var TT=" + json.dumps(str(title), ensure_ascii=False) + ";", "var WIN=" + json.dumps(wn, ensure_ascii=False) + ";", "var CRS=" + json.dumps(cr, ensure_ascii=False) + ";", "var FOOT=" + json.dumps(str(foot or ""), ensure_ascii=False) + ";", "var FOOT2=" + json.dumps(str(foot2 or ""), ensure_ascii=False) + ";", "var y0=cursorY;", "ctx.save();", "ctx.textBaseline='middle';", "/* ── hàng chip: trái nền đen chữ kem, phải nền xanh nhạt ── */", "var cp=EZ(CL(P*2.4));", "ctx.globalAlpha=cp;", "ctx.font='bold 28px Consolas, monospace';", "var lw1=ctx.measureText(CL1).width+48;", "ctx.fillStyle=INK;RR(70,y0,lw1,56,10);ctx.fill();", "ctx.fillStyle='#fbf3e7';ctx.textAlign='center';ctx.fillText(CL1,70+lw1/2,y0+30);", "ctx.font='28px Consolas, monospace';", "var rw1=ctx.measureText(CR1).width+48;", "var rx0=W-70-rw1;", "ctx.fillStyle=HA(AC.blue,0.14);RR(rx0,y0,rw1,56,10);ctx.fill();", "ctx.strokeStyle=HA(AC.blue,0.35);ctx.lineWidth=1.5;RR(rx0,y0,rw1,56,10);ctx.stroke();", "ctx.fillStyle=AC.blue;ctx.fillText(CR1,rx0+rw1/2,y0+30);", "/* ── tiêu đề lớn 78px ink ── */", "var tp=CL(P*2.2-0.2);", "ctx.globalAlpha=EZ(tp);", "ctx.font='bold 78px Segoe UI, sans-serif';var tls=[TT];", "if(ctx.measureText(TT).width>W-140){tls=wrapText(TT,W-140,'bold 78px Segoe UI').slice(0,2);}", "ctx.fillStyle=INK;ctx.textAlign='center';", "var ty=y0+104;", "tls.forEach(function(l,i){", "  var ff=78;ctx.font='bold '+ff+'px Segoe UI, sans-serif';", "  while(ctx.measureText(l).width>W-140&&ff>54){ff-=2;ctx.font='bold '+ff+'px Segoe UI, sans-serif';}", "  ctx.fillText(l,W/2,ty+48+i*96+14*(1-EZ(tp)));",
    
    "});", "var tbot=ty+tls.length*96;",
    
    "/* ── card cửa sổ: thanh title 3 chấm + word + sub + badge ── */", "var wx=100,ww=W-200,wy=tbot+44,wh=400;", "var wp2=CL(P*2-0.4);", "if(wp2>0){", "  var we=EZ(wp2);", "  ctx.save();ctx.translate(0,20*(1-we));", "  ctx.globalAlpha=wp2;", "  SH(true);ctx.fillStyle='rgba(255,255,255,0.95)';RR(wx,wy,ww,wh,22);ctx.fill();SH(false);", "  ctx.strokeStyle=SOFT;ctx.lineWidth=1.5;RR(wx,wy,ww,wh,22);ctx.stroke();", "  ctx.save();RR(wx,wy,ww,wh,22);ctx.clip();", "  ctx.fillStyle=HA(AC.orange,0.13);ctx.fillRect(wx,wy,ww,56);", "  ctx.strokeStyle=SOFT;ctx.lineWidth=1.5;", "  ctx.beginPath();ctx.moveTo(wx,wy+56);ctx.lineTo(wx+ww,wy+56);ctx.stroke();", "  ctx.restore();", "  var dc=['#d9480f','#fab005','#2f9e44'];", "  dc.forEach(function(c,i){ctx.fillStyle=c;ctx.beginPath();", "    ctx.arc(wx+36+i*32,wy+28,8,0,Math.PI*2);ctx.fill();});", "  if(WIN.bar){", "    ctx.fillStyle=GRY;ctx.font='bold 22px Consolas, monospace';ctx.textAlign='right';", "    var bt=WIN.bar;", "    while(ctx.measureText(bt).width>ww-150&&bt.length>4){bt=bt.slice(0,-2);}", "    ctx.fillText(bt,wx+ww-26,wy+29);", "  }", "  ctx.textAlign='center';", "  var kp2=CL(P*2.6-1.0);", "  if(kp2>0){", "    var ks=0.78+0.22*EB(kp2);", "    ctx.save();ctx.translate(W/2,wy+160);ctx.scale(ks,ks);", "    ctx.globalAlpha=wp2*CL(kp2*1.8);", "    ctx.fillStyle=AC.blue;var wf=64;ctx.font='bold '+wf+'px Consolas, monospace';", "    while(ctx.measureText(WIN.word).width>ww-80&&wf>36){wf-=2;ctx.font='bold '+wf+'px Consolas, monospace';}", "    ctx.fillText(WIN.word,0,0);", "    ctx.restore();", "  }", "  ctx.globalAlpha=wp2;", "  if(WIN.sub){", "    ctx.fillStyle=GRY;var sf=26;ctx.font=sf+'px Segoe UI, sans-serif';", "    while(ctx.measureText(WIN.sub).width>ww-60&&sf>19){sf-=1;ctx.font=sf+'px Segoe UI, sans-serif';}", "    ctx.fillText(WIN.sub,W/2,wy+238);", "  }", "  if(WIN.badge){", "    var hc2=HASCK(WIN.badge),bg=NOCK(WIN.badge);", "    ctx.font='bold 26px Consolas, monospace';", "    var btw=ctx.measureText(bg).width;", "    var bw2=btw+44+(hc2?32:0);", "    ctx.fillStyle=HA(AC.blue,0.12);RR(W/2-bw2/2,wy+284,bw2,52,12);ctx.fill();", "    ctx.strokeStyle=HA(AC.blue,0.35);ctx.lineWidth=1.5;RR(W/2-bw2/2,wy+284,bw2,52,12);ctx.stroke();", "    ctx.fillStyle=AC.blue;ctx.fillText(bg,W/2+(hc2?16:0),wy+311);", "    if(hc2){CKM(W/2+16-btw/2-22,wy+311,20,AC.blue);}", "  }", "  ctx.restore();", "}", "/* ── hàng gạch bỏ: old đỏ (gạch vẽ dần theo P) → new xanh + note ── */", "var sy=wy+wh+42,sh2=104;",
    
    "var sp=CL(P*2-0.7);", "if(sp>0){", "  var se=EZ(sp);",
    
    "  ctx.save();ctx.translate(0,16*(1-se));", "  ctx.globalAlpha=sp;", "  SH(true);ctx.fillStyle='rgba(255,255,255,0.92)';RR(70,sy,W-140,sh2,18);ctx.fill();SH(false);",
    
    "  ctx.strokeStyle=SOFT;ctx.lineWidth=1.5;RR(70,sy,W-140,sh2,18);ctx.stroke();", "  ctx.font='32px Consolas, monospace';var ow=ctx.measureText(CRS.o).width;", "  ctx.font='bold 32px Consolas, monospace';var nw2=ctx.measureText(CRS.n).width;",
    
    "  ctx.font='24px Segoe UI, sans-serif';var tw3=CRS.t?ctx.measureText(CRS.t).width:0;", "  var aw=72,g2=26;", "  var tot=ow+aw+nw2+(tw3>0?g2+tw3:0);", "  var x0=W/2-tot/2,ym=sy+sh2/2;", "  ctx.textAlign='left';", "  ctx.fillStyle=AC.red;ctx.font='32px Consolas, monospace';ctx.fillText(CRS.o,x0,ym);", "  var kp=CL(P*3-1.9);", "  if(kp>0){", "    var ke=EZ(kp);", "    ctx.strokeStyle=AC.red;ctx.lineWidth=4;ctx.lineCap='round';", "    ctx.beginPath();ctx.moveTo(x0-6,ym+4);", "    ctx.lineTo(x0-6+(ow+12)*ke,ym+4-10*ke);ctx.stroke();", "  }", "  var ax=x0+ow+16;", "  ctx.strokeStyle='#a4917a';ctx.lineWidth=3.5;ctx.lineCap='round';", "  ctx.beginPath();ctx.moveTo(ax,ym);ctx.lineTo(ax+32,ym);ctx.stroke();", "  ctx.fillStyle='#a4917a';ctx.beginPath();ctx.moveTo(ax+44,ym);", "  ctx.lineTo(ax+30,ym-9);ctx.lineTo(ax+30,ym+9);ctx.closePath();ctx.fill();", "  ctx.fillStyle=AC.blue;ctx.font='bold 32px Consolas, monospace';", "  ctx.fillText(CRS.n,x0+ow+aw,ym);", "  if(tw3>0){ctx.fillStyle=GRY;ctx.font='24px Segoe UI, sans-serif';",
    
    "    ctx.fillText(CRS.t,x0+ow+aw+nw2+g2,ym);}", "  ctx.restore();",
    
    "}", "/* ── foot ink + foot2 cam ── */", "var fp=CL(P*2-0.95);", "if(fp>0){", "  var fe=EZ(fp);", "  ctx.globalAlpha=fp;ctx.textAlign='center';", "  var fy=sy+sh2+74;", "  if(FOOT){", "    ctx.fillStyle=INK;var ff2=44;ctx.font='bold '+ff2+'px Segoe UI, sans-serif';", "    while(ctx.measureText(FOOT).width>W-140&&ff2>30){ff2-=2;ctx.font='bold '+ff2+'px Segoe UI, sans-serif';}", "    ctx.fillText(FOOT,W/2,fy+10*(1-fe));", "  }", "  if(FOOT2){", "    ctx.fillStyle=AC.orange;var ff3=36;ctx.font='bold '+ff3+'px Segoe UI, sans-serif';", "    while(ctx.measureText(FOOT2).width>W-140&&ff3>24){ff3-=2;ctx.font='bold '+ff3+'px Segoe UI, sans-serif';}", "    ctx.fillText(FOOT2,W/2,fy+64+10*(1-fe));", "  }", "}", "ctx.globalAlpha=1;ctx.restore();"], height)

SCENES = {"wp_grid": {"fn": wp_grid, "doc": 'wp_grid {"tag":"HỆ SINH THÁI","color":"blue","title":"7 nhà cùng lên chuyến","en":"SANDBOX PROVIDERS · 7","items":[{"name":"Vercel"},...],"check":"✓ đã kết nối","footer":"FILESYSTEM · ..."} — lưới nhà cung cấp: card trắng 225×150 name mono xanh + check xanh lá, hàng 1 tối đa 4 card hàng sau căn giữa, footer card ngang mờ', "demo": {"tag": "HỆ SINH THÁI", "color": "blue", "title": "7 nhà cùng lên chuyến", "en": "SANDBOX PROVIDERS · 7", "items": [{"name": "Vercel"},
    {"name": "Modal"},
    {"name": "Cloudflare"},
    {"name": "E2B"},
    {"name": "Blaxel"},
    {"name": "Daytona"},
    {"name": "Runloop"}], "check": "✓ đã kết nối", "footer": "FILESYSTEM · 4 kho: S3 · Azure · GCS · R2"}}, "wp_before_after": {"fn": wp_before_after, "doc": 'wp_before_after {"tag":"KIẾN TRÚC","color":"blue","title":"Não và tay, tách hẳn","old":{"head":"OLD · GỘP CHUNG","sub":"...","boxes":["..."],"warn":"..."},"new":{"head":"NEW · TÁCH RIÊNG","sub":"...","left":["..."],"left_title":"...","right":["..."],"right_title":"...","ok":"..."}} — kiến trúc cũ (panel mờ, box viền đứt, thanh warn đỏ) → mũi tên ▼ → mới (2 cột xanh dương/xanh lá, thanh ok green)', "demo": {"tag": "KIẾN TRÚC", "color": "blue", "title": "Não và tay, tách hẳn", "old": {"head": "OLD · GỘP CHUNG", "sub": "não và sandbox dính nhau", "boxes": ["SERVER", "SANDBOX: harness + file + khoá"], "warn": "sandbox sập là não đi theo"}, "new": {"head": "NEW · TÁCH RIÊNG", "sub": "não chạy chỗ tin cậy, sandbox chỉ chạy code", "left": ["SECRETS", "AGENT LOOP", "MCP · TOOLS"], "left_title": "TRUSTED HARNESS", "right": ["chạy code", "lưu file"], "right_title": "SANDBOX", "ok": "khoá không bao giờ vào sandbox"}}}, "wp_news_card": {"fn": wp_news_card, "doc": 'wp_news_card {"chip_left":"OpenAI · 2026.04.15","chip_right":"Agents SDK v0.14","title":"Harness mở nguồn thật","win":{"bar":"...","word":"HARNESS","sub":"...","badge":"..."},"cross":{"old":"closeAI","new":"OpenAI","note":"..."},"foot":"...","foot2":"..."} — tin chính: chip đen + chip xanh, tiêu đề 78px, card cửa sổ (thanh title 3 chấm + từ khoá mono xanh + badge), hàng gạch bỏ đỏ→xanh, foot ink + cam', "demo": {"chip_left": "OpenAI · 2026.04.15", "chip_right": "Agents SDK v0.14", "title": "Harness mở nguồn thật", "win": {"bar": "OPEN SOURCE · MODEL-NATIVE", "word": "HARNESS", "sub": "não điều phối agent · loop · tools · memory", "badge": "✓ SOURCE AVAILABLE"}, "cross": {"old": "closeAI", "new": "OpenAI", "note": "lần này mở thật"}, "foot": "não điều phối agent", "foot2": "nguồn công khai"}}}
