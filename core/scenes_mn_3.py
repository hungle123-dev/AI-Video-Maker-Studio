"""core/scenes_mn_3.py — Bộ scene mathnoir #3: mn_shape_grid, mn_formula,
mn_steps_math.

Phong cách manim/3Blue1Brown: nền đen tuyền (renderer lo), nét trắng mảnh lw3
TỰ VẼ DẦN, chữ ít và nhỏ gọn, accent vàng CHỈ 1 phần tử/cảnh. Xem mn_spec.md.
"""
import json, math, random
from core.custom_scenes import scene; INK = "#e8e8ea"; MUTED = "#9a9aa0"; ACCENT = "#facc15"; _HELP_JS = "function SS(t){return t*t*(3-2*t);}function PL(pts,e){if(e<=0)return;var m=pts.length-1;var f=Math.min(1,e)*m;var k=Math.floor(f);ctx.beginPath();ctx.moveTo(pts[0][0],pts[0][1]);for(var q=1;q<=k;q++)ctx.lineTo(pts[q][0],pts[q][1]);if(k<m){var tt=f-k,pa=pts[k],pb=pts[k+1];ctx.lineTo(pa[0]+(pb[0]-pa[0])*tt,pa[1]+(pb[1]-pa[1])*tt);}ctx.stroke();}function DOT(x,y,r){r=r||7;ctx.fillStyle='rgba(255,255,255,0.25)';ctx.beginPath();ctx.arc(x,y,r*2,0,Math.PI*2);ctx.fill();ctx.fillStyle='#fff';ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill();}"
def _title_js(title):
    return ["var TITLE=" + json.dumps(str(title or ""), ensure_ascii=False) + ";", "if(TITLE){ctx.save();ctx.globalAlpha=CL(P*2.5);", "ctx.font='600 34px Segoe UI, sans-serif';ctx.fillStyle='#8b8b92';", "ctx.textAlign='center';ctx.textBaseline='middle';", "ctx.fillText(TITLE,W/2,cursorY+40);ctx.restore();}"]

def mn_shape_grid(title="", items=None, cols=3, seed=0):
    _r = random.Random(12_345); _sc = round(_r.uniform(0.8, 1.04), 2); _rad = round(_r.uniform(76.0, 100.0), 1); _amp = round(_r.uniform(36.0, 52.0), 1); _curv = round(_r.uniform(85.0, 130.0), 1)
    
    _ang = round(_r.uniform(-1.15, -0.2), 2)
    
    _dgx = round(_r.uniform(-24.0, 24.0), 1)
    
    _arm = round(_rad * 42.0 / 90.0, 1); _ly = int(round(150 * _sc))
    if not items:
        items = [{"kind": "circle_plus", "label": ""},
            {"kind": "tangent", "label": ""},
            {"kind": "triangle", "label": "180°"},
            {"kind": "right_triangle", "label": "a² + b² = c²", "accent_last": True},
            {"kind": "radius", "label": ""},
            {"kind": "wave", "label": ""}]
    norm = []
    for it in items[:9]:
        norm.append({"kind": str(it.get("kind", "circle_plus")).replace("₍ₚₗᵤₛ₎", "_plus"), "label": str(it.get("label", "")), "al": bool(it.get("accent_last", False))})
    cols = max(1, min(3, int(cols)))
    
    rows = int(math.ceil(len(norm) / float(cols))); height = 200 + rows * 310
    return scene(_title_js(title) + [_HELP_JS,
    
    "var ITEMS=" + json.dumps(norm, ensure_ascii=False) + ";", "var COLS=" + str(cols) + ";", "var top=cursorY+(TITLE?120:40);", "var CWc=300, PITCH=310;", "var x0=W/2-COLS*CWc/2+(" + str(_dgx) + ");", "var GR=" + str(_rad) + ",GARM=" + str(_arm) + ",GAMP=" + str(_amp) + ",GCV=" + str(_curv) + ",GAN=" + str(_ang) + ";", "ctx.save();ctx.lineCap='round';ctx.lineJoin='round';", "/* idle: cả lưới trôi nhẹ ±3px theo time */", "ctx.translate(0,Math.sin(time*0.8)*3);", "ITEMS.forEach(function(it,i){",
    
    "  var raw=CL(P*1.5-i*0.12);if(raw<=0)return;", "  var e=EZ(raw);", "  var col=i%COLS, row=Math.floor(i/COLS);", "  var cx=x0+col*CWc+CWc/2, cy=top+row*PITCH+150;", "  ctx.save();ctx.translate(cx,cy-22);ctx.scale(" + str(_sc) + "," + str(_sc) + ");", "  ctx.globalAlpha=Math.min(1,raw*4);", "  ctx.strokeStyle='#e8e8ea';ctx.lineWidth=3;", "  var k=it.kind;", "  if(k==='circle_plus'){", "    var ec=CL(e/0.7), ep=SS(CL((e-0.7)/0.3));", "    if(ec>0){ctx.beginPath();ctx.arc(0,0,GR,-Math.PI/2,-Math.PI/2+Math.PI*2*ec);ctx.stroke();}", "    if(ep>0){ctx.beginPath();ctx.moveTo(-GARM*ep,0);ctx.lineTo(GARM*ep,0);", "      ctx.moveTo(0,-GARM*ep);ctx.lineTo(0,GARM*ep);ctx.stroke();}", "    /* idle: chấm trắng bò chậm quanh vòng tròn */", "    if(e>0.95){var oa=-Math.PI/2+time*0.5;", "      DOT(Math.cos(oa)*GR,Math.sin(oa)*GR,4);}", "  }else if(k==='tangent'){", "    /* parabol nhẹ + tiếp tuyến + 2 chấm */", "    var pc=[];for(var s=0;s<=24;s++){var xx=-90+180*s/24;pc.push([xx,xx*xx/GCV-58]);}", "    PL(pc,CL(e/0.55));", "    var txp=40, typ=txp*txp/GCV-58, sl=2*txp/GCV;", "    var et=SS(CL((e-0.55)/0.3));", "    if(et>0){var dl=84/Math.sqrt(1+sl*sl);", "      ctx.beginPath();ctx.moveTo(txp-dl*et,typ-sl*dl*et);", "      ctx.lineTo(txp+dl*et,typ+sl*dl*et);ctx.stroke();}", "    if(e>0.9){DOT(txp,typ,6);DOT(-52,(-52)*(-52)/GCV-58,6);}", "  }else if(k==='triangle'){", "    var V=[[0,-92],[82,48],[-82,48]];", "    PL([V[0],V[1],V[2],V[0]],CL(e/0.75));", "    var ea=CL((e-0.78)/0.22);", "    if(ea>0){ctx.strokeStyle='rgba(232,232,234,0.45)';ctx.lineWidth=2;", "      for(var vi=0;vi<3;vi++){", "        var v=V[vi], pp=V[(vi+2)%3], qq=V[(vi+1)%3];", "        var a1=Math.atan2(pp[1]-v[1],pp[0]-v[0]);", "        var a2=Math.atan2(qq[1]-v[1],qq[0]-v[0]);", "        var dd=a2-a1;",
    "        while(dd<-Math.PI)dd+=Math.PI*2;while(dd>Math.PI)dd-=Math.PI*2;", "        var av=SS(CL(ea*3-vi*0.7));if(av<=0)continue;", "        ctx.beginPath();ctx.arc(v[0],v[1],24,a1,a1+dd*av,dd<0);ctx.stroke();", "      }", "      ctx.strokeStyle='#e8e8ea';ctx.lineWidth=3;}", "  }else if(k==='right_triangle'){", "    var A=[-88,60], B=[88,60], C2=[88,-74];", "    PL([A,B,C2,A],CL(e/0.82));", "    var eq=SS(CL((e-0.84)/0.16));", "    if(eq>0){ctx.save();ctx.globalAlpha*=eq;", "      ctx.strokeStyle='rgba(232,232,234,0.45)';ctx.lineWidth=2;", "      ctx.beginPath();ctx.moveTo(B[0]-18,B[1]);ctx.lineTo(B[0]-18,B[1]-18);", "      ctx.lineTo(B[0],B[1]-18);ctx.stroke();ctx.restore();}", "  }else if(k==='radius'){", "    var ec2=CL(e/0.65), er=SS(CL((e-0.65)/0.25));", "    if(ec2>0){ctx.beginPath();ctx.arc(0,0,GR,-Math.PI/2,-Math.PI/2+Math.PI*2*ec2);ctx.stroke();}", "    var ra=GAN, rx2=Math.cos(ra)*GR, ry2=Math.sin(ra)*GR;", "    if(er>0){ctx.beginPath();ctx.moveTo(0,0);ctx.lineTo(rx2*er,ry2*er);ctx.stroke();}", "    if(e>0.92){DOT(0,0,5);DOT(rx2,ry2,6);}", "  }else if(k==='wave'){", "    ctx.strokeStyle='rgba(232,232,234,0.45)';ctx.lineWidth=2;", "    var ax=SS(CL(e*2));", "    ctx.beginPath();ctx.moveTo(-95,0);ctx.lineTo(-95+190*ax,0);ctx.stroke();", "    ctx.strokeStyle='#e8e8ea';ctx.lineWidth=3;", "    var wp=[];for(var s2=0;s2<=60;s2++){", "      wp.push([-95+190*s2/60,-Math.sin(s2/60*Math.PI*5)*GAMP]);}", "    PL(wp,CL((e-0.12)/0.88));", "    /* idle: chấm trắng trôi dọc đường sóng */", "    if(e>0.95){var wu=(time*0.1)%1;", "      DOT(-95+190*wu,-Math.sin(wu*Math.PI*5)*GAMP,4);}", "  }else if(k==='square'){", "    PL([[-72,-72],[72,-72],[72,72],[-72,72],[-72,-72]],e);", "  }else if(k==='arrow_graph'){", "    var ea2=SS(CL(e/0.4)), ecv=CL((e-0.4)/0.55);", "    var ox=-82, oy=72;", "    ctx.strokeStyle='rgba(232,232,234,0.45)';ctx.lineWidth=2;", "    ctx.beginPath();ctx.moveTo(ox,oy);ctx.lineTo(ox+168*ea2,oy);ctx.stroke();", "    ctx.beginPath();ctx.moveTo(ox,oy);ctx.lineTo(ox,oy-156*ea2);ctx.stroke();", "    if(ea2>=1){ctx.fillStyle='rgba(232,232,234,0.45)';", "      ctx.beginPath();ctx.moveTo(ox+180,oy);ctx.lineTo(ox+166,oy-6);ctx.lineTo(ox+166,oy+6);ctx.closePath();ctx.fill();", "      ctx.beginPath();ctx.moveTo(ox,oy-168);ctx.lineTo(ox-6,oy-154);ctx.lineTo(ox+6,oy-154);ctx.closePath();ctx.fill();}", "    ctx.strokeStyle='#e8e8ea';ctx.lineWidth=3;", "    var gp=[];for(var s3=0;s3<=30;s3++){var t3=s3/30;", "      gp.push([ox+16+146*t3,oy-14-128*t3*t3]);}", "    PL(gp,ecv);", "    if(ecv>=1){var lp=gp[30], pv=gp[28];", "      var aa=Math.atan2(lp[1]-pv[1],lp[0]-pv[0]);", "      ctx.fillStyle='#e8e8ea';ctx.beginPath();", "      ctx.moveTo(lp[0]+Math.cos(aa)*12,lp[1]+Math.sin(aa)*12);", "      ctx.lineTo(lp[0]+Math.cos(aa+2.5)*10,lp[1]+Math.sin(aa+2.5)*10);", "      ctx.lineTo(lp[0]+Math.cos(aa-2.5)*10,lp[1]+Math.sin(aa-2.5)*10);", "      ctx.closePath();ctx.fill();}", "  }",
    
    "  ctx.restore();", "  /* nhãn dưới hình — từ cuối có thể accent vàng */", "  var lb=it.label||'';", "  if(lb){var la=CL(raw*1.6-0.45);if(la>0){", "    ctx.save();ctx.globalAlpha=SS(la);", "    ctx.font='400 28px Segoe UI, sans-serif';ctx.textBaseline='middle';", "    var ly=cy-22+" + str(_ly) + ";", "    if(it.al){", "      var sp=lb.lastIndexOf(' ');", "      var pre=sp>=0?lb.slice(0,sp+1):'';", "      var lst=sp>=0?lb.slice(sp+1):lb;", "      var w1=ctx.measureText(pre).width, w2=ctx.measureText(lst).width;", "      ctx.textAlign='left';", "      ctx.fillStyle='#9a9aa0';ctx.fillText(pre,cx-(w1+w2)/2,ly);", "      /* lộ muộn: từ cuối chuyển muted→vàng giữa step (P2) + glow thở */", "      ctx.fillText(lst,cx-(w1+w2)/2+w1,ly);", "      var lr=SS(CL(P2*3-1.5));", "      if(lr>0){ctx.save();ctx.globalAlpha*=lr;", "        ctx.shadowColor='rgba(250,204,21,0.55)';",
    
    "        ctx.shadowBlur=8+5*Math.sin(time*1.6);", "        ctx.fillStyle='#facc15';", "        ctx.fillText(lst,cx-(w1+w2)/2+w1,ly);ctx.restore();}",
    
    "      /* lộ muộn ~65%: gạch đứt mờ dưới nhãn, dash trôi theo time */", "      var lr2=SS(CL(P2*4-2.6));", "      if(lr2>0){ctx.save();ctx.globalAlpha*=lr2;", "        ctx.strokeStyle='rgba(232,232,234,0.28)';ctx.lineWidth=2;", "        ctx.setLineDash([6,7]);ctx.lineDashOffset=-time*8;", "        ctx.beginPath();ctx.moveTo(cx-(w1+w2)/2,ly+24);", "        ctx.lineTo(cx+(w1+w2)/2,ly+24);ctx.stroke();", "        ctx.setLineDash([]);ctx.restore();}", "    }else{", "      ctx.textAlign='center';ctx.fillStyle='#9a9aa0';ctx.fillText(lb,cx,ly);", "    }", "    ctx.restore();}}", "});", "ctx.restore();"], height)

def mn_formula(title="", formula="a² + b² = c²", accent_part="c²", note="Định lý Pythagore", size=96, seed=0):
    _r = random.Random(12_345); _fy = int(round(_r.uniform(288, 340))); _uf = round(_r.uniform(0.62, 0.8), 2); _gap = int(round(_r.uniform(50, 74))); _uw = round(_r.uniform(0.88, 1.06), 2)
    
    _dx = round(_r.uniform(-16.0, 16.0), 1)
    
    size = max(40, min(140, int(size)))
    return scene(_title_js(title) + [_HELP_JS, "var F=" + json.dumps(str(formula), ensure_ascii=False) + ";", "var AP=" + json.dumps(str(accent_part), ensure_ascii=False) + ";", "var NOTE=" + json.dumps(str(note), ensure_ascii=False) + ";", "var SZ=" + str(size) + ";", "if(F){", "ctx.save();ctx.textBaseline='middle';ctx.textAlign='left';", "/* idle: cả khối trôi nhẹ ±3px theo time */", "ctx.translate(0,Math.sin(time*0.8)*3);", "var fy=cursorY+" + str(_fy) + ";", "ctx.font='bold '+SZ+'px Segoe UI, sans-serif';", "while(ctx.measureText(F).width>W-140&&SZ>44){SZ-=4;ctx.font='bold '+SZ+'px Segoe UI, sans-serif';}", "/* tách trước/nhấn/sau quanh accent_part */", "var ki=AP?F.indexOf(AP):-1;", "var pre=ki>=0?F.slice(0,ki):F;", "var acc=ki>=0?AP:'';", "var post=ki>=0?F.slice(ki+AP.length):'';", "var w1=ctx.measureText(pre).width, w2=ctx.measureText(acc).width;", "var w3=ctx.measureText(post).width, tw=w1+w2+w3;", "var x0=W/2-tw/2+(" + str(_dx) + ");", "/* hiện dần kiểu viết: clip theo bề ngang */", "var e=EZ(CL(P*1.2));", "ctx.save();ctx.beginPath();ctx.rect(x0-30,fy-SZ,(tw+60)*e,SZ*2);ctx.clip();", "ctx.fillStyle='#e8e8ea';ctx.fillText(pre,x0,fy);",
    
    "/* idle: glow thở trên phần accent */", "if(acc){ctx.save();ctx.shadowColor='rgba(250,204,21,0.45)';", "  ctx.shadowBlur=10+6*Math.sin(time*1.6);",
    
    "  ctx.fillStyle='#facc15';ctx.fillText(acc,x0+w1,fy);ctx.restore();}", "if(post){ctx.fillStyle='#e8e8ea';ctx.fillText(post,x0+w1+w2,fy);}", "ctx.restore();", "/* gạch chân mảnh vẽ dần */", "var ue=EZ(CL(P*1.2-0.18));", "if(ue>0){var uy=fy+SZ*" + str(_uf) + ";", "  var us=x0+tw*(1-(" + str(_uw) + "))/2;", "  ctx.strokeStyle='rgba(255,255,255,0.3)';ctx.lineWidth=2;ctx.lineCap='round';", "  ctx.beginPath();ctx.moveTo(us,uy);ctx.lineTo(us+tw*(" + str(_uw) + ")*ue,uy);ctx.stroke();}",
    
    "if(ue>=1){", "  /* lộ muộn ~65%: đoạn vàng nhạt trên gạch chân ngay dưới accent */", "  if(acc){var ae=SS(CL(P2*4-2.6));", "    if(ae>0){ctx.save();ctx.globalAlpha=ae;", "      ctx.strokeStyle='rgba(250,204,21,0.55)';ctx.lineWidth=3;ctx.lineCap='round';", "      ctx.beginPath();ctx.moveTo(x0+w1,uy);ctx.lineTo(x0+w1+w2*ae,uy);", "      ctx.stroke();ctx.restore();}}", "  /* idle: chấm trắng qua lại dọc gạch chân */", "  var du=0.5+0.5*Math.sin(time*0.5);", "  DOT(us+tw*(" + str(_uw) + ")*du,uy,4);", "}", "/* ghi chú muted — lộ muộn giữa step theo P2 */", "if(NOTE){var ne=CL(P2*3-1.5);", "  ctx.globalAlpha=SS(ne);", "  ctx.font='400 30px Segoe UI, sans-serif';ctx.fillStyle='#9a9aa0';", "  ctx.textAlign='center';", "  ctx.fillText(NOTE,W/2+(" + str(_dx) + "),fy+SZ*" + str(_uf) + "+" + str(_gap) + "+10*(1-EZ(ne)));", "  ctx.globalAlpha=1;}", "ctx.restore();", "}"], 560)

def mn_steps_math(title="", lines=None, box_last=True, seed=0):
    _r = random.Random(int(seed) if seed else 12_345); _pitch = int(round(_r.uniform(98, 122))); _dy0 = int(round(_r.uniform(-14, 14))); _dx = round(_r.uniform(-18.0, 18.0), 1); _pad = int(round(_r.uniform(46, 86)))
    
    _bh = int(round(_r.uniform(78, 104)))
    
    _rr = int(round(_r.uniform(5, 13)))
    lines = [str(x) for x in (lines or ["x² + 2x = 8", "x² + 2x − 8 = 0", "(x + 4)(x − 2) = 0", "x = −4 hoặc x = 2"])][:8]; n = max(1, len(lines))
    
    height = 80 + n * 110 + 70 + (80 if title else 0)
    return scene(_title_js(title) + [_HELP_JS, "var LINES=" + json.dumps(lines, ensure_ascii=False) + ";", "var BOX=" + ("true" if box_last else "false") + ";", "var n=LINES.length;", "var y0=cursorY+(TITLE?" + str(170 + _dy0) + ":" + str(90 + _dy0) + ");", "ctx.save();ctx.textAlign='center';ctx.textBaseline='middle';", "/* idle: cả khối dòng trôi nhẹ ±3px theo time */", "ctx.translate(0,Math.sin(time*0.8)*3);", "function lineFont(s){var lf=52;", "  ctx.font='bold '+lf+'px Segoe UI, sans-serif';", "  while(ctx.measureText(s).width>W-160&&lf>32){lf-=2;ctx.font='bold '+lf+'px Segoe UI, sans-serif';}", "  return lf;}", "LINES.forEach(function(ln,i){", "  var r=CL(P*2-i*0.22);if(r<=0)return;", "  var e=EZ(r);", "  /* dòng trước mờ dần còn 0.45 khi dòng sau hiện; dòng cuối luôn rõ */", "  var nxt=(i>=n-1)?0:CL((P*2-(i+1)*0.22)*2.5);",
    
    "  var al=(1-0.55*SS(nxt))*Math.min(1,r*2.2);", "  ctx.globalAlpha=al;",
    
    "  lineFont(ln);", "  ctx.fillStyle='#e8e8ea';", "  var ly2=y0+i*" + str(_pitch) + "+18*(1-e);", "  if(i===n-1){", "    /* idle: dòng cuối đập nhịp mềm 1% theo time */", "    var pu=1+0.01*Math.sin(time*2);", "    ctx.save();ctx.translate(W/2+(" + str(_dx) + "),ly2);", "    ctx.scale(pu,pu);ctx.fillText(ln,0,0);ctx.restore();", "  }else{ctx.fillText(ln,W/2+(" + str(_dx) + "),ly2);}", "});",
    
    "ctx.globalAlpha=1;", "/* khung vàng mảnh quanh dòng cuối — LỘ MUỘN giữa step theo P2 */", "if(BOX&&n>0){", "  var eb=CL((P2*3-1.5)/0.5);", "  if(eb>0){", "    lineFont(LINES[n-1]);", "    var bw=ctx.measureText(LINES[n-1]).width+" + str(_pad) + ", bh=" + str(_bh) + ";", "    var bx=W/2+(" + str(_dx) + ")-bw/2, by=y0+(n-1)*" + str(_pitch) + "-bh/2;", "    var per=2*(bw+bh);", "    /* idle: glow thở trên khung vàng */", "    ctx.save();ctx.shadowColor='rgba(250,204,21,0.45)';", "    ctx.shadowBlur=7+5*Math.sin(time*1.6);", "    ctx.strokeStyle='rgba(250,204,21,0.9)';ctx.lineWidth=2;ctx.lineCap='round';", "    ctx.setLineDash([Math.max(0.01,per*EZ(eb)),per]);ctx.lineDashOffset=0;", "    RR(bx,by,bw,bh," + str(_rr) + ");ctx.stroke();", "    ctx.setLineDash([]);ctx.restore();", "    /* idle: chấm trắng bò quanh chu vi khung */",
    
    "    if(eb>=1){var dd2=(time*70)%per, px2, py2;", "      if(dd2<bw){px2=bx+dd2;py2=by;}", "      else if(dd2<bw+bh){px2=bx+bw;py2=by+(dd2-bw);}", "      else if(dd2<2*bw+bh){px2=bx+bw-(dd2-bw-bh);py2=by+bh;}",
    
    "      else{px2=bx;py2=by+bh-(dd2-2*bw-bh);}", "      DOT(px2,py2,3.5);}", "  }", "}", "ctx.restore();"], height)
    
SCENES = {"mn_shape_grid": {"fn": mn_shape_grid, "doc": 'mn_shape_grid {"title":"","items":[{"kind":"right_triangle","label":"a² + b² = c²","accent_last":true}],"cols":3} — lưới hình học nét trắng tự vẽ dần stagger; kind: circle_plus|tangent|triangle|right_triangle|radius|wave|square|arrow_graph; accent_last tô vàng từ cuối của label (1 phần tử/cảnh)', "demo": {"title": "Hình học quanh ta", "cols": 3, "items": [{"kind": "circle_plus", "label": ""},
    {"kind": "tangent", "label": ""},
    {"kind": "triangle", "label": "180°"},
    {"kind": "right_triangle", "label": "a² + b² = c²", "accent_last": True},
    {"kind": "radius", "label": ""},
    {"kind": "wave", "label": ""}]}}, "mn_formula": {"fn": mn_formula, "doc": 'mn_formula {"title":"","formula":"a² + b² = c²","accent_part":"c²","note":"Định lý Pythagore","size":96} — công thức lớn hiện dần kiểu viết (clip ngang), phần accent_part tô vàng, gạch chân mảnh vẽ dần + ghi chú muted; công thức dùng unicode (x², √, ½, π, θ)', "demo": {"title": "", "formula": "a² + b² = c²", "accent_part": "c²", "note": "Định lý Pythagore", "size": 96}}, "mn_steps_math": {"fn": mn_steps_math, "doc": 'mn_steps_math {"title":"","lines":["x² + 2x = 8","x = 2"],"box_last":true} — biến đổi từng dòng hiện lần lượt (fade + trượt nhẹ, dòng cũ mờ còn 0.45), dòng cuối có khung vàng mảnh vẽ nét dần quanh', "demo": {"title": "Giải phương trình", "lines": ["x² + 2x = 8", "x² + 2x − 8 = 0", "(x + 4)(x − 2) = 0", "x = −4 hoặc x = 2"], "box_last": True}}}
