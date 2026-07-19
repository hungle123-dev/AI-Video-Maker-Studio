"""core/scenes_mn_6.py — Bộ scene mathnoir #6: mn_pendulum, mn_spiral, mn_light_trail.

Phong cách manim/3Blue1Brown: nền đen tuyền (renderer lo), nét trắng mảnh
lw3 tự vẽ nét dần, chữ nhỏ gọn, accent vàng duy nhất khi cần nhấn.
Xem mn_spec.md + mn2_spec.md.
"""
import json, random
from core.custom_scenes import scene; INK = "#e8e8ea"; MUTED = "#9a9aa0"; AXIS = "rgba(232,232,234,0.45)"; DASH = "rgba(232,232,234,0.35)"; GOLD = "#facc15"; _TITLE_JS = "if(TITLE){ctx.globalAlpha=CL(P*2.2);ctx.font='600 34px Segoe UI, sans-serif';ctx.fillStyle='#8b8b92';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(TITLE,W/2,cursorY+40);ctx.globalAlpha=1;}"; _FORMULA_SPLIT_JS = "if(FML&&FA>0.01){ctx.globalAlpha=FA;ctx.font='400 '+FS+'px Segoe UI, sans-serif';ctx.textBaseline='middle';var qi=FML.indexOf('=');if(qi<0){ctx.textAlign='center';ctx.fillStyle='" + INK + "';ctx.fillText(FML,FX,FY);}else{var lf=FML.slice(0,qi+1), rt=FML.slice(qi+1);var wl=ctx.measureText(lf).width, wr=ctx.measureText(rt).width;var sx=FX-(wl+wr)/2;ctx.textAlign='left';ctx.fillStyle='" + INK + "';ctx.fillText(lf,sx,FY);ctx.fillStyle='" + GOLD + "';ctx.fillText(rt,sx+wl,FY);}ctx.globalAlpha=1;}"
def mn_pendulum(title="", length=520, label="T = 2π√(L/g)", trail=True, seed=0):
    try:
        length = max(240.0, min(560.0, float(length)))
    except (TypeError, ValueError):
        length = 520.0
    try:
        _r = random.Random(int(seed) if seed else 12_345)
    except (TypeError, ValueError):
        _r = random.Random(12_345)

    length = round(max(240.0, min(560.0, length * _r.choice([0.78, 0.885, 0.99, 1.1]))), 1)
    amp = round(_r.choice([0.48, 0.56, 0.64, 0.72]) + _r.uniform(-0.02, 0.02), 2)
    dx = round(_r.choice([-48.0, -24.0, 0.0, 24.0, 48.0]) + _r.uniform(-7.0, 7.0), 1)
    dy = round(_r.uniform(-24.0, 28.0), 1)
    ceil_w = round(_r.uniform(78.0, 114.0), 1)
    arc_r = round(_r.uniform(60.0, 84.0), 1)
    bob_r = round(max(20.0, min(30.0, length * 0.048)), 1)
    lbl_r = round(arc_r + 34.0, 1)
    h0, hs = round(ceil_w * 0.75, 1), round(ceil_w * 0.25, 1)
    return scene([
        "var TITLE=" + json.dumps(str(title), ensure_ascii=False) + ";",
        "var L=" + json.dumps(round(length, 1)) + ";",
        "var LBL=" + json.dumps(str(label), ensure_ascii=False) + ";",
        "var TRAIL=" + json.dumps(bool(trail)) + ";",
        "ctx.save();", "ctx.lineCap='round';ctx.lineJoin='round';ctx.textBaseline='middle';", _TITLE_JS,
        "var cx=W/2+" + json.dumps(dx) + ", cy=cursorY+" + json.dumps(round(140 + dy, 1)) + ";",
        "var AMP=" + json.dumps(amp) + ";",
        "/* ── tran + diem treo ── */", "var er=EZ(CL(P*1.8));", "if(er>0.01){",
        "  ctx.globalAlpha=er;", "  ctx.strokeStyle='" + AXIS + "';ctx.lineWidth=2;",
        "  ctx.beginPath();ctx.moveTo(cx-" + json.dumps(ceil_w) + "*er,cy-6);ctx.lineTo(cx+" + json.dumps(ceil_w) + "*er,cy-6);ctx.stroke();",
        "  /* gach cheo tran */", "  for(var h=0;h<7;h++){",
        "    var hx=cx-" + json.dumps(h0) + "+h*" + json.dumps(hs) + ";",
        "    ctx.beginPath();ctx.moveTo(hx,cy-8);ctx.lineTo(hx-13,cy-24);ctx.stroke();", "  }",
        "  ctx.globalAlpha=1;", "}",
        "/* ── goc lac theo time (bien do vao dan) ── */", "var ee=EZ(CL(P*1.5));",
        "var am=EZ(CL(P*1.4-0.3));", "var a=AMP*am*Math.sin(time*1.35);", "var LL=L*ee;",
        "var bx=cx+LL*Math.sin(a), by=cy+LL*Math.cos(a);",
        "/* ── duong tham chieu dung + cung quy dao net dut ── */", "var e2=EZ(CL(P*1.3-0.25));",
        "if(e2>0.01){", "  ctx.strokeStyle='" + DASH + "';ctx.lineWidth=2;",
        "  ctx.setLineDash([8,8]);ctx.lineDashOffset=-time*8;",
        "  ctx.beginPath();ctx.moveTo(cx,cy);ctx.lineTo(cx,cy+Math.min(240,L*0.5)*e2);ctx.stroke();",
        "  ctx.beginPath();ctx.arc(cx,cy,L,Math.PI/2-AMP*e2,Math.PI/2+AMP*e2);ctx.stroke();",
        "  ctx.setLineDash([]);ctx.lineDashOffset=0;", "}",
        "/* ── nhan goc theta o dinh ── */", "if(e2>0.5&&Math.abs(a)>0.05){",
        "  var ga=Math.min(1,Math.abs(a)/0.22)*e2;", "  ctx.globalAlpha=ga;",
        "  ctx.strokeStyle='" + AXIS + "';ctx.lineWidth=2;", "  ctx.beginPath();",
        "  if(a>0){ctx.arc(cx,cy," + json.dumps(arc_r) + ",Math.PI/2-a,Math.PI/2);}",
        "  else{ctx.arc(cx,cy," + json.dumps(arc_r) + ",Math.PI/2,Math.PI/2-a);}",
        "  ctx.stroke();", "  ctx.font='400 30px Segoe UI, sans-serif';ctx.fillStyle='" + MUTED + "';",
        "  ctx.textAlign='center';", "  var ma=Math.PI/2-a/2;",
        "  ctx.fillText('\\u03b8',cx+" + json.dumps(lbl_r) + "*Math.cos(ma),cy+" + json.dumps(lbl_r) + "*Math.sin(ma));",
        "  ctx.globalAlpha=1;", "}",
        "/* ── trail: 9 cham mo dan doc cung phia sau qua nang ── */", "var tra=CL((am-0.85)*8);",
        "if(TRAIL&&tra>0.01){", "  for(var i=1;i<=9;i++){",
        "    var ta=AMP*am*Math.sin((time-0.07*i)*1.35);",
        "    var tx=cx+LL*Math.sin(ta), ty=cy+LL*Math.cos(ta);",
        "    ctx.globalAlpha=tra*0.30*(1-i/10);", "    ctx.fillStyle='#fff';",
        "    ctx.beginPath();ctx.arc(tx,ty,6*(1-i/12),0,Math.PI*2);ctx.fill();", "  }",
        "  ctx.globalAlpha=1;", "}", "/* ── day + qua nang ── */", "if(ee>0.01){",
        "  ctx.strokeStyle='" + INK + "';ctx.lineWidth=2;",
        "  ctx.beginPath();ctx.moveTo(cx,cy);ctx.lineTo(bx,by);ctx.stroke();",
        "  /* diem treo: halo tho nhe theo time + cham trang */",
        "  ctx.fillStyle='rgba(255,255,255,'+(0.20+0.08*Math.sin(time*1.6)).toFixed(3)+')';",
        "  ctx.beginPath();ctx.arc(cx,cy,11,0,Math.PI*2);ctx.fill();", "  ctx.fillStyle='#fff';",
        "  ctx.beginPath();ctx.arc(cx,cy,6,0,Math.PI*2);ctx.fill();",
        "  /* qua nang: vong tron vien trang fill den, glow tho theo time */", "  ctx.fillStyle='#060607';",
        "  ctx.beginPath();ctx.arc(bx,by," + json.dumps(bob_r) + ",0,Math.PI*2);ctx.fill();",
        "  ctx.shadowColor='rgba(255,255,255,0.35)';ctx.shadowBlur=7+4*Math.sin(time*1.6);",
        "  ctx.strokeStyle='" + INK + "';ctx.lineWidth=3;",
        "  ctx.beginPath();ctx.arc(bx,by," + json.dumps(bob_r) + ",0,Math.PI*2);ctx.stroke();",
        "  ctx.shadowBlur=0;", "}",
        "/* ── cong thuc duoi cung: reveal MUON giua step (P2) ── */",
        "var FML=LBL, FX=W/2, FY=cursorY+806, FS=34, FA=EZ(CL(P2*3-1.5));",
        _FORMULA_SPLIT_JS, "ctx.restore();",
    ], 880)

def mn_spiral(title="", squares=True, label="1, 1, 2, 3, 5, 8, 13…", seed=0):
    try:
        _r = random.Random(int(seed) if seed else 12_345)
    except (TypeError, ValueError):
        _r = random.Random(12_345)
    u = round(_r.uniform(62.0, 79.0), 1)
    vy = round(_r.uniform(450.0, 490.0), 1)
    _dxm = max(0.0, (1080.0 - 13.0 * u) / 2.0 - 20.0)
    dx = round(_r.uniform(-_dxm, _dxm), 1)
    lw = round(_r.uniform(2.4, 3.8), 1)
    flip = bool(_r.random() < 0.5)
    return scene(["var TITLE=" + json.dumps(str(title), ensure_ascii=False) + ";", "var SQ=" + json.dumps(bool(squares)) + ";",
    
    "var LBL=" + json.dumps(str(label), ensure_ascii=False) + ";", "ctx.save();", "ctx.lineCap='round';ctx.lineJoin='round';ctx.textBaseline='middle';", _TITLE_JS, "/* golden rectangle 13x8 don vi; u px/don vi; tam khung tai (W/2+dx,cursorY+vy) */", "var u=" + json.dumps(u) + ";", "var ox=W/2-3.5*u+" + json.dumps(dx) + ", oy=cursorY+" + json.dumps(vy) + "-2*u;", "var FLIP=" + json.dumps(flip) + ";",
    
    "/* lat guong ngang quanh tam don vi x=3.5: diem x -> 7-x, canh trai o -> 7-x-c */", "function XP(x){return FLIP?7-x:x;}", "function XR(x,s){return FLIP?7-x-s:x;}", "var Q=Math.PI/2, PHI=1.6180339887;", "/* ── dung day cung 1/4: 8 cung trong (thu nho 1/phi) + 6 cung Fibonacci ── */", "var arcs=[], pt=[0,0], th=Math.PI, r=1, k;", "for(k=0;k<8;k++){", "  r=r/PHI;", "  var ce=[pt[0]-r*Math.cos(th),pt[1]-r*Math.sin(th)];", "  arcs.unshift([ce[0],ce[1],r,th+Q,th]);", "  pt=[ce[0]+r*Math.cos(th+Q),ce[1]+r*Math.sin(th+Q)];", "  th=th+Q;", "}", "var FIB=[1,1,2,3,5,8];", "pt=[0,0];th=Math.PI;", "for(k=0;k<6;k++){", "  r=FIB[k];", "  var c2=[pt[0]-r*Math.cos(th),pt[1]-r*Math.sin(th)];", "  arcs.push([c2[0],c2[1],r,th,th-Q]);", "  pt=[c2[0]+r*Math.cos(th-Q),c2[1]+r*Math.sin(th-Q)];", "  th=th-Q;", "}", "/* polyline day: xoan oc log ~ r=a*e^(0.306*theta), 3.5 vong */", "var PTS=[];", "for(k=0;k<arcs.length;k++){", "  var A=arcs[k];", "  var np=Math.max(8,Math.ceil(A[2]*u/9));", "  for(var i=(k===0?0:1);i<=np;i++){", "    var aa=A[3]+(A[4]-A[3])*(i/np);", "    PTS.push([ox+XP(A[0]+A[2]*Math.cos(aa))*u,oy+(A[1]+A[2]*Math.sin(aa))*u]);", "  }", "}", "/* ── float nhe ca nhom hinh theo time (idle, +/-3px) ── */", "ctx.save();ctx.translate(0,3*Math.sin(time*0.8));", "/* ── o vuong Fibonacci hien lan luot TRUOC khi xoan oc ve qua ── */", "if(SQ){", "  var RECT=[[0,0,1],[1,0,1],[0,-2,2],[-3,-2,3],[-3,1,5],[2,-2,8]];", "  ctx.strokeStyle='rgba(232,232,234,0.35)';ctx.lineWidth=2;",
    
    "  ctx.font='400 28px Segoe UI, sans-serif';ctx.fillStyle='" + MUTED + "';", "  ctx.textAlign='center';", "  for(k=0;k<6;k++){", "    var qa=EZ(CL(P*5-k*0.3));", "    if(qa>0.01){", "      var rx=ox+XR(RECT[k][0],RECT[k][2])*u, ry=oy+RECT[k][1]*u, rs=RECT[k][2]*u;", "      ctx.globalAlpha=qa;", "      ctx.strokeRect(rx,ry,rs,rs);", "      if(k>1){ctx.fillText(String(FIB[k]),rx+rs/2,ry+rs/2);}", "    }", "  }", "  ctx.globalAlpha=1;", "}", "/* ── xoan oc TU VE NET dan + cham glow chay o dau ── */", "var es=EZ(CL(P*1.15-0.2));", "var m=Math.min(PTS.length-1,Math.floor((PTS.length-1)*es));", "if(m>1){", "  ctx.strokeStyle='" + INK + "';ctx.lineWidth=" + json.dumps(lw) + ";", "  ctx.beginPath();ctx.moveTo(PTS[0][0],PTS[0][1]);", "  for(var j=1;j<=m;j++){ctx.lineTo(PTS[j][0],PTS[j][1]);}", "  ctx.stroke();", "  /* cham trang glow chay o dau xoan oc — mo dan khi ve xong */", "  var da=1-CL((P-0.9)*10);", "  if(da>0.01){", "    var hp=PTS[m];", "    ctx.globalAlpha=da;", "    ctx.fillStyle='rgba(255,255,255,0.25)';", "    ctx.beginPath();ctx.arc(hp[0],hp[1],14,0,Math.PI*2);ctx.fill();", "    ctx.shadowColor='rgba(255,255,255,0.35)';ctx.shadowBlur=8;", "    ctx.fillStyle='#fff';", "    ctx.beginPath();ctx.arc(hp[0],hp[1],7,0,Math.PI*2);ctx.fill();", "    ctx.shadowBlur=0;ctx.globalAlpha=1;", "  }", "  /* cham trang du hanh doc xoan oc sau khi ve xong (idle theo time) */", "  var wa=CL((P-0.95)*8);", "  if(wa>0.01){", "    var wp=PTS[Math.floor((PTS.length-1)*((time*0.12)%1))];", "    ctx.globalAlpha=wa;", "    ctx.fillStyle='rgba(255,255,255,0.22)';", "    ctx.beginPath();ctx.arc(wp[0],wp[1],11,0,Math.PI*2);ctx.fill();", "    ctx.shadowColor='rgba(255,255,255,0.35)';ctx.shadowBlur=7+4*Math.sin(time*1.6);", "    ctx.fillStyle='#fff';", "    ctx.beginPath();ctx.arc(wp[0],wp[1],5,0,Math.PI*2);ctx.fill();", "    ctx.shadowBlur=0;ctx.globalAlpha=1;", "  }", "}", "/* ── khung golden rectangle net dut mo — reveal MUON ~65% step (P2) ── */", "var fr=CL(P2*4-2.6);", "if(fr>0.01){", "  ctx.globalAlpha=fr*0.55;", "  ctx.strokeStyle='rgba(232,232,234,0.35)';ctx.lineWidth=2;", "  ctx.setLineDash([10,10]);ctx.lineDashOffset=-time*8;", "  ctx.strokeRect(ox-3*u-12,oy-2*u-12,13*u+24,8*u+24);", "  ctx.setLineDash([]);ctx.lineDashOffset=0;ctx.globalAlpha=1;",
    
    "}", "ctx.restore();", "/* ── nhan day so duoi: reveal MUON giua step (P2) ── */", "if(LBL){", "  ctx.globalAlpha=CL(P2*3-1.5);", "  ctx.font='400 30px Segoe UI, sans-serif';ctx.fillStyle='" + MUTED + "';", "  ctx.textAlign='center';", "  ctx.fillText(LBL,W/2,cursorY+862);", "  ctx.globalAlpha=1;", "}", "ctx.restore();"], 940)

_LT_KINDS = ("parabola", "arc_up", "sine_toss")
def mn_light_trail(title="", kind="parabola", from_label="ném", to_label="chạm đất", formula="y = v·t − ½gt²", seed=0):
    kind = str(kind).lower()
    if kind not in _LT_KINDS:
        kind = "parabola"
    try:
        _r = random.Random(int(seed) if seed else 12_345)
    except (TypeError, ValueError):
        _r = random.Random(12_345)
    m0 = round(_r.choice([100.0, 135.0, 170.0]) + _r.uniform(0.0, 10.0), 1)
    m1 = round(_r.choice([100.0, 135.0, 170.0]) + _r.uniform(0.0, 10.0), 1)
    hm = round(_r.choice([345.0, 395.0, 450.0]) + _r.uniform(-5.0, 5.0), 1)
    basey = round(600.0 + _r.uniform(-30.0, 25.0), 1)
    pb = round(_r.choice([0.72, 0.95, 1.18, 1.42]) + _r.uniform(-0.03, 0.03), 2)
    fq = round(_r.choice([1.9, 2.2, 2.5]) + _r.uniform(-0.05, 0.05), 2)
    pm = round(1.0 / (1.0 + pb) * (pb / (1.0 + pb))**pb, 4)
    return scene(["var TITLE=" + json.dumps(str(title), ensure_ascii=False) + ";",
    
    "var KIND=" + json.dumps(kind) + ";", "var FL=" + json.dumps(str(from_label), ensure_ascii=False) + ";", "var TL=" + json.dumps(str(to_label), ensure_ascii=False) + ";", "var LBL=" + json.dumps(str(formula), ensure_ascii=False) + ";",
    
    "ctx.save();",
    
    "ctx.lineCap='round';ctx.lineJoin='round';ctx.textBaseline='middle';", _TITLE_JS, "var x0=" + json.dumps(m0) + ", x1=W-" + json.dumps(m1) + ", base=cursorY+" + json.dumps(basey) + ", hm=" + json.dumps(hm) + ";",
    
    "function PY(t){", "  if(KIND==='arc_up'){return base-hm*Math.sin(t*Math.PI/2);}", "  if(KIND==='sine_toss'){return base-hm*0.85*Math.abs(Math.sin(t*Math.PI*" + json.dumps(fq) + "))*(1-0.5*t);}", "  return base-hm*0.95*(t*Math.pow(1-t," + json.dumps(pb) + "))/" + json.dumps(pm) + ";", "}", "var n=160, PTS=[];", "for(var i=0;i<=n;i++){var t=i/n;PTS.push([x0+(x1-x0)*t,PY(t)]);}", "/* ── duong dat mo (net dut ngang tai chan) ── */", "var eg=EZ(CL(P*1.8));", "if(eg>0.01&&KIND!=='arc_up'){", "  ctx.globalAlpha=eg;", "  ctx.strokeStyle='" + DASH + "';ctx.lineWidth=2;", "  ctx.setLineDash([8,8]);ctx.lineDashOffset=-time*8;", "  ctx.beginPath();ctx.moveTo(x0-30,base+26);ctx.lineTo(x0+(x1-x0+60)*eg-30,base+26);ctx.stroke();", "  ctx.setLineDash([]);ctx.lineDashOffset=0;ctx.globalAlpha=1;", "}", "/* ── vet sang TU VE NET dan ── */", "var e=EZ(CL(P*1.25));", "var m=Math.min(n,Math.floor(n*e));", "if(m>1){",
    
    "  ctx.strokeStyle='" + INK + "';ctx.lineWidth=3;",
    
    "  ctx.beginPath();ctx.moveTo(PTS[0][0],PTS[0][1]);", "  for(var j=1;j<=m;j++){ctx.lineTo(PTS[j][0],PTS[j][1]);}", "  ctx.stroke();", "  /* hat lap lanh roi rot doc vet (nhap theo time) */", "  var SPK=[0.16,0.33,0.5,0.67,0.84];", "  for(var s=0;s<5;s++){", "    var tk=SPK[s];", "    if(tk<=e){", "      var fall=(time*42+s*53)%64;", "      var sa=(1-fall/64)*(0.35+0.35*Math.sin(time*3.1+s*2.3));", "      if(sa>0.02){", "        ctx.globalAlpha=sa;", "        ctx.fillStyle='#fff';", "        ctx.beginPath();ctx.arc(x0+(x1-x0)*tk+(s%2?9:-9),PY(tk)+12+fall,3,0,Math.PI*2);ctx.fill();", "      }", "    }", "  }", "  ctx.globalAlpha=1;", "  /* DUOI PHAT SANG: 12 cham sau dau vet, nho + mo dan */", "  for(var q=12;q>=1;q--){", "    var qi=m-q*4;", "    if(qi>=0){",
    
    "      ctx.globalAlpha=0.5*(1-q/13);", "      ctx.fillStyle='#fff';", "      ctx.beginPath();ctx.arc(PTS[qi][0],PTS[qi][1],1.5+7*(1-q/13),0,Math.PI*2);ctx.fill();", "    }", "  }", "  ctx.globalAlpha=1;", "  /* cham dau vet r7 glow trang + halo tho nhe theo time */", "  var hd=PTS[m];", "  ctx.fillStyle='rgba(255,255,255,'+(0.20+0.08*Math.sin(time*1.6)).toFixed(3)+')';", "  ctx.beginPath();ctx.arc(hd[0],hd[1],14,0,Math.PI*2);ctx.fill();", "  ctx.shadowColor='rgba(255,255,255,0.35)';ctx.shadowBlur=7+4*Math.sin(time*1.6);", "  ctx.fillStyle='#fff';", "  ctx.beginPath();ctx.arc(hd[0],hd[1],7,0,Math.PI*2);ctx.fill();", "  ctx.shadowBlur=0;", "  /* cham nho du hanh lai doc quy dao sau khi ve xong (idle theo time) */", "  var va=CL((P-0.95)*8);", "  if(va>0.01){", "    var vp=PTS[Math.floor(n*((time*0.22)%1))];", "    ctx.globalAlpha=va*0.75;", "    ctx.fillStyle='#fff';", "    ctx.beginPath();ctx.arc(vp[0],vp[1],4,0,Math.PI*2);ctx.fill();", "    ctx.globalAlpha=1;", "  }", "}",
    
    "/* ── nhan 2 dau ── */",
    
    "ctx.font='400 28px Segoe UI, sans-serif';ctx.fillStyle='" + MUTED + "';", "if(FL){", "  ctx.globalAlpha=CL(P*2.4-0.2);", "  ctx.textAlign='center';", "  ctx.fillText(FL,x0,PY(0)+48);", "}", "if(TL){",
    
    "  /* nhan diem cuoi: reveal MUON ~65% step (P2) */", "  ctx.globalAlpha=CL(P2*4-2.6);", "  ctx.textAlign='center';", "  ctx.fillText(TL,x1,PY(1)+48);", "}", "ctx.globalAlpha=1;", "/* ── cong thuc: reveal MUON giua step (P2) ── */", "var FML=LBL, FX=W/2, FY=cursorY+740, FS=34, FA=EZ(CL(P2*3-1.5));", _FORMULA_SPLIT_JS, "ctx.restore();"], 840)

SCENES = {"mn_pendulum": {"fn": mn_pendulum, "doc": 'mn_pendulum {"title":"","length":520,"label":"T = 2π√(L/g)","trail":true} — con lắc dao động điều hoà: trần gạch chéo + dây lw2 + quả nặng viền trắng lắc ±35° theo thời gian, cung quỹ đạo nét đứt, nhãn góc θ, 9 chấm trail mờ dần, công thức dưới (vế phải vàng)', "demo": {"title": "Dao động điều hoà", "length": 520, "label": "T = 2π√(L/g)", "trail": True}}, "mn_spiral": {"fn": mn_spiral, "doc": 'mn_spiral {"title":"","squares":true,"label":"1, 1, 2, 3, 5, 8, 13…"} — xoắn ốc vàng (log, ~3.5 vòng) tự vẽ nét dần với chấm trắng glow chạy ở đầu; squares: các ô vuông Fibonacci 1,1,2,3,5,8 viền mờ hiện lần lượt đúng cấu trúc golden rectangle trước khi xoắn ốc vẽ qua', "demo": {"title": "Xoắn ốc vàng", "squares": True, "label": "1, 1, 2, 3, 5, 8, 13…"}}, "mn_light_trail": {"fn": mn_light_trail, "doc": 'mn_light_trail {"title":"","kind":"parabola","from_label":"ném","to_label":"chạm đất","formula":"y = v·t − ½gt²"} — vệt sáng quỹ đạo (parabola|arc_up|sine_toss) tự vẽ nét dần với đuôi phát sáng 12 chấm + chấm đầu glow, hạt lấp lánh rơi theo thời gian, nhãn 2 đầu, công thức dưới (vế phải vàng)', "demo": {"title": "Quỹ đạo cú ném", "kind": "parabola", "from_label": "ném", "to_label": "chạm đất", "formula": "y = v·t − ½gt²"}}}
