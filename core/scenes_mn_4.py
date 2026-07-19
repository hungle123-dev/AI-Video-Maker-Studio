"""core/scenes_mn_4.py — Bộ scene mathnoir #4: mn_number_line,
mn_triangle_anatomy, mn_transform.

Phong cách manim/3Blue1Brown: nền đen tuyền (renderer lo), nét trắng mảnh
lw3 tự vẽ dần, chữ nhỏ gọn muted, accent (vàng/xanh) đúng 1 phần tử/cảnh.
Xem mn_spec.md.
"""
import inspect, json, keyword, random
from core.custom_scenes import scene; INK = "#e8e8ea"; MUT = "#9a9aa0"; SUB = "rgba(232,232,234,0.45)"; DSH = "rgba(232,232,234,0.35)"; YEL = "#facc15"; BLU = "#60a5fa"; _LBL = "'400 30px Segoe UI, sans-serif'"; _TCK = "'400 28px Segoe UI, sans-serif'"
from core.triangle_body import BODY as _TRIANGLE_BODY
def _title_js(title):
    return ["var TITLE=" + json.dumps(str(title or ""), ensure_ascii=False) + ";", "if(TITLE){", "  ctx.save();ctx.globalAlpha=CL(P*2.5);", "  ctx.font='600 34px Segoe UI, sans-serif';ctx.fillStyle='#8b8b92';", "  ctx.textAlign='center';ctx.textBaseline='middle';", "  ctx.fillText(TITLE,W/2,cursorY+40);", "  ctx.restore();", "}"]

def _kw_signature(pairs):
    ps = []
    for name, default in pairs:
        safe = name + "_" if keyword.iskeyword(name) else name
        p = inspect.Parameter(safe, inspect.Parameter.KEYWORD_ONLY, default=default)
        if safe != name:
            object.__setattr__(p, "_name", name)
        ps.append(p)
    return inspect.Signature(ps)

def mn_number_line(**kw):
    title = str(kw.get("title", "")); a = float(kw.get("from", kw.get("frm", -3))); b = float(kw.get("to", 5))
    if b <= a:
        b = a + 1.0
    point = max(a, min(b, float(kw.get("point", 2)))); rng = kw.get("range")
    
    if not isinstance(rng, (list, tuple)) or len(rng) < 2:
        rng = [0, 3]
    
    r0 = max(a, min(b, float(min(rng[0], rng[1])))); r1 = max(a, min(b, float(max(rng[0], rng[1])))); range_label = str(kw.get("range_label", "")); point_label = str(kw.get("point_label", "x = 2"))
    
    seed = kw.get("seed", 0)
    
    _r = random.Random("mn_nl:%d" % (int(seed) if seed else 12_345))
    
    ayo = round(_r.uniform(-30, 40)); mrg = round(_r.uniform(85, 155))
    
    amp = round(_r.uniform(58, 86)); blw = round(_r.uniform(6.0, 10.0), 1); plo = round(_r.uniform(80, 118))
    return scene(_title_js(title) + ["var A=" + json.dumps(a) + ", B=" + json.dumps(b) + ";", "var PT=" + json.dumps(point) + ";", "var R0=" + json.dumps(r0) + ", R1=" + json.dumps(r1) + ";", "var RL=" + json.dumps(range_label, ensure_ascii=False) + ";", "var PL=" + json.dumps(point_label, ensure_ascii=False) + ";", "ctx.save();ctx.lineCap='round';ctx.lineJoin='round';", "ctx.textAlign='center';ctx.textBaseline='middle';", "/* idle: cả nhóm trôi nhẹ ±3px theo time */", "ctx.translate(0,3*Math.sin(time*0.8));", "var ay=cursorY+(TITLE?" + str(280 + ayo) + ":" + str(230 + ayo) + ");", "var ax=" + str(mrg) + ", aw=W-" + str(2 * mrg) + ";", "function X(v){return ax+(v-A)/(B-A)*aw;}", "/* ── trục ngang tự vẽ dần ── */", "var e=EZ(CL(P*1.5));", "var reach=ax-16+(aw+32)*e;", "ctx.strokeStyle=" + json.dumps(SUB) + ";ctx.lineWidth=2;", "ctx.beginPath();ctx.moveTo(ax-16,ay);ctx.lineTo(reach,ay);ctx.stroke();", "var ha=CL(e*10-9);", "if(ha>0){", "  ctx.globalAlpha=ha;ctx.fillStyle=" + json.dumps(SUB) + ";", "  ctx.beginPath();ctx.moveTo(ax+aw+28,ay);", "  ctx.lineTo(ax+aw+12,ay-7);ctx.lineTo(ax+aw+12,ay+7);", "  ctx.closePath();ctx.fill();ctx.globalAlpha=1;", "}", "/* tick + nhãn số hiện theo đầu nét */", "ctx.font=" + _TCK + ";", "for(var v=Math.ceil(A);v<=Math.floor(B);v++){", "  var tx=X(v);", "  var al=CL((reach+12-tx)/28);", "  if(al<=0)continue;", "  ctx.globalAlpha=al;", "  ctx.strokeStyle=" + json.dumps(SUB) + ";ctx.lineWidth=2;", "  ctx.beginPath();ctx.moveTo(tx,ay-11);ctx.lineTo(tx,ay+11);ctx.stroke();", "  ctx.fillStyle=" + json.dumps(MUT) + ";", "  ctx.fillText(String(v),tx,ay+44);",
    
    "  ctx.globalAlpha=1;", "}", "/* ── đoạn [R0,R1] tô xanh — accent duy nhất ── */", "var e2=EZ(CL(P*1.7-0.5));", "if(e2>0&&R1>R0){", "  var x0=X(R0), x1=x0+(X(R1)-x0)*e2;", "  ctx.globalAlpha=0.8;", "  ctx.strokeStyle=" + json.dumps(BLU) + ";ctx.lineWidth=" + str(blw) + ";", "  ctx.beginPath();ctx.moveTo(x0,ay);ctx.lineTo(x1,ay);ctx.stroke();", "  ctx.globalAlpha=1;", "  ctx.fillStyle=" + json.dumps(BLU) + ";", "  ctx.beginPath();ctx.arc(x0,ay," + str(blw) + ",0,Math.PI*2);ctx.fill();", "  ctx.beginPath();ctx.arc(x1,ay," + str(blw) + ",0,Math.PI*2);ctx.fill();", "  /* idle: chấm trắng nhỏ chạy qua lại trên đoạn xanh */", "  if(e2>=1){", "    var tu=0.5-0.5*Math.cos(time*1.0);", "    ctx.globalAlpha=0.75;ctx.fillStyle='#fff';", "    ctx.beginPath();ctx.arc(X(R0)+(X(R1)-X(R0))*tu,ay,3.5,0,Math.PI*2);ctx.fill();", "    ctx.globalAlpha=1;", "  }", "  if(RL){", "    /* reveal muộn ~giữa step theo P2 */", "    ctx.globalAlpha=CL(P2*3-1.5);", "    ctx.font=" + _TCK + ";", "    ctx.fillText(RL,(X(R0)+X(R1))/2,ay-42);", "    ctx.globalAlpha=1;", "  }", "}", "/* ── điểm nhảy tới PT (nảy EB + vồng lên) ── */", "var t3=CL(P*2.2-1.2);", "if(t3>0){", "  var px=X(A)+(X(PT)-X(A))*EB(t3);", "  var py=ay-" + str(amp) + "*Math.sin(Math.PI*t3);", "  /* idle: glow thở nhẹ khi điểm đã đáp */", "  ctx.shadowColor='rgba(255,255,255,0.35)';", "  ctx.shadowBlur=(t3<1)?8:7+5*Math.sin(time*1.6);", "  ctx.fillStyle='rgba(255,255,255,0.25)';", "  ctx.beginPath();ctx.arc(px,py,14,0,Math.PI*2);ctx.fill();", "  ctx.fillStyle='#fff';", "  ctx.beginPath();ctx.arc(px,py,7,0,Math.PI*2);ctx.fill();", "  ctx.shadowBlur=0;", "  if(PL){", "    /* reveal muộn ~65% step theo P2 */",
    
    "    ctx.globalAlpha=CL(P2*4-2.6);", "    ctx.font=" + _LBL + ";ctx.fillStyle=" + json.dumps(INK) + ";", "    ctx.fillText(PL,X(PT),ay+" + str(plo) + ");", "    ctx.globalAlpha=1;", "  }", "}", "ctx.restore();"], 460)

mn_number_line.__signature__ = _kw_signature([("title", ""), ("from", -3), ("to", 5), ("point", 2), ("range", [0, 3]), ("range_label", ""), ("point_label", "x = 2"), ("seed", 0)])
def mn_triangle_anatomy(title="", angles=None, sides=None, height_line=True, formula="S = ½·a·h", seed=0):
    angles = [str(value) for value in (angles or ["A", "B", "C"])][:3]
    while len(angles) < 3:
        angles.append("")
    sides = [str(value) for value in (sides or ["a", "b", "c"])][:3]
    while len(sides) < 3:
        sides.append("")

    rng = random.Random("mn_tri:%d" % (int(seed) if seed else 12_345))
    apex_offset = round(rng.uniform(-170, 170))
    half_width = round(rng.uniform(265, 370))
    triangle_height = round(rng.uniform(425, 515))
    arc_radius = round(rng.uniform(33, 47))
    angle_label_radius = round(rng.uniform(74, 96))
    side_push = round(rng.uniform(36, 48))
    height_label_y = round(triangle_height * 0.525)

    body = (
        _TRIANGLE_BODY
        .replace("__ARC__", str(arc_radius))
        .replace("__ALR__", str(angle_label_radius))
        .replace("__SPU__", str(side_push))
        .replace("__TH__", str(triangle_height))
        .replace("__HY__", str(height_label_y))
    )
    return scene(
        _title_js(title)
        + [
            "var ANG=" + json.dumps(angles, ensure_ascii=False) + ";",
            "var SID=" + json.dumps(sides, ensure_ascii=False) + ";",
            "var HL=" + json.dumps(bool(height_line)) + ";",
            "var F=" + json.dumps(str(formula), ensure_ascii=False) + ";",
            "ctx.save();ctx.lineCap='round';ctx.lineJoin='round';",
            "ctx.textAlign='center';ctx.textBaseline='middle';",
            "/* idle: cả nhóm trôi nhẹ ±3px theo time */",
            "ctx.translate(0,3*Math.sin(time*0.8));",
            "var y0=cursorY+(TITLE?170:110);",
            "var cx=W/2, byv=y0+" + str(triangle_height) + ";",
            "var Ax=cx+(" + str(apex_offset) + ");",
            "var VA=[Ax,y0], VB=[cx-" + str(half_width) + ",byv], VC=[cx+" + str(half_width) + ",byv];",
            body,
        ],
        800,
    )

def mn_transform(title="", from_label="Hình vuông", to_label="Hình tròn", mode="square_circle", seed=0):
    _r = random.Random("mn_tf:%d" % 12_345); sz = 2 * round(_r.uniform(110, 150)); hs = sz // 2; cyo = round(_r.uniform(140, 200)); lmg = round(_r.uniform(200, 290)); rmg = round(_r.uniform(200, 290))
    
    ains = round(_r.uniform(28, 50))
    
    lly = round(_r.uniform(46, 70))
    return scene(_title_js(title) + ["var FL=" + json.dumps(str(from_label), ensure_ascii=False) + ";", "var TL=" + json.dumps(str(to_label), ensure_ascii=False) + ";", "ctx.save();ctx.lineCap='round';ctx.lineJoin='round';", "ctx.textAlign='center';ctx.textBaseline='middle';", "/* idle: cả nhóm trôi nhẹ ±3px theo time */", "ctx.translate(0,3*Math.sin(time*0.8));", "var y0=cursorY+(TITLE?170:110);", "var cy=y0+" + str(cyo) + ", S=" + str(sz) + ", hs=" + str(hs) + ";", "var lx=" + str(lmg) + ", rx=W-" + str(rmg) + ";", "/* morph lặp vô tận: bo góc đối pha hai bên */",
    
    "var pp=0.5+0.5*Math.sin(time*0.9);", "var rl=hs-pp*hs, rr=pp*hs;", "var per=4*S;", "var e0=EZ(CL(P*2.0)), e1=EZ(CL(P*2.0-0.45)), e2=EZ(CL(P*2.0-0.9));", "ctx.strokeStyle=" + json.dumps(INK) + ";ctx.lineWidth=3;", "/* hình gốc trái — viền tự vẽ dần bằng dash */", "if(e0>0){", "  ctx.setLineDash([per*e0,per]);",
    
    "  RR(lx-hs,cy-hs,S,S,rl);ctx.stroke();", "  ctx.setLineDash([]);", "}", "/* mũi tên giữa vẽ dần */", "if(e1>0){", "  var ax0=lx+hs+" + str(ains) + ", ax1=rx-hs-" + str(ains) + ";", "  var tip=ax0+(ax1-ax0)*e1;", "  ctx.beginPath();ctx.moveTo(ax0,cy);ctx.lineTo(tip-6,cy);ctx.stroke();", "  ctx.fillStyle=" + json.dumps(INK) + ";", "  ctx.beginPath();ctx.moveTo(tip+8,cy);", "  ctx.lineTo(tip-8,cy-8);ctx.lineTo(tip-8,cy+8);", "  ctx.closePath();ctx.fill();", "  /* idle: chấm trắng nhỏ chạy dọc mũi tên */", "  if(e1>=1){", "    var tu=(time*0.35)%1;", "    ctx.globalAlpha=0.8*Math.sin(Math.PI*tu);", "    ctx.fillStyle='#fff';", "    ctx.beginPath();ctx.arc(ax0+(ax1-16-ax0)*tu,cy,3.5,0,Math.PI*2);ctx.fill();", "    ctx.globalAlpha=1;", "  }", "}", "/* hình đích phải */", "if(e2>0){",
    
    "  ctx.setLineDash([per*e2,per]);", "  ctx.strokeStyle=" + json.dumps(INK) + ";", "  /* idle: viền hình đích thở nhẹ bằng shadowBlur */",
    
    "  ctx.shadowColor='rgba(255,255,255,0.28)';", "  ctx.shadowBlur=7+5*Math.sin(time*1.6);", "  RR(rx-hs,cy-hs,S,S,rr);ctx.stroke();", "  ctx.shadowBlur=0;", "  ctx.setLineDash([]);", "}", "/* nhãn dưới mỗi hình */", "ctx.font=" + _LBL + ";ctx.fillStyle=" + json.dumps(MUT) + ";", "ctx.globalAlpha=CL(P*2.0-0.6);ctx.fillText(FL,lx,cy+hs+" + str(lly) + ");", "/* nhãn đích reveal muộn ~giữa step theo P2 */", "ctx.globalAlpha=CL(P2*3-1.5);ctx.fillText(TL,rx,cy+hs+" + str(lly) + ");", "ctx.globalAlpha=1;", "ctx.restore();"], 620)

SCENES = {"mn_number_line": {"fn": mn_number_line, "doc": 'mn_number_line {"title":"","from":-3,"to":5,"point":2,"range":[0,3],"range_label":"0 ≤ x ≤ 3","point_label":"x = 2"} — trục số tự vẽ dần: tick mỗi đơn vị, đoạn [range] tô xanh dày + 2 chấm, điểm trắng nhảy nảy tới `point` kèm nhãn', "demo": {"title": "Nghiệm trên trục số", "from": -3, "to": 5, "point": 2, "range": [0, 3], "range_label": "0 ≤ x ≤ 3", "point_label": "x = 2"}}, "mn_triangle_anatomy": {"fn": mn_triangle_anatomy, "doc": 'mn_triangle_anatomy {"title":"","angles":["A","B","C"],"sides":["a","b","c"],"height_line":true,"formula":"S = ½·a·h"} — tam giác lớn vẽ dần từng cạnh nối tiếp, cung + nhãn 3 góc, nhãn 3 cạnh, đường cao nét đứt + vuông góc + h, công thức dưới (vế phải vàng)', "demo": {"title": "Giải phẫu tam giác", "angles": ["A", "B", "C"], "sides": ["a", "b", "c"], "height_line": True, "formula": "S = ½·a·h"}}, "mn_transform": {"fn": mn_transform, "doc": 'mn_transform {"title":"","from_label":"Hình vuông","to_label":"Hình tròn","mode":"square_circle"} — biến hình trái → phải: hai hình 260px bo góc nội suy đối pha theo time (vuông ↔ tròn chảy qua lại), mũi tên giữa vẽ dần, nhãn muted dưới mỗi hình', "demo": {"title": "Biến hình liên tục", "from_label": "Hình vuông", "to_label": "Hình tròn", "mode": "square_circle"}}}
