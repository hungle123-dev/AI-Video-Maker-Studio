"""core/scenes_mn_2.py — Bộ scene mathnoir #2: mn_sine_trace, mn_graph.

Phong cách manim/3Blue1Brown: nền đen tuyền (renderer lo), nét trắng mảnh
lw3, hình TỰ VẼ NÉT dần theo tiến độ, accent vàng duy nhất khi cần nhấn.
Xem mn_spec.md.
"""
import json, random
from core.custom_scenes import scene; _TITLE_JS = "if(TITLE){ctx.globalAlpha=CL(P*2.2);ctx.font='600 34px Segoe UI, sans-serif';ctx.fillStyle='#8b8b92';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(TITLE,W/2,cursorY+40);ctx.globalAlpha=1;}"
def mn_sine_trace(title="", cycles=2, label="góc", fn="sin", seed=0):
    try:
        cycles = max(1.0, min(4.0, float(cycles)))
        while 1:
            fn = "sin"
            _r = random.Random(12_345)
            _R = round(170 * _r.uniform(0.8, 1.18), 1)
            _A = round(170 * _r.uniform(0.8, 1.16), 1)
            _cx = round(_R + 34 + _r.uniform(20, 55), 1)
            _cyv = round(430 + _r.uniform(-45, 22), 1)
            _x0 = round(_cx + _R + 34 + _r.uniform(15, 58), 1)
            _ph0 = round(_r.uniform(0.0, 6.28), 2)
            return scene(["var TITLE=" + json.dumps(str(title), ensure_ascii=False) + ";", "var CYC=" + json.dumps(cycles) + ";", "var LBL=" + json.dumps(str(label), ensure_ascii=False) + ";", "var FN=" + json.dumps(fn) + ";", "ctx.save();", "ctx.lineCap='round';ctx.lineJoin='round';ctx.textBaseline='middle';",
    
    _TITLE_JS, "var cx=" + str(_cx) + ", cy=cursorY+" + str(_cyv) + ", R=" + str(_R) + ";", "var x0=" + str(_x0) + ", x1=W-60, A=" + str(_A) + ";",
    
    "/* song dung som hon truc de nhan cuoi truc khong de len song */", "var xw1=x1-104;", "var ph=time*1.4+" + str(_ph0) + ";", "function FV(a){return FN==='cos'?Math.cos(a):Math.sin(a);}", "/* goc diem tren vong tron sao cho cao do y = gia tri ham (sin/cos) */", "var dotA=(FN==='cos'?ph+Math.PI/2:ph);", "/* ── truc manh xuyen tam vong tron ── */", "var ea=EZ(CL(P*1.8));", "ctx.strokeStyle='rgba(232,232,234,0.45)';ctx.lineWidth=2;", "ctx.beginPath();ctx.moveTo(cx-(R+34)*ea,cy);ctx.lineTo(cx+(R+34)*ea,cy);ctx.stroke();", "ctx.beginPath();ctx.moveTo(cx,cy-(R+34)*ea);ctx.lineTo(cx,cy+(R+34)*ea);ctx.stroke();", "/* ── vong tron TU VE NET dan ── */", "var e=EZ(CL(P*1.4));", "if(e>0.002){", "  ctx.strokeStyle='#e8e8ea';ctx.lineWidth=3;", "  ctx.beginPath();ctx.arc(cx,cy,R,-Math.PI/2,-Math.PI/2+Math.PI*2*e);ctx.stroke();", "}", "/* ── truc hoanh song + mui ten + nhan ── */", "var e3=EZ(CL(P*1.5-0.1));", "if(e3>0){", "  ctx.strokeStyle='rgba(232,232,234,0.45)';ctx.lineWidth=2;", "  ctx.beginPath();ctx.moveTo(x0,cy);ctx.lineTo(x0+(x1-x0)*e3,cy);ctx.stroke();", "  /* truc tung nho tai dau song */", "  ctx.beginPath();ctx.moveTo(x0,cy+(A+44)*e3);ctx.lineTo(x0,cy-(A+44)*e3);ctx.stroke();", "}", "if(e3>0.96){", "  ctx.fillStyle='rgba(232,232,234,0.45)';", "  ctx.beginPath();ctx.moveTo(x1+8,cy);ctx.lineTo(x1-6,cy-6);ctx.lineTo(x1-6,cy+6);ctx.closePath();ctx.fill();", "  ctx.beginPath();ctx.moveTo(x0,cy-A-52);ctx.lineTo(x0-6,cy-A-38);ctx.lineTo(x0+6,cy-A-38);ctx.closePath();ctx.fill();", "}", "/* ── nhan truc: REVEAL MUON ~65% step (P2 cham) ── */", "var e5=CL(P2*4-2.6);", "if(e5>0){",
    
    "  ctx.globalAlpha=e5;", "  ctx.font='400 30px Segoe UI, sans-serif';ctx.fillStyle='#9a9aa0';", "  ctx.textAlign='right';ctx.fillText(LBL,x1,cy+42);", "  ctx.globalAlpha=1;", "}", "/* ── nhan 1/−1 + net dut o ±bien: REVEAL MUON giua step (P2) ── */", "var e4=CL(P2*3-1.5);", "if(e4>0){", "  ctx.globalAlpha=e4;", "  ctx.font='400 30px Segoe UI, sans-serif';ctx.fillStyle='#9a9aa0';", "  ctx.textAlign='right';", "  ctx.fillText('1',x0-16,cy-A);", "  ctx.fillText('\\u22121',x0-16,cy+A);", "  ctx.strokeStyle='rgba(232,232,234,0.35)';ctx.lineWidth=2;", "  ctx.setLineDash([8,8]);ctx.lineDashOffset=-time*8;", "  ctx.beginPath();ctx.moveTo(x0+12,cy-A);ctx.lineTo(x1-14,cy-A);ctx.stroke();", "  ctx.beginPath();ctx.moveTo(x0+12,cy+A);ctx.lineTo(x1-14,cy+A);ctx.stroke();", "  ctx.setLineDash([]);ctx.lineDashOffset=0;ctx.globalAlpha=1;", "}", "/* ── song TU VE toi diem hien tai, pha troi theo time ── */", "var e2=EZ(CL(P*1.3));", "var n=150, k=CYC*Math.PI*2;", "var m=Math.floor(n*e2);", "if(m>1){", "  ctx.strokeStyle='#e8e8ea';ctx.lineWidth=3;", "  ctx.beginPath();", "  for(var i=0;i<=m;i++){", "    var s=i/n, xv=x0+(xw1-x0)*s, yv=cy-A*FV(ph-s*k);", "    if(i===0)ctx.moveTo(xv,yv);else ctx.lineTo(xv,yv);", "  }", "  ctx.stroke();", "}", "/* ── ban kinh + diem quay + noi net dut sang dau song ── */", "var er=CL(P*2-0.8);", "if(er>0){", "  var pxx=cx+Math.cos(dotA)*R, pyy=cy-Math.sin(dotA)*R;", "  var hy=cy-A*FV(ph);", "  ctx.globalAlpha=er;", "  ctx.strokeStyle='#e8e8ea';ctx.lineWidth=3;", "  ctx.beginPath();ctx.moveTo(cx,cy);ctx.lineTo(pxx,pyy);ctx.stroke();", "  /* net dut ngang: diem vong tron ↔ dau song, dash troi theo time */",
    
    "  ctx.strokeStyle='rgba(232,232,234,0.35)';ctx.lineWidth=2;", "  ctx.setLineDash([8,8]);ctx.lineDashOffset=-time*8;", "  ctx.beginPath();ctx.moveTo(pxx,pyy);ctx.lineTo(x0,hy);ctx.stroke();", "  ctx.setLineDash([]);ctx.lineDashOffset=0;", "  /* cham diem tren vong tron: halo + glow tho phap (breathing) */", "  ctx.fillStyle='rgba(255,255,255,'+(0.2+0.05*Math.sin(time*1.6)).toFixed(3)+')';", "  ctx.beginPath();ctx.arc(pxx,pyy,14,0,Math.PI*2);ctx.fill();", "  ctx.beginPath();ctx.arc(x0,hy,14,0,Math.PI*2);ctx.fill();", "  ctx.shadowColor='rgba(255,255,255,0.35)';ctx.shadowBlur=8+4*Math.sin(time*1.6);", "  ctx.fillStyle='#fff';", "  ctx.beginPath();ctx.arc(pxx,pyy,7,0,Math.PI*2);ctx.fill();", "  ctx.beginPath();ctx.arc(x0,hy,7,0,Math.PI*2);ctx.fill();", "  ctx.shadowBlur=0;ctx.globalAlpha=1;", "}", "ctx.restore();"], 880)
    except:
        pass

_KINDS = ("parabola", "sin", "exp", "line", "sqrt")
def mn_graph(title="", kind="parabola", tangent=True, xlabel="x", ylabel="y", point_label="", seed=0):
    kind = str(kind).lower()
    if kind not in _KINDS:
        kind = "parabola"
    _r = random.Random(12_345); _HW = round(380 * _r.uniform(0.78, 1.13), 1); _HH = round(350 * _r.uniform(0.78, 1.12), 1); _cxo = round(-60 + _r.uniform(-48, 42), 1)
    
    _mo = round(_r.uniform(0, min(90.0, max(0.0, 810 - 2 * _HH))), 1); _cyv = round(908 - _HH - _mo, 1)
    
    _FX = round(_HW / 380.0 * 0.93, 3)
    
    _FY = round(_HH / 350.0 * _r.uniform(0.72, 1.08), 3)
    
    _phg = round(_r.uniform(0.0, 6.28), 2); _cxpy = 540 + _cxo
    
    _TL = round(min(158.0, _cxpy - 251.99999999999997 * _FX - 12, 1068 - _cxpy - 251.99999999999997 * _FX), 1)
    return scene(["var TITLE=" + json.dumps(str(title), ensure_ascii=False) + ";",
    
    "var KIND=" + json.dumps(kind) + ";", "var TAN=" + json.dumps(bool(tangent)) + ";", "var XL=" + json.dumps(str(xlabel), ensure_ascii=False) + ";", "var YL=" + json.dumps(str(ylabel), ensure_ascii=False) + ";", "var PL=" + json.dumps(str(point_label), ensure_ascii=False) + ";", "ctx.save();", "ctx.lineCap='round';ctx.lineJoin='round';ctx.textBaseline='middle';", _TITLE_JS, "/* float nhe ca cum ±3px theo time (title dung yen) */", "ctx.translate(0,3*Math.sin(time*0.8));", "var cx=W/2+(" + str(_cxo) + "), cy=cursorY+" + str(_cyv) + ", HW=" + str(_HW) + ", HH=" + str(_HH) + ";",
    
    "var FX=" + str(_FX) + ", FY=" + str(_FY) + ", TL=" + str(_TL) + ";", "/* ── truc x/y ve dan tu tam + mui ten ── */", "var ea=EZ(CL(P*1.6));", "if(ea>0){", "  ctx.strokeStyle='rgba(232,232,234,0.45)';ctx.lineWidth=2;", "  ctx.beginPath();ctx.moveTo(cx-HW*ea,cy);ctx.lineTo(cx+HW*ea,cy);ctx.stroke();", "  ctx.beginPath();ctx.moveTo(cx,cy+HH*ea);ctx.lineTo(cx,cy-HH*ea);ctx.stroke();", "}", "if(ea>0.96){", "  ctx.fillStyle='rgba(232,232,234,0.45)';", "  ctx.beginPath();ctx.moveTo(cx+HW+8,cy);ctx.lineTo(cx+HW-6,cy-6);ctx.lineTo(cx+HW-6,cy+6);ctx.closePath();ctx.fill();", "  ctx.beginPath();ctx.moveTo(cx,cy-HH-8);ctx.lineTo(cx-6,cy-HH+6);ctx.lineTo(cx+6,cy-HH+6);ctx.closePath();ctx.fill();", "  ctx.font='400 30px Segoe UI, sans-serif';ctx.fillStyle='#9a9aa0';", "  ctx.textAlign='center';", "  ctx.fillText(XL,cx+HW-12,cy+38);", "  ctx.fillText(YL,cx-36,cy-HH+12);", "}", "/* ── diem duong cong theo kind ── */", "var n=140, PTS=[];", "for(var i=0;i<=n;i++){", "  var t=i/n, u=-1+2*t, X, Y;", "  if(KIND==='sin'){X=u*360*FX;Y=-Math.sin(u*Math.PI*2)*230*FY;}",
    
    "  else if(KIND==='exp'){X=u*340*FX;Y=-Math.exp(u*1.6)*62*FY;}", "  else if(KIND==='line'){X=u*340*FX;Y=-u*280*FY;}", "  else if(KIND==='sqrt'){X=t*350*FX;Y=-Math.sqrt(t)*300*FY;}", "  else{X=u*340*FX;Y=-u*u*300*FY;}", "  PTS.push([cx+X,cy+Y]);", "}", "/* ── polyline TU VE toi chi so i<=n*e ── */", "var ec=EZ(CL(P*1.4-0.25));", "var m=Math.floor(n*ec);", "if(m>0){", "  ctx.strokeStyle='#e8e8ea';ctx.lineWidth=3;", "  ctx.beginPath();ctx.moveTo(PTS[0][0],PTS[0][1]);", "  for(var j=1;j<=m;j++){ctx.lineTo(PTS[j][0],PTS[j][1]);}", "  ctx.stroke();", "}", "/* ── tiep diem truot theo time: dung chung cho tiep tuyen + idle ── */", "var tt=0.5+0.35*Math.sin(time*0.7+" + str(_phg) + ");", "var fi=tt*n;", "var i0=Math.max(1,Math.min(n-1,Math.floor(fi)));", "var fr=fi-i0;", "var p0=PTS[i0], p1=PTS[i0+1], pm=PTS[i0-1];", "var px=p0[0]+(p1[0]-p0[0])*fr, py=p0[1]+(p1[1]-p0[1])*fr;", "var dx=p1[0]-pm[0], dy=p1[1]-pm[1];", "var dl=Math.sqrt(dx*dx+dy*dy)||1;dx/=dl;dy/=dl;", "/* ── REVEAL MUON ~65% step (P2): net dut FAINT tha toa do -> 2 truc */", "var eh=CL(P2*4-2.6);", "if(eh>0){",
    
    "  ctx.globalAlpha=eh;", "  ctx.strokeStyle='rgba(232,232,234,0.22)';ctx.lineWidth=2;", "  ctx.setLineDash([7,7]);ctx.lineDashOffset=-time*8;", "  ctx.beginPath();ctx.moveTo(px,py);ctx.lineTo(px,cy);ctx.stroke();", "  ctx.beginPath();ctx.moveTo(px,py);ctx.lineTo(cx,py);ctx.stroke();", "  ctx.setLineDash([]);ctx.lineDashOffset=0;ctx.globalAlpha=1;", "}", "/* ── tiep tuyen truot theo time (accent duy nhat) ── */", "if(TAN){", "  var ta=CL(P*2.5-1.5);", "  if(ta>0){", "    ctx.globalAlpha=ta;", "    ctx.strokeStyle='#facc15';ctx.lineWidth=3;", "    ctx.beginPath();ctx.moveTo(px-dx*TL,py-dy*TL);ctx.lineTo(px+dx*TL,py+dy*TL);ctx.stroke();", "    /* cham trang glow tho phap (breathing) tai tiep diem */", "    ctx.fillStyle='rgba(255,255,255,'+(0.2+0.05*Math.sin(time*1.6)).toFixed(3)+')';", "    ctx.beginPath();ctx.arc(px,py,14,0,Math.PI*2);ctx.fill();", "    ctx.shadowColor='rgba(255,255,255,0.35)';ctx.shadowBlur=8+4*Math.sin(time*1.6);", "    ctx.fillStyle='#fff';", "    ctx.beginPath();ctx.arc(px,py,7,0,Math.PI*2);ctx.fill();", "    ctx.shadowBlur=0;", "    if(PL){", "      /* nhan tiep diem: REVEAL MUON giua step (P2) */", "      var epl=CL(P2*3-1.5);", "      if(epl>0){", "        /* nhan lech theo phap tuyen (-dy,dx): phia ngoai duong cong */", "        var nx=-dy, ny=dx;", "        ctx.globalAlpha=ta*epl;", "        ctx.font='400 28px Segoe UI, sans-serif';ctx.fillStyle='#9a9aa0';", "        ctx.textAlign=(nx>=0?'left':'right');", "        ctx.fillText(PL,px+nx*52,py+ny*52);", "      }", "    }", "    ctx.globalAlpha=1;", "  }", "}else{", "  /* khong tiep tuyen: cham trang nho truot doc duong cong (idle) */", "  var ed=CL(P*2.5-1.5);", "  if(ed>0){", "    ctx.globalAlpha=ed*0.9;",
    
    "    ctx.shadowColor='rgba(255,255,255,0.35)';ctx.shadowBlur=8+4*Math.sin(time*1.6);", "    ctx.fillStyle='#fff';", "    ctx.beginPath();ctx.arc(px,py,5,0,Math.PI*2);ctx.fill();", "    ctx.shadowBlur=0;ctx.globalAlpha=1;", "  }", "}", "ctx.restore();"], 930)

SCENES = {"mn_sine_trace": {"fn": mn_sine_trace, "doc": 'mn_sine_trace {"title":"","cycles":2,"label":"góc","fn":"sin"} — vòng tròn đơn vị nhỏ bên trái có điểm quay theo thời gian, kéo ra sóng sin/cos trôi bên phải: sóng tự vẽ nét dần, nét đứt nối điểm tròn ↔ đầu sóng cùng cao độ, chấm trắng glow', "demo": {"title": "Sóng sin sinh ra từ vòng tròn", "cycles": 2, "label": "góc", "fn": "sin"}}, "mn_graph": {"fn": mn_graph, "doc": 'mn_graph {"title":"","kind":"parabola","tangent":true,"xlabel":"x","ylabel":"y","point_label":""} — trục toạ độ mũi tên + đồ thị hàm (parabola|sin|exp|line|sqrt) tự vẽ nét dần; tangent: tiếp tuyến vàng trượt dọc đường cong theo thời gian với chấm trắng glow tại tiếp điểm', "demo": {"title": "Đạo hàm = độ dốc tiếp tuyến", "kind": "parabola", "tangent": True, "xlabel": "x", "ylabel": "y", "point_label": "f′(x)"}}}
