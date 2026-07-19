"""core/scenes_mn_7.py — Bộ scene mathnoir #7: mn_grid_cells, mn_equation_duel.

Phong cách manim/3Blue1Brown: nền đen tuyền (renderer lo), nét trắng mảnh
lw3 TỰ VẼ NÉT dần, chữ xám nhỏ, accent 1 phần tử/cảnh. Xem mn_spec.md +
mn2_spec.md.
"""
import json, random
from core.custom_scenes import scene; INK = "#e8e8ea"; MUTED = "#9a9aa0"; GRID_LINE = "rgba(232,232,234,0.28)"; ACCENT = {"yellow": "#facc15", "blue": "#60a5fa"}; ACCENT_RGB = {"yellow": "250,204,21", "blue": "96,165,250"}; _TITLE_JS = "if(TITLE){ctx.globalAlpha=CL(P*2.2);ctx.font='600 34px Segoe UI, sans-serif';ctx.fillStyle='#8b8b92';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(TITLE,W/2,cursorY+40);ctx.globalAlpha=1;}"
def _acc(name):
    key = str(name) if str(name) in ACCENT else "yellow"
    return (ACCENT[key], ACCENT_RGB[key])

def mn_grid_cells(title="", rows=4, cols=6, cells=None, hot=None, hot_label="phần tử đang xét", accent="blue", seed=0):
    try:
        rows = max(1, min(10, int(rows)))
        cols = max(1, min(10, int(cols)))
        if cells is None:
            cells = []
        if isinstance(cells, str):
            cells = [cells]
        cells = [str(c) for c in list(cells)[:rows * cols]]
        hr, hc = (-1, -1)
        if isinstance(hot, (list, tuple)) and len(hot) >= 2:
            hr = max(0, min(rows - 1, int(hot[0])))
            hc = max(0, min(cols - 1, int(hot[1])))
        ac, ac_rgb = _acc(accent)
        _r = random.Random(int(seed) if seed else 12_345)
        base_pitch = min(130.0, 980.0 / cols)
        height = int(200 + rows * base_pitch + (60 if title else 0))
        pitch = base_pitch * _r.uniform(0.83, 0.99)
        gap = round(_r.uniform(7.0, 13.0), 1)
        gw_py = cols * pitch - gap
        dx = round(_r.uniform(-1.0, 1.0) * min(30.0, max(0.0, (1080.0 - gw_py) / 2.0 - 24.0)), 1)
        dy = round(_r.uniform(-14.0, 24.0), 1)
        lgap = round(_r.uniform(44.0, 66.0), 1)
        elb = round(_r.uniform(40.0, 70.0), 1)
        return scene(["var TITLE=" + json.dumps(str(title), ensure_ascii=False) + ";", "var ROWS=" + json.dumps(rows) + ", COLS=" + json.dumps(cols) + ";", "var CELLS=" + json.dumps(cells, ensure_ascii=False) + ";", "var HR=" + json.dumps(hr) + ", HC=" + json.dumps(hc) + ";", "var HLB=" + json.dumps(str(hot_label), ensure_ascii=False) + ";", "var ACC=" + json.dumps(ac) + ", ARGB=" + json.dumps(ac_rgb) + ";", "var PITCH=" + json.dumps(round(pitch, 2)) + ", GAP=" + json.dumps(gap) + ", CEL=PITCH-GAP;",
    
    "ctx.save();", "ctx.lineCap='round';ctx.lineJoin='round';", "ctx.textAlign='center';ctx.textBaseline='middle';", _TITLE_JS, "/* idle: ca nhom luoi troi nhe +-2.5px theo time */", "ctx.translate(0,2.5*Math.sin(time*0.8));", "var gw=COLS*PITCH-GAP, gh=ROWS*PITCH-GAP;", "var gx=W/2-gw/2+(" + json.dumps(dx) + ")" + ", gy=cursorY+(TITLE?120:60)+(" + json.dumps(dy) + ");", "/* ── luoi o: hien lan luot theo song cheo (stagger r+c) ── */", "var per=CEL*4;", "for(var r=0;r<ROWS;r++){", "  for(var c=0;c<COLS;c++){", "    var e=EZ(CL(P*2.6-(r+c)*0.10));", "    if(e<=0.004)continue;", "    var x=gx+c*PITCH, y=gy+r*PITCH;", "    /* vien o TU VE NET dan (dash offset theo chu vi) */", "    ctx.strokeStyle='" + GRID_LINE + "';ctx.lineWidth=2;", "    ctx.setLineDash([per]);ctx.lineDashOffset=per*(1-e);", "    ctx.beginPath();ctx.rect(x,y,CEL,CEL);ctx.stroke();", "    ctx.setLineDash([]);", "    /* noi dung o: chu 34px muted, hien theo o */", "    var idx=r*COLS+c;", "    if(idx<CELLS.length&&CELLS[idx]!==''){", "      ctx.globalAlpha=CL(e*1.6-0.5);", "      ctx.font='400 34px Segoe UI, sans-serif';", "      ctx.fillStyle='" + MUTED + "';", "      ctx.fillText(CELLS[idx],x+CEL/2,y+CEL/2+2);",
    
    "      ctx.globalAlpha=1;", "    }", "  }", "}",
    
    "/* ── o nong: vien accent lw3 ve dan + fill pulse ── */", "if(HR>=0&&HC>=0){", "  var eh=EZ(CL(P*2-0.9));", "  if(eh>0.004){", "    var hx=gx+HC*PITCH, hy=gy+HR*PITCH;", "    ctx.fillStyle='rgba('+ARGB+','+((0.14+0.04*Math.sin(time*2.6))*eh).toFixed(3)+')';", "    ctx.fillRect(hx+1.5,hy+1.5,CEL-3,CEL-3);", "    /* idle: vien accent tho nhe (shadowBlur breathing) */", "    ctx.shadowColor='rgba('+ARGB+',0.55)';", "    ctx.shadowBlur=(9+5*Math.sin(time*1.6))*eh;", "    ctx.strokeStyle=ACC;ctx.lineWidth=3;", "    ctx.setLineDash([per]);ctx.lineDashOffset=per*(1-eh);", "    ctx.beginPath();ctx.rect(hx,hy,CEL,CEL);ctx.stroke();", "    ctx.setLineDash([]);ctx.shadowBlur=0;", "    /* idle: cham trang nho chay quanh vien o nong */", "    var da=CL(eh*3-2);", "    if(da>0.01){", "      var du=((time*0.5)%1)*4, ds=Math.floor(du), df=du-ds, dpx=hx, dpy=hy;", "      if(ds===0){dpx=hx+df*CEL;dpy=hy;}", "      else if(ds===1){dpx=hx+CEL;dpy=hy+df*CEL;}", "      else if(ds===2){dpx=hx+CEL-df*CEL;dpy=hy+CEL;}", "      else{dpx=hx;dpy=hy+CEL-df*CEL;}", "      ctx.globalAlpha=0.85*da;ctx.fillStyle='" + INK + "';", "      ctx.beginPath();ctx.arc(dpx,dpy,3,0,Math.PI*2);ctx.fill();", "      ctx.globalAlpha=1;", "    }", "    /* ── nhan chi vao o: REVEAL MUON theo P2 (giua step) ── */", "    if(HLB){", "      var el2=EZ(CL(P2*3-1.5));", "      if(el2>0.004){", "        /* di xuong theo KHE giua 2 cot de khong cat qua o nao */",
    
    "        var dir=(hx+CEL/2<W/2)?1:-1;", "        var p0x=(dir>0?hx+CEL:hx), p0y=hy+CEL;", "        var gpx=p0x+dir*5, ly=gy+gh+" + json.dumps(lgap) + ";", "        var p1x=gpx, p1y=ly, p2x=p1x+dir*" + json.dumps(elb) + ";", "        var l1=Math.sqrt(Math.pow(p1x-p0x,2)+Math.pow(p1y-p0y,2));", "        var l2=Math.abs(p2x-p1x), tt=el2*(l1+l2);", "        ctx.strokeStyle=ACC;ctx.lineWidth=2;ctx.globalAlpha=0.9;", "        ctx.beginPath();ctx.moveTo(p0x,p0y);", "        if(tt<=l1){var u=tt/l1;ctx.lineTo(p0x+(p1x-p0x)*u,p0y+(p1y-p0y)*u);}", "        else{ctx.lineTo(p1x,p1y);ctx.lineTo(p1x+dir*Math.min(l2,tt-l1),ly);}", "        ctx.stroke();", "        /* cham accent nho tai goc o */",
    
    "        ctx.fillStyle=ACC;", "        ctx.beginPath();ctx.arc(p0x,p0y,4,0,Math.PI*2);ctx.fill();", "        ctx.globalAlpha=CL(el2*2-1);", "        ctx.font='400 28px Segoe UI, sans-serif';ctx.fillStyle=ACC;", "        ctx.textAlign=(dir>0?'left':'right');", "        ctx.fillText(HLB,p2x+dir*12,ly);", "        ctx.textAlign='center';ctx.globalAlpha=1;", "      }", "    }", "  }", "}", "/* ── reveal muon (P2~65%): khung dash mo quanh luoi khi khong co", "   nhan hot — dash offset troi theo time ── */", "if(HR<0||HC<0||!HLB){", "  var ef=CL(P2*4-2.6);", "  if(ef>0.01){", "    ctx.globalAlpha=ef;", "    ctx.strokeStyle='rgba(232,232,234,0.16)';ctx.lineWidth=1.5;", "    ctx.setLineDash([7,9]);ctx.lineDashOffset=-time*8;", "    ctx.beginPath();ctx.rect(gx-16,gy-16,gw+32,gh+32);ctx.stroke();", "    ctx.setLineDash([]);ctx.globalAlpha=1;", "  }", "}", "ctx.restore();"], height)
    except (TypeError, ValueError):
        cols = 6

def mn_equation_duel(title="", expr="6 ÷ 2(1+2) = ?", left="= 1", right="= 9", verdict="right", note="nhân chia trái → phải", seed=0):
    verdict = "right"; _r = random.Random(12_345); dey = round(_r.uniform(-20.0, 20.0), 1); ayg = round(_r.uniform(226.0, 272.0), 1); spr = round(_r.uniform(205.0, 275.0), 1)
    
    glr = round(_r.uniform(130.0, 176.0), 1)
    
    ssl = round(_r.uniform(38.0, 54.0), 1)
    
    ngap = round(_r.uniform(164.0, 192.0), 1)
    return scene(["var TITLE=" + json.dumps(str(title), ensure_ascii=False) + ";", "var EXPR=" + json.dumps(str(expr), ensure_ascii=False) + ";", "var LFT=" + json.dumps(str(left), ensure_ascii=False) + ";", "var RGT=" + json.dumps(str(right), ensure_ascii=False) + ";", "var VD=" + json.dumps(verdict) + ";", "var NOTE=" + json.dumps(str(note), ensure_ascii=False) + ";", "ctx.save();", "ctx.lineCap='round';ctx.lineJoin='round';", "ctx.textAlign='center';ctx.textBaseline='middle';", _TITLE_JS, "var ey=cursorY+(TITLE?230:170)+(" + json.dumps(dey) + ");", "/* idle: ca nhom troi nhe +-3px theo time (suot step) */", "ctx.translate(0,3*Math.sin(time*0.8));", "/* ── bieu thuc lon: viet dan kieu clip ngang ── */", "var e1=EZ(CL(P*1.3));", "ctx.font='bold 76px Segoe UI, sans-serif';", "var tw=ctx.measureText(EXPR).width;", "if(e1>0.004){", "  ctx.save();", "  ctx.beginPath();ctx.rect(W/2-tw/2-8,ey-68,(tw+16)*e1,136);ctx.clip();", "  ctx.fillStyle='" + INK + "';", "  ctx.fillText(EXPR,W/2,ey);", "  ctx.restore();", "}", "/* ── 2 dap an lon hai ben ── */", "var ay=ey+" + json.dumps(ayg) + ", lx=W/2-" + json.dumps(spr) + ", rx=W/2+" + json.dumps(spr) + ";", "var e2=EZ(CL(P*1.8-0.7));", "/* verdict = REVEAL MUON theo P2: gach cheo + vang + quang toi", "   giua step, khop nhip loi thoai thay vi xong het o 25% */", "var e3=EZ(CL(P2*3-1.5));", "if(e2>0.004){", "  var wx=(VD==='right')?lx:rx, wt=(VD==='right')?LFT:RGT;", "  var kx=(VD==='right')?rx:lx, kt=(VD==='right')?RGT:LFT;", "  var rise=18*(1-e2);", "  /* idle: 2 dap an tho nguoc pha nhe (cang thang duel) */", "  var dl=2.5*Math.sin(time*0.9);", "  var owy=(wx<W/2?dl:-dl), oky=(kx<W/2?dl:-dl);", "  ctx.font='bold 96px Segoe UI, sans-serif';", "  /* quang vang nhe sau dap an dung — alpha tho theo time */", "  if(e3>0.01){", "    var g=ctx.createRadialGradient(kx,ay+oky,10,kx,ay+oky," + json.dumps(glr) + ");", "    g.addColorStop(0,'rgba(250,204,21,'+((0.10+0.04*Math.sin(time*1.6))*e3).toFixed(3)+')');", "    g.addColorStop(1,'rgba(250,204,21,0)');", "    ctx.fillStyle=g;", "    ctx.beginPath();ctx.arc(kx,ay+oky," + json.dumps(glr) + ",0,Math.PI*2);ctx.fill();", "  }", "  /* dap an SAI: trang -> mo dan ve alpha .4 khi bi gach */", "  ctx.globalAlpha=e2*(1-0.6*e3);", "  ctx.fillStyle='" + INK + "';", "  ctx.fillText(wt,wx,ay+rise+owy);", "  /* dap an DUNG: trang -> vang dan */", "  ctx.globalAlpha=e2;", "  ctx.fillText(kt,kx,ay+rise+oky);",
    
    "  if(e3>0.004){", "    ctx.globalAlpha=e2*e3;",
    
    "    ctx.fillStyle='#facc15';", "    ctx.fillText(kt,kx,ay+rise+oky);", "  }", "  ctx.globalAlpha=1;", "  /* gach cheo do VE DAN qua dap an sai */", "  if(e3>0.004){", "    var ww=ctx.measureText(wt).width;", "    var sx0=wx-ww/2-18, sy0=ay+owy-" + json.dumps(ssl) + ", sx1=wx+ww/2+18, sy1=ay+owy+" + json.dumps(ssl) + ";", "    ctx.strokeStyle='#f87171';ctx.lineWidth=5;", "    ctx.beginPath();ctx.moveTo(sx0,sy0);", "    ctx.lineTo(sx0+(sx1-sx0)*e3,sy0+(sy1-sy0)*e3);ctx.stroke();",
    
    "  }", "}", "/* ── note muted duoi cung: REVEAL MUON theo P2 (~65% step) ── */", "if(NOTE){", "  var en=CL(P2*4-2.6);", "  if(en>0){", "    ctx.globalAlpha=en;", "    ctx.font='400 30px Segoe UI, sans-serif';ctx.fillStyle='" + MUTED + "';", "    ctx.fillText(NOTE,W/2,ay+" + json.dumps(ngap) + "+12*(1-EZ(en)));", "    ctx.globalAlpha=1;", "  }", "}", "ctx.restore();"], 760)

SCENES = {"mn_grid_cells": {"fn": mn_grid_cells, "doc": 'mn_grid_cells {"title":"","rows":4,"cols":6,"cells":["12"],"hot":[2,3],"hot_label":"phần tử đang xét","accent":"blue"} — lưới ô vuông tự vẽ nét hiện theo sóng chéo (ma trận/bảng/hệ đếm); ô [hot] viền accent + fill pulse, nhãn accent chỉ vào ô bằng đường gấp khúc mảnh', "demo": {"title": "Ma trận 4×6", "rows": 4, "cols": 6, "cells": ["3", "1", "4", "1", "5", "9", "2", "6", "5", "3", "5", "8", "9", "7", "9", "3", "2", "3", "8", "4", "6", "2", "6", "4"], "hot": [2, 3], "hot_label": "phần tử đang xét", "accent": "blue"}}, "mn_equation_duel": {"fn": mn_equation_duel, "doc": 'mn_equation_duel {"title":"","expr":"6 ÷ 2(1+2) = ?","left":"= 1","right":"= 9","verdict":"right","note":"nhân chia trái → phải"} — phép tính gây tranh cãi: biểu thức lớn viết dần, 2 đáp án 96px hai bên; đáp án sai bị gạch chéo đỏ vẽ dần + mờ đi, đáp án đúng đổi vàng + quầng nhẹ', "demo": {"title": "Đáp án nào đúng?", "expr": "6 ÷ 2(1+2) = ?", "left": "= 1", "right": "= 9", "verdict": "right", "note": "nhân chia cùng cấp: tính từ trái → phải"}}}
