"""core/custom_scenes.py — Bộ cảnh động canvas cao cấp của TubeCraft.

Registered as first-class custom_js templates: use in lesson scripts as
    {"type": "custom_js", "template": "<name>", "params": {...}}
and script_generator._expand_custom_js_templates() will expand them here.

JS runtime env: ctx, W, H, MX, cursorY, stepProgress (0-1), time (seconds),
rc(colorName), wrapText(text,maxW,font), drawEmoji. Emojis in fillText are
auto-rendered as color Twemoji. Never use backticks in code strings.

USAGE GUIDANCE (semantic picks — avoid over-using any one scene):
  journey_path = long roadmap · stairs_steps = ascending order ·
  domino_flow = cause-effect chain · orbit_cycle = repeating loop ·
  code_typing = any code/terminal · web_window = browser result ·
  metric_grid = numbers count-up · big_word = typographic hook ·
  progress_map = evolving series outro · stamp_done/badge-like = single win.
"""
import json
import math
import re


PRE = "var P=Math.max(0,Math.min(1,stepProgress*4));var P2=Math.max(0,Math.min(1,stepProgress));function RR(x,y,w,h,r){ctx.beginPath();ctx.roundRect(x,y,w,h,r);}function CL(v){return Math.max(0,Math.min(1,v));}function EZ(t){return 1-Math.pow(1-t,3);}function EB(t){var c1=1.70158,c3=c1+1;return 1+c3*Math.pow(t-1,3)+c1*Math.pow(t-1,2);}"
NEON_SPRITES = (
    "think", "idea", "run", "fall", "climb", "lift", "laptop", "point",
    "celebrate", "flag",
)


def _safe_text(value) -> str:
    """Keep scene parameters as data, never JavaScript syntax.

    A few legacy scene factories interpolate labels into single-quoted JS
    strings.  Normalising quotation marks and backslashes here keeps the
    declarative template boundary safe without making authors lose their text.
    """
    text = str(value or "")[:500]
    return (text.replace("\\", "／").replace("`", "´")
                .replace("'", "’").replace('"', "”")
                .replace("\r", " ").replace("\n", " ")
                .replace("\t", " ").replace("\x00", ""))


def sanitize_params(params):
    """Return bounded JSON-like data safe to interpolate in local scenes."""
    def clean(value, depth=0):
        if depth > 5:
            return ""
        if value is None or isinstance(value, bool):
            return value
        if isinstance(value, int):
            return max(-1_000_000_000, min(1_000_000_000, value))
        if isinstance(value, float):
            return max(-1_000_000_000, min(1_000_000_000, value)) if math.isfinite(value) else 0
        if isinstance(value, str):
            return _safe_text(value)
        if isinstance(value, (list, tuple)):
            return [clean(item, depth + 1) for item in value[:32]]
        if isinstance(value, dict):
            return {
                _safe_text(key)[:64]: clean(item, depth + 1)
                for key, item in list(value.items())[:32]
            }
        return _safe_text(value)

    return clean(params) if isinstance(params, dict) else {}
def scene(code_lines, height):
    return {"type": "custom_js", "code": PRE + "\n" + "\n".join(code_lines), "height": height}


def neon_sprite_panel(sprite="idea", kicker="", title="", rows=None):
    """Trusted Neon Doodle scene using a bundled character sprite.

    The model supplies only short data.  The local factory owns the drawing
    code, including ``ui.sprite``, so the template remains expressive without
    allowing model-authored JavaScript through the renderer boundary.
    """
    sprite = str(sprite or "idea").strip().lower()
    if sprite not in NEON_SPRITES:
        sprite = "idea"
    kicker = _safe_text(kicker or "NEON DOODLE")[:22]
    values = rows if isinstance(rows, (list, tuple)) else []
    labels = [_safe_text(value.get("text") or value.get("label") or "")[:32]
              if isinstance(value, dict) else _safe_text(value)[:32]
              for value in values if str(value or "").strip()][:3]
    if not labels:
        labels = ["QUAN SÁT", "HÀNH ĐỘNG", "KẾT QUẢ"]
    return scene([
        "var NS=" + json.dumps(sprite, ensure_ascii=False) + ";",
        "var NK=" + json.dumps(kicker, ensure_ascii=False) + ";",
        "var NR=" + json.dumps(labels, ensure_ascii=False) + ";",
        "var cx=W/2,y=cursorY+8,p=EZ(CL(P*1.9));",
        "ctx.save();ctx.globalAlpha=Math.min(1,P*2.2);",
        "ui.sprite(NS,cx,y+280,460,{seed:NR.length});",
        "var px=110,pw=W-220,py=y+560;ui.glass(px,py,pw,320,{accent:'green'});",
        "ctx.fillStyle='#a3e635';ctx.font='700 22px Consolas,monospace';ctx.textAlign='left';ctx.textBaseline='middle';ctx.fillText(NK.toUpperCase(),px+44,py+28);",
        "NR.forEach(function(label,i){var rp=EZ(CL(P*2-i*0.25));if(rp<=0)return;var ry=py+66+i*94;ctx.save();ctx.globalAlpha=rp;ctx.fillStyle='#dbe5d0';ctx.font='700 28px Consolas,monospace';ctx.textAlign='left';ctx.textBaseline='middle';ctx.fillText(label,px+44,ry-14);ctx.fillStyle='rgba(255,255,255,0.10)';RR(px+44,ry,pw-220,14,7);ctx.fill();ui.bar(px+44,ry,pw-220,14,Math.min(1,0.42+i*0.22)*rp,{color:i===1?'cyan':'green'});ctx.fillStyle='#93a58a';ctx.textAlign='right';ctx.fillText('SET',px+pw-40,ry+12);ctx.restore();});",
        "ctx.restore();",
    ], 880)

def episode_ring(n, total=13):
    return scene(["var cx=W/2, cy=cursorY+195, R=150;", "ctx.save();", "// outer rotating dashed ring", "ctx.strokeStyle='rgba(34,211,238,0.5)';ctx.lineWidth=2.5;", "ctx.setLineDash([14,10]);ctx.lineDashOffset=-time*40;", "ctx.beginPath();ctx.arc(cx,cy,R+26,0,Math.PI*2);ctx.stroke();ctx.setLineDash([]);", "// glow disc", "var g=ctx.createRadialGradient(cx,cy,20,cx,cy,R+10);", "g.addColorStop(0,'rgba(255,215,0,0.16)');g.addColorStop(1,'rgba(255,215,0,0)');", "ctx.fillStyle=g;ctx.beginPath();ctx.arc(cx,cy,R+10,0,Math.PI*2);ctx.fill();", "// main circle", "ctx.strokeStyle=rc('title');ctx.lineWidth=5;", "ctx.shadowColor=rc('title');ctx.shadowBlur=18;", "ctx.beginPath();ctx.arc(cx,cy,R,0,Math.PI*2);ctx.stroke();ctx.shadowBlur=0;", "// progress arc (episode position in serial)", "ctx.strokeStyle=rc('cyan');ctx.lineWidth=7;ctx.lineCap='round';", "ctx.beginPath();ctx.arc(cx,cy,R,-Math.PI/2,-Math.PI/2+Math.PI*2*(" + str(n) + "/" + str(total) + ")*EZ(P));ctx.stroke();", "// orbiting satellite dot", "var oa=-Math.PI/2+time*1.1;", "ctx.fillStyle='#fff';ctx.shadowColor=rc('cyan');ctx.shadowBlur=14;", "ctx.beginPath();ctx.arc(cx+Math.cos(oa)*(R+26),cy+Math.sin(oa)*(R+26),7,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;", "// texts", "ctx.textAlign='center';ctx.textBaseline='middle';", "ctx.fillStyle=rc('muted');ctx.font='bold 30px sans-serif';ctx.fillText('B À I',cx,cy-84);", "var ns=Math.round(" + str(n) + "*CL(P*1.6));", "ctx.fillStyle=rc('title');ctx.font='bold 150px sans-serif';ctx.fillText(String(ns),cx,cy+6);", "ctx.fillStyle=rc('cyan');ctx.font='bold 30px sans-serif';ctx.fillText('/ " + str(total) + "',cx,cy+96);", "ctx.restore();"], 400)

def phone_hero(orbit_icons=("🛒", "📦", "🧠", "🔐")):
    icons = json.dumps(list(orbit_icons), ensure_ascii=False)
    return scene(["var cx=W/2, top=cursorY+30, pw=330, ph=560;", "ctx.save();", "// orbiting feature icons (behind phone)", "var EMS=" + icons + ";", "EMS.forEach(function(e,i){", "  var a=time*0.55+i*(Math.PI*2/EMS.length);", "  var ex=cx+Math.cos(a)*300, ey=top+ph/2+Math.sin(a)*230;", "  ctx.globalAlpha=0.55+0.45*Math.sin(a);", "  ctx.font='46px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';", "  ctx.fillText(e,ex,ey);", "});ctx.globalAlpha=1;", "// phone body", "ctx.shadowColor=rc('cyan');ctx.shadowBlur=34;", "ctx.fillStyle='#0c1322';RR(cx-pw/2,top,pw,ph,46);ctx.fill();ctx.shadowBlur=0;", "ctx.strokeStyle='rgba(34,211,238,0.75)';ctx.lineWidth=3;RR(cx-pw/2,top,pw,ph,46);ctx.stroke();", "// screen + notch", "ctx.fillStyle='#0a0f1d';RR(cx-pw/2+13,top+13,pw-26,ph-26,34);ctx.fill();", "ctx.fillStyle='#040711';RR(cx-56,top+22,112,22,11);ctx.fill();", "// header bar", "var p1=CL(P*3);", "ctx.globalAlpha=p1;ctx.fillStyle='rgba(34,211,238,0.16)';RR(cx-pw/2+26,top+62,pw-52,54,14);ctx.fill();", "ctx.fillStyle='rgba(34,211,238,0.8)';RR(cx-pw/2+40,top+80,110,18,9);ctx.fill();ctx.globalAlpha=1;", "// search pill", "var p2=CL(P*3-0.6);", "ctx.globalAlpha=p2;ctx.strokeStyle='rgba(255,255,255,0.25)';ctx.lineWidth=2;", "RR(cx-pw/2+26,top+134,pw-52,44,22);ctx.stroke();", "ctx.fillStyle='rgba(255,255,255,0.28)';RR(cx-pw/2+44,top+150,90,12,6);ctx.fill();ctx.globalAlpha=1;", "// product cards sliding in", "for(var i=0;i<3;i++){", "  var pc=CL(P*3.2-0.9-i*0.45);if(pc<=0)continue;", "  var slide=(1-EB(pc))*70;", "  var yy=top+198+i*112;", "  ctx.globalAlpha=pc;", "  ctx.fillStyle='rgba(255,255,255,0.055)';RR(cx-pw/2+26+slide,yy,pw-52,96,16);ctx.fill();", "  ctx.strokeStyle='rgba(255,255,255,0.12)';ctx.lineWidth=1.5;RR(cx-pw/2+26+slide,yy,pw-52,96,16);ctx.stroke();", "  ctx.fillStyle=['rgba(34,211,238,0.85)','rgba(34,197,94,0.85)','rgba(255,215,0,0.85)'][i];", "  ctx.beginPath();ctx.arc(cx-pw/2+62+slide,yy+48,20,0,Math.PI*2);ctx.fill();", "  ctx.fillStyle='rgba(255,255,255,0.75)';RR(cx-pw/2+96+slide,yy+26,130,14,7);ctx.fill();", "  ctx.fillStyle='rgba(255,255,255,0.3)';RR(cx-pw/2+96+slide,yy+52,170,11,5);ctx.fill();", "  ctx.globalAlpha=1;", "}", "// bottom nav", "var p3=CL(P*3-1.6);ctx.globalAlpha=p3;", "ctx.fillStyle='rgba(255,255,255,0.07)';RR(cx-pw/2+26,top+ph-72,pw-52,44,22);ctx.fill();", "for(var j=0;j<4;j++){ctx.fillStyle=j===0?rc('cyan'):'rgba(255,255,255,0.3)';", "ctx.beginPath();ctx.arc(cx-pw/2+70+j*((pw-90)/3.4),top+ph-50,8,0,Math.PI*2);ctx.fill();}", "ctx.globalAlpha=1;ctx.restore();"], 640)

def code_typing(title, lines):
    payload = json.dumps(
        [[[t, c] for t, c in ln] for ln in lines], ensure_ascii=False
    )
    h = 118 + len(lines) * 42 + 20
    return scene(["var LINES=" + payload + ";", "var COLS={kw:'#c792ea',str:'#9ece6a',fn:'#7aa2f7',txt:'#e6edf3',cm:'#565f89',num:'#ff9e64',err:'#f7768e',ok:'#4ade80'};", "var w=Math.min(W-MX*2,880), x=W/2-w/2, y=cursorY+8;", "var lh=42, bh=64+LINES.length*lh+24;", "ctx.save();", "// window", "ctx.shadowColor='rgba(0,0,0,0.6)';ctx.shadowBlur=26;ctx.shadowOffsetY=8;", "ctx.fillStyle='#0d1424';RR(x,y,w,bh,18);ctx.fill();ctx.shadowBlur=0;ctx.shadowOffsetY=0;", "ctx.strokeStyle='rgba(122,162,247,0.35)';ctx.lineWidth=1.5;RR(x,y,w,bh,18);ctx.stroke();", "// title bar", "ctx.fillStyle='rgba(255,255,255,0.04)';RR(x,y,w,52,18);ctx.fill();", "['#ff5f57','#febc2e','#28c840'].forEach(function(c,i){ctx.fillStyle=c;ctx.beginPath();ctx.arc(x+30+i*30,y+26,7.5,0,Math.PI*2);ctx.fill();});", "ctx.fillStyle='rgba(230,237,243,0.75)';ctx.font='bold 22px Consolas';ctx.textAlign='center';ctx.textBaseline='middle';", "ctx.fillText('" + title.replace("'", "\\'") + "',x+w/2,y+27);", "// typing reveal", "var total=0;LINES.forEach(function(l){l.forEach(function(s){total+=s[0].length;});});", "var typed=Math.floor(total*CL(P*1.12)), used=0;", "ctx.textAlign='left';", "for(var li=0;li<LINES.length;li++){", "  var ly=y+52+28+li*lh;", "  ctx.fillStyle='rgba(120,135,170,0.45)';ctx.font='22px Consolas';", "  ctx.fillText(String(li+1).padStart(2,' '),x+22,ly);", "  var tx=x+78;", "  for(var si=0;si<LINES[li].length;si++){", "    var seg=LINES[li][si],text=seg[0];", "    if(used>=typed)break;", "    var show=text.slice(0,Math.max(0,typed-used));used+=text.length;", "    ctx.fillStyle=COLS[seg[1]]||COLS.txt;ctx.font='26px Consolas';", "    ctx.fillText(show,tx,ly);tx+=ctx.measureText(show).width;", "  }", "  if(used>=typed){",
    
    "    if(Math.floor(time*2.4)%2===0){ctx.fillStyle=rc('cyan');ctx.fillRect(tx+3,ly-14,13,30);}", "    break;", "  }", "}",
    
    "ctx.restore();"], h)
    
def edge_globe(center_emoji="⚡", label="300+ thành phố · gần người dùng nhất"):
    return scene(["var gx=W/2, gy=cursorY+240, R=195;", "ctx.save();", "// globe sphere", "var g=ctx.createRadialGradient(gx-60,gy-70,20,gx,gy,R);", "g.addColorStop(0,'rgba(34,211,238,0.18)');g.addColorStop(1,'rgba(34,211,238,0.02)');", "ctx.fillStyle=g;ctx.beginPath();ctx.arc(gx,gy,R,0,Math.PI*2);ctx.fill();", "ctx.strokeStyle='rgba(34,211,238,0.55)';ctx.lineWidth=2.5;", "ctx.beginPath();ctx.arc(gx,gy,R,0,Math.PI*2);ctx.stroke();", "// meridians / latitudes", "ctx.strokeStyle='rgba(34,211,238,0.22)';ctx.lineWidth=1.5;", "[0.34,0.68].forEach(function(k){ctx.beginPath();ctx.ellipse(gx,gy,R*k,R,0,0,Math.PI*2);ctx.stroke();});", "[ -0.45,0,0.45].forEach(function(k){var ry=R*Math.sqrt(1-k*k);", "ctx.beginPath();ctx.ellipse(gx,gy+R*k*0.0,ry,ry*0.32,0,0,Math.PI*2);ctx.globalAlpha=0.5;ctx.stroke();ctx.globalAlpha=1;});", "// cities + radiating pulses + packets", "var CTS=[[-0.62,-0.28],[0.55,-0.42],[0.7,0.3],[-0.38,0.52],[0.06,-0.72],[-0.05,0.7]];", "CTS.forEach(function(c,i){", "  var px=gx+c[0]*R, py=gy+c[1]*R;", "  var pr=(time*0.55+i*0.19)%1;", "  ctx.strokeStyle='rgba(34,197,94,'+(0.75*(1-pr))+')';ctx.lineWidth=2.5;", "  ctx.beginPath();ctx.arc(px,py,6+pr*44,0,Math.PI*2);ctx.stroke();", "  ctx.fillStyle=rc('green');ctx.shadowColor=rc('green');ctx.shadowBlur=10;", "  ctx.beginPath();ctx.arc(px,py,6,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;", "  // packet center->city", "  var t=(time*0.5+i*0.35)%1;", "  ctx.fillStyle='rgba(255,255,255,0.95)';", "  ctx.beginPath();ctx.arc(gx+(px-gx)*t,gy+(py-gy)*t,4.5,0,Math.PI*2);ctx.fill();", "});", "// core", "ctx.fillStyle='rgba(10,16,30,0.9)';ctx.beginPath();ctx.arc(gx,gy,52,0,Math.PI*2);ctx.fill();", "ctx.strokeStyle=rc('title');ctx.lineWidth=3;ctx.shadowColor=rc('title');ctx.shadowBlur=16;", "ctx.beginPath();ctx.arc(gx,gy,52,0,Math.PI*2);ctx.stroke();ctx.shadowBlur=0;", "ctx.font='56px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';", "ctx.fillText('" + center_emoji + "',gx,gy+2);", "// caption chip", "ctx.font='bold 27px sans-serif';", "var lw=ctx.measureText('" + label.replace("'", "\\'") + "').width+56;", "ctx.fillStyle='rgba(34,211,238,0.1)';RR(gx-lw/2,gy+R+34,lw,52,26);ctx.fill();", "ctx.strokeStyle='rgba(34,211,238,0.5)';ctx.lineWidth=1.5;RR(gx-lw/2,gy+R+34,lw,52,26);ctx.stroke();", "ctx.fillStyle=rc('cyan');ctx.fillText('" + label.replace("'", "\\'") + "',gx,gy+R+61);", "ctx.restore();"], 560)

def data_river(left_emoji="📱", left_label="APP", mid_emoji="☁️", mid_label="WORKER", right_kind="db", right_label="D1", right_emoji="📦"):
    if right_kind == "db":
        right_js = "ctx.strokeStyle=rc('cyan');ctx.lineWidth=3;ctx.fillStyle='rgba(34,211,238,0.08)';ctx.beginPath();ctx.ellipse(ax2,cy-52,54,18,0,0,Math.PI*2);ctx.fill();ctx.stroke();ctx.fillRect?0:0;ctx.beginPath();ctx.moveTo(ax2-54,cy-52);ctx.lineTo(ax2-54,cy+44);ctx.ellipse(ax2,cy+44,54,18,0,Math.PI,0,true);ctx.lineTo(ax2+54,cy-52);ctx.stroke();ctx.fillStyle='rgba(34,211,238,0.08)';ctx.beginPath();ctx.moveTo(ax2-54,cy-52);ctx.lineTo(ax2-54,cy+44);ctx.ellipse(ax2,cy+44,54,18,0,Math.PI,0,true);ctx.lineTo(ax2+54,cy-52);ctx.ellipse(ax2,cy-52,54,18,0,0,Math.PI);ctx.fill();[ -20,4,28].forEach(function(dy,ri){var ra=CL(P*3-ri*0.5);ctx.globalAlpha=ra;ctx.strokeStyle='rgba(34,211,238,0.5)';ctx.lineWidth=2;ctx.beginPath();ctx.ellipse(ax2,cy+dy,54,18,0,Math.PI*0.08,Math.PI*0.92);ctx.stroke();ctx.globalAlpha=1;});"
    else:
        right_js = "ctx.strokeStyle=rc('orange');ctx.lineWidth=3;ctx.fillStyle='rgba(255,158,100,0.08)';RR(ax2-56,cy-56,112,112,16);ctx.fill();ctx.stroke();ctx.font='52px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText('" + right_emoji + "',ax2,cy);"
    return scene(["var cy=cursorY+150;", "var ax0=MX+120, ax1=W/2, ax2=W-MX-120;", "ctx.save();", "// wire", "ctx.strokeStyle='rgba(255,255,255,0.1)';ctx.lineWidth=5;", "ctx.beginPath();ctx.moveTo(ax0+70,cy);ctx.lineTo(ax2-70,cy);ctx.stroke();", "// packets ->", "for(var i=0;i<4;i++){var t=(time*0.42+i/4)%1;", "  var px=ax0+70+(ax2-ax0-140)*t;", "  ctx.fillStyle=rc('cyan');ctx.shadowColor=rc('cyan');ctx.shadowBlur=10;", "  ctx.beginPath();ctx.arc(px,cy-9,5.5,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;}", "// packets <-", "for(var i2=0;i2<4;i2++){var t2=(time*0.42+i2/4+0.5)%1;", "  var px2=ax2-70-(ax2-ax0-140)*t2;", "  ctx.fillStyle=rc('green');ctx.shadowColor=rc('green');ctx.shadowBlur=10;", "  ctx.beginPath();ctx.arc(px2,cy+11,5.5,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;}", "// left: phone", "ctx.fillStyle='#0c1322';ctx.strokeStyle='rgba(34,211,238,0.7)';ctx.lineWidth=2.5;", "RR(ax0-42,cy-72,84,144,18);ctx.fill();ctx.stroke();", "ctx.fillStyle='rgba(34,211,238,0.15)';RR(ax0-30,cy-58,60,20,6);ctx.fill();", "ctx.fillStyle='rgba(255,255,255,0.14)';RR(ax0-30,cy-28,60,12,5);ctx.fill();RR(ax0-30,cy-8,60,12,5);ctx.fill();", "ctx.font='34px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';", "ctx.fillText('" + left_emoji + "',ax0,cy+42);", "// mid: worker core", "var pulse=1+0.06*Math.sin(time*4);", "ctx.fillStyle='rgba(10,16,30,0.95)';ctx.beginPath();ctx.arc(ax1,cy,56*pulse,0,Math.PI*2);ctx.fill();", "ctx.strokeStyle=rc('title');ctx.lineWidth=3;ctx.shadowColor=rc('title');ctx.shadowBlur=18;", "ctx.beginPath();ctx.arc(ax1,cy,56*pulse,0,Math.PI*2);ctx.stroke();ctx.shadowBlur=0;", "ctx.font='54px sans-serif';ctx.fillText('" + mid_emoji + "',ax1,cy+2);", "// right node", right_js, "// labels", "ctx.font='bold 26px sans-serif';ctx.fillStyle=rc('muted');ctx.textBaseline='alphabetic';", "ctx.fillText('" + left_label + "',ax0,cy+128);", "ctx.fillText('" + mid_label + "',ax1,cy+128);", "ctx.fillText('" + right_label + "',ax2,cy+128);", "ctx.restore();"], 330)

def shield_wall(icon="🛡️", left_label="BOT: CHẶN", right_label="NGƯỜI THẬT: QUA"):
    return scene(["var cx=W/2, cy=cursorY+215;", "ctx.save();", "// shield shape", "function shieldPath(s){ctx.beginPath();ctx.moveTo(cx,cy-s);", "ctx.quadraticCurveTo(cx+s*0.95,cy-s*0.75,cx+s*0.82,cy+s*0.15);", "ctx.quadraticCurveTo(cx+s*0.6,cy+s*0.85,cx,cy+s*1.05);", "ctx.quadraticCurveTo(cx-s*0.6,cy+s*0.85,cx-s*0.82,cy+s*0.15);", "ctx.quadraticCurveTo(cx-s*0.95,cy-s*0.75,cx,cy-s);ctx.closePath();}", "var glow=14+7*Math.sin(time*3);", "var sg=ctx.createLinearGradient(cx,cy-150,cx,cy+160);", "sg.addColorStop(0,'rgba(34,211,238,0.22)');sg.addColorStop(1,'rgba(34,211,238,0.05)');", "ctx.fillStyle=sg;shieldPath(150);ctx.fill();", "ctx.strokeStyle=rc('cyan');ctx.lineWidth=5;ctx.shadowColor=rc('cyan');ctx.shadowBlur=glow;", "shieldPath(150);ctx.stroke();ctx.shadowBlur=0;", "ctx.strokeStyle='rgba(34,211,238,0.35)';ctx.lineWidth=2;shieldPath(118);ctx.stroke();", "ctx.font='72px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';", "ctx.fillText('" + icon + "',cx,cy+4);", "// bots slamming from the left", "for(var i=0;i<4;i++){", "  var t=(time*0.55+i*0.26)%1;", "  var sx=MX+30, sy=cy-140+i*88;", "  var hx=cx-158, hy=cy-60+i*44;", "  if(t<0.8){var bx=sx+(hx-sx)*(t/0.8), by=sy+(hy-sy)*(t/0.8);", "    ctx.fillStyle=rc('red');ctx.shadowColor=rc('red');ctx.shadowBlur=8;", "    ctx.beginPath();ctx.arc(bx,by,8,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;", "    ctx.strokeStyle='rgba(239,68,68,0.5)';ctx.lineWidth=2;", "    ctx.beginPath();ctx.moveTo(bx-16,by);ctx.lineTo(bx-34,by);ctx.stroke();", "  }else{var bp=(t-0.8)/0.2;", "    ctx.strokeStyle='rgba(239,68,68,'+(1-bp)+')';ctx.lineWidth=3;", "    for(var k=0;k<5;k++){var a=k*(Math.PI*2/5)+bp*2;", "      ctx.beginPath();ctx.moveTo(hx+Math.cos(a)*6,hy+Math.sin(a)*6);", "      ctx.lineTo(hx+Math.cos(a)*(10+bp*22),hy+Math.sin(a)*(10+bp*22));ctx.stroke();}", "  }", "}", "// humans passing on the right side", "for(var j=0;j<3;j++){", "  var ht=(time*0.4+j*0.33)%1;", "  var px=cx+150+(W-MX-30-(cx+150))*ht, py=cy-40+j*52;", "  ctx.globalAlpha=ht<0.1?ht*10:(ht>0.9?(1-ht)*10:1);", "  ctx.fillStyle=rc('green');ctx.shadowColor=rc('green');ctx.shadowBlur=8;", "  ctx.beginPath();ctx.arc(px,py,8,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;", "  ctx.strokeStyle='rgba(34,197,94,0.5)';ctx.lineWidth=2;", "  ctx.beginPath();ctx.moveTo(px-16,py);ctx.lineTo(px-32,py);ctx.stroke();ctx.globalAlpha=1;", "}", "// labels", "ctx.font='bold 25px sans-serif';ctx.textBaseline='alphabetic';", "ctx.fillStyle=rc('red');ctx.textAlign='left';ctx.fillText('" + left_label + "',MX+16,cy+218);", "ctx.fillStyle=rc('green');ctx.textAlign='right';ctx.fillText('" + right_label + "',W-MX-16,cy+218);", "ctx.restore();"], 480)

def neuro_stream(answer="Paracetamol 500mg: hạ sốt, giảm đau. Người lớn 1-2 viên/lần."):
    ans = json.dumps(answer, ensure_ascii=False)
    return scene(["var bx=W/2-270, by=cursorY+215;", "ctx.save();", "// neural net: 3 layers", "var L=[4,5,3], nodes=[];", "for(var c=0;c<3;c++){var col=[];", "  for(var r=0;r<L[c];r++){col.push([bx-95+c*95, by-((L[c]-1)*54)/2+r*54]);}nodes.push(col);}", "for(var c1=0;c1<2;c1++){", "  nodes[c1].forEach(function(a,ai){nodes[c1+1].forEach(function(b,bi){", "    var w=0.5+0.5*Math.sin(time*2.6-c1*1.4+ai+bi);", "    ctx.strokeStyle='rgba(34,211,238,'+(0.08+0.3*w)+')';ctx.lineWidth=1.4;", "    ctx.beginPath();ctx.moveTo(a[0],a[1]);ctx.lineTo(b[0],b[1]);ctx.stroke();});});}", "nodes.forEach(function(col,ci){col.forEach(function(n,ni){", "  var act=0.5+0.5*Math.sin(time*2.6-ci*1.4+ni);", "  ctx.fillStyle='rgba(34,211,238,'+(0.35+0.65*act)+')';", "  ctx.shadowColor=rc('cyan');ctx.shadowBlur=8*act;", "  ctx.beginPath();ctx.arc(n[0],n[1],7+act*3,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;});});", "// flying tokens to bubble", "var bubX=W/2+15, bubY=by-135, bubW=430, bubH=270;", "for(var i=0;i<3;i++){var t=(time*0.7+i/3)%1;", "  var fx=bx+95+(bubX-bx-95)*t, fy=by+Math.sin(t*Math.PI)*-46;", "  ctx.globalAlpha=1-t*0.4;ctx.fillStyle=rc('title');", "  RR(fx-7,fy-7,14,14,4);ctx.fill();ctx.globalAlpha=1;}", "// chat bubble", "ctx.fillStyle='rgba(255,255,255,0.05)';RR(bubX,bubY,bubW,bubH,22);ctx.fill();", "ctx.strokeStyle='rgba(34,211,238,0.45)';ctx.lineWidth=2;RR(bubX,bubY,bubW,bubH,22);ctx.stroke();", "ctx.beginPath();ctx.moveTo(bubX+2,by-16);ctx.lineTo(bubX-20,by);ctx.lineTo(bubX+2,by+16);", "ctx.fillStyle='rgba(255,255,255,0.05)';ctx.fill();", "// AI chip", "ctx.fillStyle='rgba(34,211,238,0.15)';RR(bubX+18,bubY+14,86,34,17);ctx.fill();", "ctx.fillStyle=rc('cyan');ctx.font='bold 21px sans-serif';ctx.textAlign='left';ctx.textBaseline='middle';", "ctx.fillText('🧠 AI',bubX+34,bubY+31);", "// streaming words", "var TXT=" + ans + ";var words=TXT.split(' ');", "var n=Math.floor(words.length*CL(P*1.15));", "var shown=words.slice(0,n).join(' ')+(n<words.length&&Math.floor(time*2.4)%2===0?' ▍':'');", "ctx.fillStyle='rgba(230,237,243,0.92)';ctx.font='25px sans-serif';", "var lines=wrapText(shown,bubW-44,'25px sans-serif');", "for(var li=0;li<Math.min(lines.length,5);li++){ctx.fillText(lines[li],bubX+22,bubY+80+li*36);}", "ctx.restore();"], 470)

def laser_scan(product="PARA 500", name="Paracetamol 500mg", price="2.000đ / viên", stock="Tồn: 128 vỉ"):
    return scene(["var bx=W/2-290, by=cursorY+55, bw=250, bh=320;", "ctx.save();", "// medicine box", "ctx.fillStyle='#f1f5f9';RR(bx,by,bw,bh,14);ctx.fill();", "ctx.fillStyle='#e11d48';RR(bx,by,bw,74,14);ctx.fillRect(bx,by+40,bw,34);ctx.fill();", "ctx.fillStyle='#fff';ctx.font='bold 30px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';", "ctx.fillText('" + product + "',bx+bw/2,by+40);", "ctx.fillStyle='#cbd5e1';RR(bx+30,by+100,bw-60,16,8);ctx.fill();RR(bx+30,by+130,bw-100,14,7);ctx.fill();", "// barcode", "var bcY=by+bh-96, bcH=64;", "ctx.fillStyle='#fff';RR(bx+28,bcY-10,bw-56,bcH+20,6);ctx.fill();", "for(var i=0;i<34;i++){var bwd=(i*7%3)+1.5;", "  ctx.fillStyle='#0f172a';ctx.fillRect(bx+36+i*(bw-72)/34,bcY,bwd,bcH);}", "// sweeping laser", "var ly=by+((Math.sin(time*1.7)+1)/2)*(bh-8)+4;", "var lg=ctx.createLinearGradient(bx-30,ly-22,bx-30,ly+22);", "lg.addColorStop(0,'rgba(239,68,68,0)');lg.addColorStop(0.5,'rgba(239,68,68,0.35)');lg.addColorStop(1,'rgba(239,68,68,0)');", "ctx.fillStyle=lg;ctx.fillRect(bx-24,ly-22,bw+48,44);", "ctx.strokeStyle='rgba(255,60,60,0.95)';ctx.lineWidth=3;ctx.shadowColor='#ff2020';ctx.shadowBlur=16;", "ctx.beginPath();ctx.moveTo(bx-24,ly);ctx.lineTo(bx+bw+24,ly);ctx.stroke();ctx.shadowBlur=0;", "// dashed connector", "var rp=CL(P*2.4-0.8);", "if(rp>0){ctx.strokeStyle='rgba(34,197,94,0.6)';ctx.lineWidth=2.5;ctx.setLineDash([8,7]);", "ctx.beginPath();ctx.moveTo(bx+bw+8,by+bh/2);ctx.lineTo(bx+bw+70,by+bh/2);ctx.stroke();ctx.setLineDash([]);}", "// result card pops", "if(rp>0){var sc=EB(rp), rx=bx+bw+78, ry=by+52;", "  ctx.save();ctx.translate(rx+160,ry+110);ctx.scale(sc,sc);ctx.translate(-(rx+160),-(ry+110));", "  ctx.fillStyle='rgba(34,197,94,0.09)';RR(rx,ry,320,220,20);ctx.fill();", "  ctx.strokeStyle=rc('green');ctx.lineWidth=2.5;ctx.shadowColor=rc('green');ctx.shadowBlur=14;", "  RR(rx,ry,320,220,20);ctx.stroke();ctx.shadowBlur=0;", "  ctx.textAlign='left';ctx.textBaseline='middle';", "  ctx.font='40px sans-serif';ctx.fillText('✅',rx+24,ry+46);", "  ctx.fillStyle='#fff';ctx.font='bold 28px sans-serif';ctx.fillText('" + name + "',rx+76,ry+46);", "  ctx.fillStyle=rc('green');ctx.font='bold 34px sans-serif';ctx.fillText('" + price + "',rx+24,ry+112);", "  ctx.fillStyle=rc('muted');ctx.font='25px sans-serif';ctx.fillText('" + stock + "',rx+24,ry+168);", "  ctx.restore();}", "ctx.restore();"], 440)

def metric_grid(metrics):
    payload = json.dumps(metrics, ensure_ascii=False); rows = (len(metrics) + 1) // 2; h = rows * 205 + 30
    return scene(["var MS=" + payload + ";", "var cw=(W-MX*2-28)/2, ch=185;", "ctx.save();", "MS.forEach(function(m,i){", "  var col=i%2,row=Math.floor(i/2);", "  var x=MX+col*(cw+28), y=cursorY+14+row*(ch+20);", "  var ap=CL(P*3-i*0.35);if(ap<=0)return;", "  var rise=(1-EZ(ap))*40;", "  ctx.globalAlpha=ap;", "  ctx.fillStyle='rgba(255,255,255,0.045)';RR(x,y+rise,cw,ch,20);ctx.fill();", "  ctx.strokeStyle='rgba(34,211,238,0.3)';ctx.lineWidth=1.5;RR(x,y+rise,cw,ch,20);ctx.stroke();", "  ctx.font='44px sans-serif';ctx.textAlign='left';ctx.textBaseline='middle';", "  ctx.fillText(m.icon,x+26,y+rise+52);", "  var val=Math.round(m.v*CL(P*1.5-i*0.15));", "  var vs=String(val).replace(/\\B(?=(\\d{3})+(?!\\d))/g,'.');", "  ctx.fillStyle=rc(m.color||'title');ctx.font='bold 58px sans-serif';", "  ctx.fillText(vs+(m.suffix||''),x+26,y+rise+118);", "  ctx.fillStyle=rc('muted');ctx.font='24px sans-serif';", "  ctx.fillText(m.label,x+28,y+rise+160);", "  ctx.globalAlpha=1;", "});", "ctx.restore();"], h)

def rocket_finale():
    return scene(["var cx=W/2, top=cursorY, hgt=540;", "ctx.save();", "// star field", "for(var i=0;i<46;i++){", "  var sx=((i*173)%(W-2*MX))+MX;", "  var sy=top+(((i*97)+time*(26+(i%4)*22))%hgt);", "  ctx.globalAlpha=0.25+((i*53)%50)/100;", "  ctx.fillStyle='#fff';ctx.fillRect(sx,sy,i%5===0?3:2,i%5===0?3:2);}", "ctx.globalAlpha=1;", "// planet arc at bottom", "var pg=ctx.createLinearGradient(0,top+hgt-90,0,top+hgt);", "pg.addColorStop(0,'rgba(34,211,238,0.25)');pg.addColorStop(1,'rgba(34,211,238,0)');", "ctx.fillStyle=pg;ctx.beginPath();ctx.arc(cx,top+hgt+560,640,Math.PI*1.15,Math.PI*1.85);ctx.fill();", "ctx.strokeStyle='rgba(34,211,238,0.5)';ctx.lineWidth=3;", "ctx.beginPath();ctx.arc(cx,top+hgt+560,600,Math.PI*1.2,Math.PI*1.8);ctx.stroke();", "// rocket ascent", "var ry=top+hgt-120-EZ(CL(P*1.1))*360, rx=cx+Math.sin(time*2.2)*7;", "// flame", "var fl=18+10*Math.abs(Math.sin(time*22));", "var fg=ctx.createLinearGradient(rx,ry+52,rx,ry+52+fl*3.4);", "fg.addColorStop(0,'rgba(255,215,0,0.95)');fg.addColorStop(0.5,'rgba(255,120,30,0.8)');fg.addColorStop(1,'rgba(255,60,0,0)');", "ctx.fillStyle=fg;ctx.beginPath();", "ctx.moveTo(rx-16,ry+50);ctx.quadraticCurveTo(rx,ry+52+fl*3.4,rx+16,ry+50);ctx.closePath();ctx.fill();", "// exhaust particles", "for(var e=0;e<8;e++){var et=(time*1.6+e/8)%1;", "  ctx.globalAlpha=(1-et)*0.6;ctx.fillStyle=e%2?'#ffb347':'#9ca3af';", "  ctx.beginPath();ctx.arc(rx+Math.sin(e*9)*14*et,ry+58+et*130,4+et*5,0,Math.PI*2);ctx.fill();}", "ctx.globalAlpha=1;", "// rocket emoji, rotated to fly up", "ctx.save();ctx.translate(rx,ry);ctx.rotate(-Math.PI/4);", "ctx.font='120px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';", "ctx.fillText('🚀',0,0);ctx.restore();", "ctx.restore();"], 560)

def forge_apk():
    return scene(["var cy=cursorY+190, lx=MX+110, mx=W/2, rxx=W-MX-130;", "ctx.save();", "// conveyor", "ctx.strokeStyle='rgba(255,255,255,0.1)';ctx.lineWidth=5;", "ctx.beginPath();ctx.moveTo(lx,cy);ctx.lineTo(rxx,cy);ctx.stroke();", "// source chips flying into machine", "var CHIPS=[['HTML','#ff9e64'],['CSS','#7aa2f7'],['JS','#e0af68']];", "CHIPS.forEach(function(c,i){", "  var t=(time*0.5+i/3)%1;", "  var sx=lx-40, sy=cy-120+i*70;", "  var fx=sx+(mx-70-sx)*t, fy=sy+(cy-sy)*t;", "  var shrink=1-t*0.45;", "  ctx.globalAlpha=t>0.9?(1-t)*10:1;", "  ctx.fillStyle='rgba(255,255,255,0.06)';", "  RR(fx-44*shrink,fy-24*shrink,88*shrink,48*shrink,10);ctx.fill();", "  ctx.strokeStyle=c[1];ctx.lineWidth=2;RR(fx-44*shrink,fy-24*shrink,88*shrink,48*shrink,10);ctx.stroke();", "  ctx.fillStyle=c[1];ctx.font='bold '+Math.round(24*shrink)+'px Consolas';", "  ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(c[0],fx,fy);", "  ctx.globalAlpha=1;});", "// capacitor machine (vibrates)", "var vib=Math.sin(time*26)*2.2;", "ctx.save();ctx.translate(vib,0);", "ctx.fillStyle='#0d1424';RR(mx-85,cy-95,170,190,24);ctx.fill();", "ctx.strokeStyle=rc('cyan');ctx.lineWidth=3;ctx.shadowColor=rc('cyan');ctx.shadowBlur=18;", "RR(mx-85,cy-95,170,190,24);ctx.stroke();ctx.shadowBlur=0;", "ctx.font='64px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText('⚡',mx,cy-16);", "ctx.fillStyle=rc('cyan');ctx.font='bold 21px sans-serif';ctx.fillText('CAPACITOR',mx,cy+56);", "// gear", "ctx.save();ctx.translate(mx+62,cy-72);ctx.rotate(time*2.4);", "ctx.strokeStyle='rgba(255,255,255,0.5)';ctx.lineWidth=3;", "for(var g=0;g<8;g++){ctx.beginPath();ctx.moveTo(0,10);ctx.lineTo(0,17);ctx.stroke();ctx.rotate(Math.PI/4);}", "ctx.beginPath();ctx.arc(0,0,10,0,Math.PI*2);ctx.stroke();ctx.restore();", "ctx.restore();", "// output phone with APK badge", "var op=CL(P*2.2-0.9), osc=EB(op);", "if(op>0){", "  ctx.save();ctx.translate(rxx,cy);ctx.scale(osc,osc);ctx.translate(-rxx,-cy);", "  ctx.fillStyle='#0c1322';ctx.strokeStyle=rc('green');ctx.lineWidth=3;", "  ctx.shadowColor=rc('green');ctx.shadowBlur=16;", "  RR(rxx-52,cy-95,104,190,22);ctx.fill();ctx.stroke();ctx.shadowBlur=0;", "  ctx.font='46px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText('💊',rxx,cy-14);", "  ctx.fillStyle=rc('green');RR(rxx-42,cy+40,84,36,18);ctx.fill();", "  ctx.fillStyle='#04210f';ctx.font='bold 22px sans-serif';ctx.fillText('APK',rxx,cy+58);", "  ctx.restore();}", "ctx.restore();"], 400)

def journey_path(items, walker="🚶"):
    payload = json.dumps(items, ensure_ascii=False)
    return scene(["var ITEMS=" + payload + ";", "var x0=MX+70, x1=W-MX-70, top=cursorY+40, bot=cursorY+430;", "ctx.save();", "function pt(t){", "  var x=x0+(x1-x0)*t;", "  var y=bot-(bot-top)*t + Math.sin(t*Math.PI*2)*52;", "  return [x,y];}", "// dotted base path", "ctx.setLineDash([2,16]);ctx.lineCap='round';ctx.lineWidth=7;", "ctx.strokeStyle='rgba(255,255,255,0.22)';", "ctx.beginPath();for(var s=0;s<=60;s++){var p=pt(s/60);if(s===0)ctx.moveTo(p[0],p[1]);else ctx.lineTo(p[0],p[1]);}ctx.stroke();", "// lit portion", "var lit=Math.max(0,Math.min(1,P*1.15));", "ctx.strokeStyle=rc('title');ctx.shadowColor=rc('title');ctx.shadowBlur=10;", "ctx.beginPath();for(var s2=0;s2<=60*lit;s2++){var p2=pt(s2/60);if(s2===0)ctx.moveTo(p2[0],p2[1]);else ctx.lineTo(p2[0],p2[1]);}ctx.stroke();", "ctx.setLineDash([]);ctx.shadowBlur=0;", "// milestones", "ITEMS.forEach(function(m,i){", "  var t=ITEMS.length===1?0.5:i/(ITEMS.length-1);", "  var p=pt(t);var on=lit>=t-0.02;", "  var pop=CL(P*2.6-i*0.4), sc=EB(pop);if(pop<=0)return;", "  ctx.save();ctx.translate(p[0],p[1]);ctx.scale(sc,sc);", "  ctx.fillStyle=on?'rgba(34,211,238,0.16)':'rgba(255,255,255,0.05)';", "  ctx.beginPath();ctx.arc(0,0,44,0,Math.PI*2);ctx.fill();", "  ctx.strokeStyle=on?rc('cyan'):'rgba(255,255,255,0.2)';ctx.lineWidth=3;", "  if(on){ctx.shadowColor=rc('cyan');ctx.shadowBlur=14;}", "  ctx.beginPath();ctx.arc(0,0,44,0,Math.PI*2);ctx.stroke();ctx.shadowBlur=0;", "  ctx.font='40px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';", "  ctx.fillText(m.icon,0,1);", "  ctx.restore();", "  var above=(i%2===0);", "  ctx.globalAlpha=pop;", "  ctx.font='bold 24px sans-serif';", "  var tw=ctx.measureText(m.label).width+36;", "  var lx=Math.max(MX,Math.min(p[0]-tw/2,W-MX-tw));", "  var lyy=above?p[1]-96:p[1]+62;", "  ctx.fillStyle='rgba(13,20,36,0.92)';RR(lx,lyy,tw,42,21);ctx.fill();", "  ctx.strokeStyle=on?'rgba(34,211,238,0.5)':'rgba(255,255,255,0.15)';ctx.lineWidth=1.5;RR(lx,lyy,tw,42,21);ctx.stroke();", "  ctx.fillStyle=on?rc('text'):rc('muted');ctx.textAlign='center';ctx.textBaseline='middle';", "  ctx.fillText(m.label,lx+tw/2,lyy+22);", "  ctx.globalAlpha=1;", "});", "// walker bobbing at lit tip", "var wp=pt(Math.min(lit,1));", "ctx.font='44px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';", "ctx.fillText('" + walker + "',wp[0],wp[1]-58-Math.abs(Math.sin(time*6))*8);", "if(lit>0.97){ctx.font='48px sans-serif';ctx.fillText('🏁',x1+8,top-60);}", "ctx.restore();"], 500)

def tool_dock(tools):
    payload = json.dumps(tools, ensure_ascii=False)
    return scene(["var TS=" + payload + ";", "var n=TS.length, cw=Math.min(300,(W-MX*2-(n-1)*26)/n), totalW=cw*n+26*(n-1);", "var x0=W/2-totalW/2, y0=cursorY+30, ch=330;", "ctx.save();", "TS.forEach(function(t,i){", "  var ap=CL(P*2.6-i*0.42);if(ap<=0)return;", "  var drop=(1-EB(ap))*-90;", "  var x=x0+i*(cw+26), y=y0+drop;", "  ctx.globalAlpha=Math.min(1,ap*1.6);", "  ctx.fillStyle='rgba(255,255,255,0.05)';RR(x,y,cw,ch,24);ctx.fill();", "  ctx.strokeStyle='rgba(34,211,238,0.35)';ctx.lineWidth=2;RR(x,y,cw,ch,24);ctx.stroke();", "  ctx.fillStyle='rgba(34,211,238,0.1)';RR(x+cw/2-56,y+30,112,112,28);ctx.fill();", "  ctx.strokeStyle='rgba(34,211,238,0.4)';RR(x+cw/2-56,y+30,112,112,28);ctx.stroke();", "  ctx.font='64px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';", "  ctx.fillText(t.icon,x+cw/2,y+88);", "  ctx.fillStyle='#fff';ctx.font='bold 30px sans-serif';ctx.fillText(t.name,x+cw/2,y+186);", "  ctx.fillStyle=rc('muted');ctx.font='22px sans-serif';", "  var lines=wrapText(t.sub,cw-36,'22px sans-serif');", "  lines.slice(0,2).forEach(function(l,li){ctx.fillText(l,x+cw/2,y+224+li*30);});", "  var bp=CL(P*1.7-0.25-i*0.2);", "  ctx.fillStyle='rgba(255,255,255,0.1)';RR(x+30,y+ch-40,cw-60,14,7);ctx.fill();", "  ctx.fillStyle=bp>=1?rc('green'):rc('cyan');RR(x+30,y+ch-40,(cw-60)*bp,14,7);ctx.fill();", "  if(bp>=1){ctx.fillStyle=rc('green');ctx.font='bold 20px sans-serif';ctx.fillText('✓ SẴN SÀNG',x+cw/2,y+ch-64);}", "  ctx.globalAlpha=1;", "});", "ctx.restore();"], 400)

def keycaps(word="LÀM!"):
    letters = json.dumps(list(word), ensure_ascii=False)
    return scene(["var KS=" + letters + ";", "var n=KS.length, kw=118, gap=20, totalW=n*kw+(n-1)*gap;", "var x0=W/2-totalW/2, y0=cursorY+45;", "ctx.save();", "KS.forEach(function(k,i){", "  var w=Math.sin(time*3.2-i*0.9);var press=w>0.55?1:0;", "  var dy=press*10;", "  var x=x0+i*(kw+gap);", "  ctx.fillStyle='rgba(0,0,0,0.5)';RR(x,y0+14,kw,118,20);ctx.fill();", "  var kg=ctx.createLinearGradient(0,y0+dy,0,y0+dy+118);", "  kg.addColorStop(0,'#1d283f');kg.addColorStop(1,'#0d1424');", "  ctx.fillStyle=kg;RR(x,y0+dy,kw,118,20);ctx.fill();", "  ctx.strokeStyle=press?rc('cyan'):'rgba(255,255,255,0.2)';ctx.lineWidth=2.5;", "  if(press){ctx.shadowColor=rc('cyan');ctx.shadowBlur=18;}", "  RR(x,y0+dy,kw,118,20);ctx.stroke();ctx.shadowBlur=0;", "  ctx.fillStyle=press?rc('cyan'):'#e6edf3';ctx.font='bold 56px sans-serif';", "  ctx.textAlign='center';ctx.textBaseline='middle';", "  ctx.fillText(k,x+kw/2,y0+dy+60);", "});", "ctx.restore();"], 230)

def stamp_done(text="XONG BÀI 1"):
    safe = text.replace("'", "\\'")
    return scene(["var cx=W/2, cy=cursorY+185;", "ctx.save();", "var sp=CL(P*1.8);", "var sc=3-2*EZ(sp); if(sp>=1)sc=1;", "var rot=-0.12*(1-EZ(sp))-0.06;", "ctx.globalAlpha=Math.min(1,sp*1.5);", "ctx.translate(cx,cy);ctx.rotate(rot);ctx.scale(sc,sc);", "ctx.strokeStyle=rc('green');ctx.lineWidth=9;", "ctx.shadowColor=rc('green');ctx.shadowBlur=sp>=0.95?22:0;", "ctx.beginPath();ctx.arc(0,0,150,0,Math.PI*2);ctx.stroke();", "ctx.lineWidth=3;ctx.beginPath();ctx.arc(0,0,128,0,Math.PI*2);ctx.stroke();ctx.shadowBlur=0;", "for(var d=0;d<24;d++){var a=d*(Math.PI*2/24);", "  ctx.fillStyle='rgba(34,197,94,0.65)';", "  ctx.beginPath();ctx.arc(Math.cos(a)*139,Math.sin(a)*139,3,0,Math.PI*2);ctx.fill();}", "// hand-drawn check stroke (emoji 2714 is black in Twemoji — invisible on dark)", "ctx.strokeStyle=rc('green');ctx.lineWidth=16;ctx.lineCap='round';ctx.lineJoin='round';", "ctx.beginPath();ctx.moveTo(-48,-38);ctx.lineTo(-12,-4);ctx.lineTo(58,-78);ctx.stroke();", "ctx.fillStyle=rc('green');ctx.font='bold 44px sans-serif';", "ctx.textAlign='center';ctx.textBaseline='middle';", "var words='" + safe + "'.split(' ');", "if(words.length>=2){ctx.fillText(words[0],0,36);ctx.fillText(words.slice(1).join(' '),0,88);}", "else{ctx.fillText('" + safe + "',0,52);}", "ctx.restore();", "if(sp>=0.9){", "  for(var q=0;q<10;q++){var qa=q*(Math.PI*2/10)+0.4;", "    var qt=Math.min(1,(sp-0.9)*10)*0.6+((time*0.8+q*0.1)%0.4);", "    ctx.globalAlpha=Math.max(0,0.8-qt);ctx.fillStyle=q%2?rc('green'):rc('title');", "    ctx.beginPath();ctx.arc(cx+Math.cos(qa)*(165+qt*90),cy+Math.sin(qa)*(165+qt*90),4,0,Math.PI*2);ctx.fill();}", "  ctx.globalAlpha=1;}", "ctx.restore();"], 380)

def versus_split(left_title, left_sub, right_title, right_sub, left_icon="❌", right_icon="✅"):
    return scene(["var cy=cursorY+165, cw=(W-MX*2-130)/2, ch=250;", "var lx=MX, rx=W-MX-cw;", "ctx.save();", "var sl=EB(CL(P*1.6));", "// left card slides from left (red)", "ctx.save();ctx.translate(-(1-sl)*320,0);", "ctx.fillStyle='rgba(239,68,68,0.07)';RR(lx,cy-ch/2,cw,ch,22);ctx.fill();", "ctx.strokeStyle='rgba(239,68,68,0.7)';ctx.lineWidth=2.5;RR(lx,cy-ch/2,cw,ch,22);ctx.stroke();", "ctx.font='46px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';", "ctx.fillText('" + left_icon + "',lx+cw/2,cy-ch/2+56);", "ctx.fillStyle='#fff';ctx.font='bold 30px sans-serif';", "ctx.fillText('" + left_title.replace("'", "\\'") + "',lx+cw/2,cy-8);", "ctx.fillStyle=rc('red');ctx.font='24px sans-serif';", "var ll=wrapText('" + left_sub.replace("'", "\\'") + "',cw-40,'24px sans-serif');", "ll.slice(0,2).forEach(function(l,i){ctx.fillText(l,lx+cw/2,cy+38+i*32);});", "ctx.restore();", "// right card slides from right (green)", "ctx.save();ctx.translate((1-sl)*320,0);", "ctx.fillStyle='rgba(34,197,94,0.07)';RR(rx,cy-ch/2,cw,ch,22);ctx.fill();", "ctx.strokeStyle='rgba(34,197,94,0.75)';ctx.lineWidth=2.5;", "ctx.shadowColor=rc('green');ctx.shadowBlur=10;RR(rx,cy-ch/2,cw,ch,22);ctx.stroke();ctx.shadowBlur=0;", "ctx.font='46px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';", "ctx.fillText('" + right_icon + "',rx+cw/2,cy-ch/2+56);", "ctx.fillStyle='#fff';ctx.font='bold 30px sans-serif';", "ctx.fillText('" + right_title.replace("'", "\\'") + "',rx+cw/2,cy-8);", "ctx.fillStyle=rc('green');ctx.font='24px sans-serif';", "var rl=wrapText('" + right_sub.replace("'", "\\'") + "',cw-40,'24px sans-serif');", "rl.slice(0,2).forEach(function(l,i){ctx.fillText(l,rx+cw/2,cy+38+i*32);});", "ctx.restore();", "// VS badge with electric ring", "var vp=EB(CL(P*2.2-0.5));", "if(vp>0){ctx.save();ctx.translate(W/2,cy);ctx.scale(vp,vp);", "ctx.fillStyle='#0d1424';ctx.beginPath();ctx.arc(0,0,52,0,Math.PI*2);ctx.fill();", "ctx.strokeStyle=rc('title');ctx.lineWidth=3.5;ctx.shadowColor=rc('title');ctx.shadowBlur=16;", "ctx.beginPath();ctx.arc(0,0,52,0,Math.PI*2);ctx.stroke();ctx.shadowBlur=0;", "for(var k=0;k<6;k++){var a=k*Math.PI/3+time*2.2;",
    
    "  ctx.strokeStyle='rgba(255,215,0,0.5)';ctx.lineWidth=2;", "  ctx.beginPath();ctx.moveTo(Math.cos(a)*58,Math.sin(a)*58);ctx.lineTo(Math.cos(a)*70,Math.sin(a)*70);ctx.stroke();}", "ctx.fillStyle=rc('title');ctx.font='bold 40px sans-serif';", "ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText('VS',0,2);",
    
    "ctx.restore();}", "ctx.restore();"], 340)

def web_window(url, title, badge="LIVE", badge_color="green"):
    return scene(["var w=Math.min(W-MX*2,860), x=W/2-w/2, y=cursorY+8, h=380;", "ctx.save();", "ctx.shadowColor='rgba(0,0,0,0.55)';ctx.shadowBlur=26;ctx.shadowOffsetY=8;", "ctx.fillStyle='#0d1424';RR(x,y,w,h,18);ctx.fill();ctx.shadowBlur=0;ctx.shadowOffsetY=0;", "ctx.strokeStyle='rgba(34,211,238,0.35)';ctx.lineWidth=1.5;RR(x,y,w,h,18);ctx.stroke();", "// chrome bar", "ctx.fillStyle='rgba(255,255,255,0.045)';RR(x,y,w,56,18);ctx.fill();", "['#ff5f57','#febc2e','#28c840'].forEach(function(c,i){ctx.fillStyle=c;ctx.beginPath();ctx.arc(x+28+i*28,y+28,7,0,Math.PI*2);ctx.fill();});", "// url pill", "ctx.fillStyle='rgba(255,255,255,0.07)';RR(x+110,y+13,w-240,30,15);ctx.fill();", "ctx.fillStyle=rc('green');ctx.font='17px sans-serif';ctx.textAlign='left';ctx.textBaseline='middle';", "ctx.fillText('🔒',x+124,y+29);", "ctx.fillStyle='rgba(230,237,243,0.85)';ctx.font='19px Consolas';", "ctx.fillText('" + url + "',x+152,y+29);", "// badge chip", "ctx.fillStyle='rgba(34,197,94,0.16)';RR(x+w-112,y+13,96,30,15);ctx.fill();", "ctx.fillStyle=rc('" + badge_color + "');ctx.font='bold 17px sans-serif';ctx.textAlign='center';", "ctx.fillText('" + badge + "',x+w-64,y+29);", "// loading bar completes by P", "var lp=CL(P*1.7);", "ctx.fillStyle=rc('cyan');ctx.fillRect(x,y+56,w*lp,3);", "// page content skeleton reveals", "var reveal=CL(P*1.9-0.25);", "ctx.globalAlpha=Math.min(1,reveal*1.6);", "ctx.fillStyle='rgba(34,211,238,0.14)';RR(x+34,y+86,w-68,64,12);ctx.fill();", "ctx.fillStyle='#fff';ctx.font='bold 30px sans-serif';ctx.textAlign='center';", "var tl=wrapText('" + title.replace("'", "\\'") + "',w-110,'bold 30px sans-serif');", "ctx.fillText(tl[0]||'',x+w/2,y+118);", "ctx.globalAlpha=1;", "for(var i=0;i<3;i++){var rp2=CL(reveal*3-0.5-i*0.5);if(rp2<=0)continue;", "  ctx.globalAlpha=rp2;", "  var ry=y+176+i*60;", "  ctx.fillStyle='rgba(255,255,255,0.05)';RR(x+34,ry,w-68,46,10);ctx.fill();", "  ctx.fillStyle=['rgba(34,211,238,0.7)','rgba(34,197,94,0.7)','rgba(255,215,0,0.7)'][i];", "  ctx.beginPath();ctx.arc(x+66,ry+23,12,0,Math.PI*2);ctx.fill();", "  ctx.fillStyle='rgba(255,255,255,0.5)';RR(x+96,ry+15,190+i*40,14,7);ctx.fill();", "  ctx.globalAlpha=1;}", "// shimmer sweep while loading", "if(lp<1){var shx=x+((time*260)%(w+200))-100;", "  var sg=ctx.createLinearGradient(shx-70,0,shx+70,0);", "  sg.addColorStop(0,'rgba(255,255,255,0)');sg.addColorStop(0.5,'rgba(255,255,255,0.05)');sg.addColorStop(1,'rgba(255,255,255,0)');", "  ctx.fillStyle=sg;ctx.fillRect(x,y+60,w,h-60);}", "ctx.restore();"], 410)

def check_sweep(items):
    payload = json.dumps(items, ensure_ascii=False); h = len(items) * 92 + 30
    return scene(["var ITEMS=" + payload + ";", "var w=Math.min(W-MX*2,760), x=W/2-w/2;", "ctx.save();", "ITEMS.forEach(function(it,i){", "  var ap=CL(P*2.8-i*0.5);if(ap<=0)return;", "  var y=cursorY+16+i*92;", "  var slide=(1-EZ(ap))*60;", "  ctx.globalAlpha=Math.min(1,ap*1.5);", "  ctx.fillStyle='rgba(255,255,255,0.045)';RR(x+slide,y,w,76,38);ctx.fill();", "  ctx.strokeStyle=it.ok?'rgba(34,197,94,0.45)':'rgba(239,68,68,0.45)';", "  ctx.lineWidth=2;RR(x+slide,y,w,76,38);ctx.stroke();", "  // circle + animated mark", "  var mcx=x+slide+42, mcy=y+38;", "  ctx.strokeStyle=it.ok?rc('green'):rc('red');ctx.lineWidth=3.5;", "  ctx.beginPath();ctx.arc(mcx,mcy,22,-Math.PI/2,-Math.PI/2+Math.PI*2*CL(ap*1.4));ctx.stroke();", "  var mp=CL(ap*2-0.7);", "  if(mp>0){ctx.lineWidth=5;ctx.lineCap='round';", "    if(it.ok){ctx.beginPath();ctx.moveTo(mcx-9,mcy+1);", "      ctx.lineTo(mcx-9+8*mp,mcy+1+7*mp);ctx.lineTo(mcx-1+12*mp*0,mcy+8);", "      ctx.moveTo(mcx-1,mcy+8);ctx.lineTo(mcx-1+11*mp,mcy+8-14*mp);ctx.stroke();}", "    else{ctx.beginPath();ctx.moveTo(mcx-8*mp,mcy-8*mp);ctx.lineTo(mcx+8*mp,mcy+8*mp);", "      ctx.moveTo(mcx+8*mp,mcy-8*mp);ctx.lineTo(mcx-8*mp,mcy+8*mp);ctx.stroke();}}", "  ctx.fillStyle=it.ok?'#e6edf3':'rgba(230,237,243,0.85)';", "  ctx.font='bold 28px sans-serif';ctx.textAlign='left';ctx.textBaseline='middle';", "  ctx.fillText(it.text,x+slide+86,y+39);", "  ctx.globalAlpha=1;", "});", "ctx.restore();"], h)

def style_sync(caption="Cùng 1 hội thoại = cùng 1 phong cách"):
    return scene(["var n=4, cw=150, ch=250, gap=34;", "var x0=W/2-(n*cw+(n-1)*gap)/2, y0=cursorY+30;", "ctx.save();", "var hue=[188,188,188,188];", "var sync=CL(P*1.4);", "for(var i=0;i<n;i++){", "  var ap=CL(P*2.6-i*0.35);if(ap<=0)continue;", "  var x=x0+i*(cw+gap);", "  // before-sync each card has its own hue; they converge to cyan as P grows", "  var own=[0,268,120,35][i];", "  var hh=own+(188-own)*sync;", "  ctx.globalAlpha=ap;", "  ctx.fillStyle='#0c1322';RR(x,y0,cw,ch,20);ctx.fill();", "  ctx.strokeStyle='hsla('+hh+',80%,60%,0.85)';ctx.lineWidth=2.5;", "  if(sync>0.9){ctx.shadowColor='hsl(188,80%,60%)';ctx.shadowBlur=12;}", "  RR(x,y0,cw,ch,20);ctx.stroke();ctx.shadowBlur=0;", "  // header band", "  ctx.fillStyle='hsla('+hh+',80%,60%,0.3)';RR(x+12,y0+14,cw-24,34,9);ctx.fill();", "  // content bars", "  ctx.fillStyle='rgba(255,255,255,0.16)';", "  RR(x+12,y0+64,cw-24,14,7);ctx.fill();RR(x+12,y0+90,cw-46,14,7);ctx.fill();", "  // button", "  ctx.fillStyle='hsla('+hh+',80%,60%,0.75)';RR(x+12,y0+ch-52,cw-24,32,16);ctx.fill();", "  ctx.globalAlpha=1;", "}", "// sync link line under cards", "if(sync>0.5){var ly=y0+ch+34;", "  ctx.strokeStyle='rgba(34,211,238,0.6)';ctx.lineWidth=2.5;ctx.setLineDash([10,8]);", "  ctx.lineDashOffset=-time*30;", "  ctx.beginPath();ctx.moveTo(x0+20,ly);ctx.lineTo(x0+n*cw+(n-1)*gap-20,ly);ctx.stroke();ctx.setLineDash([]);", "  ctx.fillStyle=rc('cyan');ctx.font='bold 26px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';", "  ctx.fillText('" + caption.replace("'", "\\'") + "',W/2,ly+44);}", "ctx.restore();"], 400)

def big_word(kicker, word, sub, color="title"):
    letters = json.dumps(list(word), ensure_ascii=False)
    return scene(["var LS=" + letters + ";", "var cy=cursorY+195;", "ctx.save();", "// kicker", "ctx.textAlign='center';ctx.textBaseline='middle';", "ctx.fillStyle=rc('muted');ctx.font='bold 28px sans-serif';", "ctx.fillText('" + kicker.replace("'", "\\'") + "',W/2,cy-118);", "// fit font size", "var fs=130;", "ctx.font='bold '+fs+'px sans-serif';", "var full=LS.join('');", "while(ctx.measureText(full).width>W-MX*2-40&&fs>54){fs-=6;ctx.font='bold '+fs+'px sans-serif';}", "var widths=LS.map(function(ch){return ctx.measureText(ch).width;});", "var total=widths.reduce(function(a,b){return a+b;},0)+ (LS.length-1)*6;", "var x=W/2-total/2;", "// letters pop in staggered", "for(var i=0;i<LS.length;i++){", "  var lp=CL(P*2.4-i*0.14);", "  if(lp>0){var sc=EB(lp);", "    ctx.save();ctx.translate(x+widths[i]/2,cy);ctx.scale(sc,sc);", "    ctx.globalAlpha=Math.min(1,lp*1.8);", "    ctx.shadowColor=rc('" + color + "');ctx.shadowBlur=lp>=1?16:0;", "    ctx.fillStyle=rc('" + color + "');ctx.font='bold '+fs+'px sans-serif';", "    ctx.fillText(LS[i],0,0);ctx.restore();}", "  x+=widths[i]+6;", "}", "// underline sweep", "var up=CL(P*1.6-0.4);", "if(up>0){ctx.strokeStyle=rc('cyan');ctx.lineWidth=5;ctx.lineCap='round';", "  ctx.beginPath();ctx.moveTo(W/2-total/2*up,cy+fs*0.62);ctx.lineTo(W/2+total/2*up,cy+fs*0.62);ctx.stroke();}", "// sub", "var sp=CL(P*2-0.9);", "ctx.globalAlpha=sp;ctx.fillStyle=rc('cyan');ctx.font='bold 32px sans-serif';", "ctx.fillText('" + sub.replace("'", "\\'") + "',W/2,cy+fs*0.62+56);", "ctx.globalAlpha=1;ctx.restore();"], 420)

def progress_map(n, total=13, done_text="", remain_text=""):
    if not done_text:
        done_text = f"✓  XONG BÀI {n}"
    done = done_text.replace("'", "\\'")
    rem_n = max(0, int(total) - int(n))
    if not remain_text:
        remain_text = (
            f"Còn {rem_n} bài nữa — tiếp tục nào!"
            if rem_n
            else "Hoàn thành toàn bộ serial!"
        )
    if remain_text:
        match remain_text.replace("'", "\\'"):
            case _ as remain:
                return scene(["var N=" + str(total) + ", DONE=" + str(n) + ";", "var y=cursorY+205, x0=MX+34, x1=W-MX-34;", "var step=(x1-x0)/(N-1);", "ctx.save();", "// done chip on top", "var cp=EB(CL(P*1.6));", "ctx.save();ctx.translate(W/2,cursorY+80);ctx.scale(cp,cp);", "ctx.font='bold 44px sans-serif';", "var ct='" + done + "';", "var cw2=ctx.measureText(ct).width+76;", "ctx.fillStyle='rgba(34,197,94,0.12)';RR(-cw2/2,-40,cw2,80,40);ctx.fill();", "ctx.strokeStyle=rc('green');ctx.lineWidth=3;ctx.shadowColor=rc('green');ctx.shadowBlur=16;", "RR(-cw2/2,-40,cw2,80,40);ctx.stroke();ctx.shadowBlur=0;", "ctx.fillStyle=rc('green');ctx.textAlign='center';ctx.textBaseline='middle';", "ctx.fillText(ct,0,2);ctx.restore();", "// rail", "ctx.strokeStyle='rgba(255,255,255,0.14)';ctx.lineWidth=6;ctx.lineCap='round';", "ctx.beginPath();ctx.moveTo(x0,y);ctx.lineTo(x1,y);ctx.stroke();", "// lit rail up to current", "var lit=CL(P*1.3);", "ctx.strokeStyle=rc('green');ctx.shadowColor=rc('green');ctx.shadowBlur=8;", "ctx.beginPath();ctx.moveTo(x0,y);ctx.lineTo(x0+step*(DONE-1)*lit,y);ctx.stroke();ctx.shadowBlur=0;", "// nodes", "for(var i=0;i<N;i++){", "  var nx=x0+step*i;",
    
    "  var isDone=i<DONE, isCur=(i===DONE-1);", "  var ap=CL(P*2.4-i*0.1);", "  if(isDone&&ap>0){", "    ctx.fillStyle=rc('green');", "    if(isCur){var pl=1+0.22*Math.sin(time*5);", "      ctx.strokeStyle='rgba(34,197,94,0.55)';ctx.lineWidth=3;",
    
    "      ctx.beginPath();ctx.arc(nx,y,15*pl+6,0,Math.PI*2);ctx.stroke();}", "    ctx.shadowColor=rc('green');ctx.shadowBlur=10;", "    ctx.beginPath();ctx.arc(nx,y,isCur?13:9,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;",
    
    "  }else{", "    ctx.fillStyle='rgba(255,255,255,0.16)';", "    ctx.beginPath();ctx.arc(nx,y,7,0,Math.PI*2);ctx.fill();", "  }", "  // milestone numbers every node under", "  if(i===0||i===N-1||isCur){", "    ctx.fillStyle=isCur?rc('green'):rc('muted');", "    ctx.font=(isCur?'bold 26px':'22px')+' sans-serif';ctx.textAlign='center';ctx.textBaseline='alphabetic';", "    ctx.fillText(String(i+1),nx,y+44);}", "}", "// remaining text", "ctx.fillStyle=rc('muted');ctx.font='26px sans-serif';ctx.textAlign='center';", "ctx.fillText('" + remain + "',W/2,y+96);", "ctx.restore();"], 330)

def stairs_steps(items):
    payload = json.dumps(items, ensure_ascii=False); n = len(items); h = 150 + n * 108
    return scene(["var ITEMS=" + payload + ";", "var n=ITEMS.length;", "var stepH=96, stepGap=12;", "var baseY=cursorY+40+(n-1)*(stepH+stepGap)+stepH;", "var colW=Math.min(560,W-MX*2-260);", "ctx.save();", "ITEMS.forEach(function(it,i){", "  var ap=CL(P*2.6-i*0.45);if(ap<=0)return;", "  var rise=(1-EB(ap))*70;", "  var y=baseY-(i+1)*(stepH+stepGap)+rise;", "  var x=MX+40+i*((W-MX*2-colW-80)/Math.max(1,n-1));", "  ctx.globalAlpha=Math.min(1,ap*1.5);", "  // platform", "  ctx.fillStyle='rgba(255,255,255,0.05)';RR(x,y,colW,stepH,18);ctx.fill();", "  ctx.strokeStyle='rgba(34,211,238,0.45)';ctx.lineWidth=2;RR(x,y,colW,stepH,18);ctx.stroke();", "  // side edge (3D feel)", "  ctx.fillStyle='rgba(34,211,238,0.12)';", "  ctx.beginPath();ctx.moveTo(x+18,y+stepH);ctx.lineTo(x+30,y+stepH+10);", "  ctx.lineTo(x+colW+12,y+stepH+10);ctx.lineTo(x+colW,y+stepH);ctx.closePath();ctx.fill();", "  // number badge", "  ctx.fillStyle='rgba(34,211,238,0.16)';ctx.beginPath();ctx.arc(x+52,y+stepH/2,30,0,Math.PI*2);ctx.fill();", "  ctx.strokeStyle=rc('cyan');ctx.lineWidth=2.5;ctx.beginPath();ctx.arc(x+52,y+stepH/2,30,0,Math.PI*2);ctx.stroke();", "  ctx.fillStyle=rc('cyan');ctx.font='bold 32px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';", "  ctx.fillText(String(i+1),x+52,y+stepH/2+1);", "  // icon + label", "  ctx.font='38px sans-serif';ctx.fillText(it.icon,x+116,y+stepH/2);", "  ctx.fillStyle='#fff';ctx.font='bold 28px sans-serif';ctx.textAlign='left';", "  ctx.fillText(it.label,x+156,y+stepH/2+1);", "  ctx.globalAlpha=1;", "});", "// climber dot ascending along badges", "var cp2=CL(P*1.2);", "var idx=Math.min(n-1,Math.floor(cp2*n));", "var fx=MX+40+idx*((W-MX*2-colW-80)/Math.max(1,n-1))+52;", "var fy=baseY-(idx+1)*(stepH+stepGap)-26;", "ctx.fillStyle=rc('title');ctx.shadowColor=rc('title');ctx.shadowBlur=14;", "ctx.beginPath();ctx.arc(fx,fy-8-Math.abs(Math.sin(time*5))*7,9,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;", "ctx.restore();"], h)

def domino_flow(items):
    payload = json.dumps(items, ensure_ascii=False)
    return scene(["var ITEMS=" + payload + ";", "var n=ITEMS.length;", "var cw=Math.min(272,(W-MX*2-(n-1)*70)/n), ch=300;", "var totalW=cw*n+70*(n-1);", "var x0=W/2-totalW/2, y0=cursorY+35;", "ctx.save();", "ITEMS.forEach(function(it,i){", "  var ap=CL(P*2.4-i*0.5);", "  // chevron before card (i>0)", "  if(i>0){var chp=CL(P*2.4-i*0.5+0.25);", "    var chx=x0+i*(cw+70)-46;", "    for(var k2=0;k2<2;k2++){", "      var lit=chp>0.5, pulse=(time*2+i)%1;", "      ctx.strokeStyle=lit?('rgba(255,215,0,'+(0.55+0.45*Math.sin(time*5-i))+')'):'rgba(255,255,255,0.15)';", "      ctx.lineWidth=6;ctx.lineCap='round';", "      ctx.beginPath();ctx.moveTo(chx+k2*20,y0+ch/2-16);", "      ctx.lineTo(chx+k2*20+14,y0+ch/2);ctx.lineTo(chx+k2*20,y0+ch/2+16);ctx.stroke();}}", "  if(ap<=0)return;", "  // card flips in (scaleX)", "  var sc=EB(ap);", "  var x=x0+i*(cw+70);", "  ctx.save();ctx.translate(x+cw/2,y0+ch/2);ctx.scale(Math.max(0.02,sc),1);ctx.translate(-(x+cw/2),-(y0+ch/2));", "  ctx.globalAlpha=Math.min(1,ap*1.6);", "  ctx.fillStyle='#0d1424';RR(x,y0,cw,ch,22);ctx.fill();", "  var last=i===n-1;", "  ctx.strokeStyle=last?rc('green'):'rgba(34,211,238,0.55)';ctx.lineWidth=2.5;", "  if(last&&ap>=1){ctx.shadowColor=rc('green');ctx.shadowBlur=14;}", "  RR(x,y0,cw,ch,22);ctx.stroke();ctx.shadowBlur=0;", "  // big step number watermark", "  ctx.fillStyle='rgba(255,255,255,0.06)';ctx.font='bold 110px sans-serif';", "  ctx.textAlign='center';ctx.textBaseline='middle';", "  ctx.fillText(String(i+1),x+cw/2,y0+72);", "  // icon", "  ctx.font='58px sans-serif';ctx.fillText(it.icon,x+cw/2,y0+140);", "  // label (wrap 2 lines)", "  ctx.fillStyle='#fff';ctx.font='bold 26px sans-serif';", "  var ls=wrapText(it.label,cw-30,'bold 26px sans-serif');", "  ls.slice(0,2).forEach(function(l,li){ctx.fillText(l,x+cw/2,y0+212+li*34);});", "  ctx.globalAlpha=1;ctx.restore();", "});", "ctx.restore();"], 360)

def orbit_cycle(items, center_label="LẶP LẠI"):
    payload = json.dumps(items, ensure_ascii=False)
    return scene(["var ITEMS=" + payload + ";", "var cx=W/2, cy=cursorY+310, R=185;", "ctx.save();", "// rotating dashed orbit with direction arrows", "ctx.strokeStyle='rgba(34,211,238,0.4)';ctx.lineWidth=3;", "ctx.setLineDash([14,12]);ctx.lineDashOffset=-time*36;", "ctx.beginPath();ctx.arc(cx,cy,R,0,Math.PI*2);ctx.stroke();ctx.setLineDash([]);", "// 3 direction arrowheads gliding on the orbit", "for(var a2=0;a2<3;a2++){", "  var ang=time*0.7+a2*(Math.PI*2/3);", "  var ax=cx+Math.cos(ang)*R, ay=cy+Math.sin(ang)*R;", "  var tx=-Math.sin(ang), ty=Math.cos(ang);", "  ctx.fillStyle='rgba(255,215,0,0.85)';", "  ctx.beginPath();ctx.moveTo(ax+tx*16,ay+ty*16);", "  ctx.lineTo(ax-tx*6+Math.cos(ang)*9,ay-ty*6+Math.sin(ang)*9);", "  ctx.lineTo(ax-tx*6-Math.cos(ang)*9,ay-ty*6-Math.sin(ang)*9);ctx.closePath();ctx.fill();}", "// center label", "ctx.fillStyle='rgba(13,20,36,0.95)';ctx.beginPath();ctx.arc(cx,cy,74,0,Math.PI*2);ctx.fill();", "ctx.strokeStyle='rgba(255,255,255,0.2)';ctx.lineWidth=2;ctx.beginPath();ctx.arc(cx,cy,74,0,Math.PI*2);ctx.stroke();", "ctx.font='34px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';", "ctx.fillText('🔁',cx,cy-20);", "ctx.fillStyle=rc('cyan');ctx.font='bold 23px sans-serif';", "ctx.fillText('" + center_label.replace("'", "\\'") + "',cx,cy+26);", "// nodes at 12h, 4h, 8h", "ITEMS.forEach(function(it,i){", "  var ang=-Math.PI/2+i*(Math.PI*2/ITEMS.length);", "  var nx=cx+Math.cos(ang)*R, ny=cy+Math.sin(ang)*R;", "  var ap=CL(P*2.4-i*0.45);if(ap<=0)return;", "  var sc=EB(ap);", "  // active highlight cycles with time", "  var active=Math.floor(time*0.9)%ITEMS.length===i;", "  ctx.save();ctx.translate(nx,ny);ctx.scale(sc,sc);", "  ctx.fillStyle=active?'rgba(34,211,238,0.2)':'rgba(13,20,36,0.95)';", "  ctx.beginPath();ctx.arc(0,0,52,0,Math.PI*2);ctx.fill();", "  ctx.strokeStyle=active?rc('cyan'):'rgba(34,211,238,0.45)';ctx.lineWidth=3;", "  if(active){ctx.shadowColor=rc('cyan');ctx.shadowBlur=18;}", "  ctx.beginPath();ctx.arc(0,0,52,0,Math.PI*2);ctx.stroke();ctx.shadowBlur=0;", "  ctx.font='42px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';", "  ctx.fillText(it.icon,0,1);ctx.restore();", "  // label chip outside node", "  ctx.globalAlpha=ap;", "  ctx.font='bold 25px sans-serif';", "  var tw=ctx.measureText(it.label).width+34;", "  var lx=nx-tw/2, ly=ny+(Math.sin(ang)>=0.3?66:( Math.sin(ang)<=-0.3?-104:66));", "  if(Math.cos(ang)>0.5){lx=nx+64;ly=ny-21;}", "  if(Math.cos(ang)<-0.5){lx=nx-64-tw;ly=ny-21;}", "  lx=Math.max(MX-30,Math.min(lx,W-MX+30-tw));", "  ctx.fillStyle='rgba(13,20,36,0.92)';RR(lx,ly,tw,42,21);ctx.fill();", "  ctx.strokeStyle='rgba(34,211,238,0.4)';ctx.lineWidth=1.5;RR(lx,ly,tw,42,21);ctx.stroke();", "  ctx.fillStyle='#fff';ctx.textAlign='center';ctx.textBaseline='middle';", "  ctx.fillText(it.label,lx+tw/2,ly+22);", "  ctx.globalAlpha=1;", "});", "ctx.restore();"], 660)

def news_backdrop():
    el = scene(["// full-bleed backdrop — element absolute nên không chiếm flow", "ctx.save();", "// grid", "ctx.strokeStyle='rgba(120,160,255,0.045)';ctx.lineWidth=1;", "for(var gx=0;gx<=W;gx+=98){ctx.beginPath();ctx.moveTo(gx,0);ctx.lineTo(gx,H);ctx.stroke();}", "for(var gy=0;gy<=H;gy+=98){ctx.beginPath();ctx.moveTo(0,gy);ctx.lineTo(W,gy);ctx.stroke();}", "// stars (deterministic, twinkle theo time)", "var CLR=['rgba(255,255,255,','rgba(52,211,153,','rgba(96,165,250,','rgba(167,139,250,'];", "for(var i=0;i<64;i++){", "  var sx=((i*197)%(W-40))+20, sy=((i*389)%(H-40))+20;", "  var tw=0.25+0.55*Math.abs(Math.sin(time*1.4+i*1.7));", "  ctx.fillStyle=CLR[i%4]+tw+')';", "  var r=(i%7===0)?2.6:1.6;", "  ctx.beginPath();ctx.arc(sx,sy,r,0,Math.PI*2);ctx.fill();", "}", "// 2 vệt sao băng chéo mờ", "for(var k=0;k<2;k++){", "  var t=(time*0.18+k*0.5)%1;", "  var x0=W*(0.15+k*0.55)+t*260, y0=H*(0.12+k*0.6)+t*120;", "  var gd=ctx.createLinearGradient(x0,y0,x0-160,y0-70);", "  gd.addColorStop(0,'rgba(148,163,255,'+(0.35*(1-t))+')');gd.addColorStop(1,'rgba(148,163,255,0)');", "  ctx.strokeStyle=gd;ctx.lineWidth=2;", "  ctx.beginPath();ctx.moveTo(x0,y0);ctx.lineTo(x0-160,y0-70);ctx.stroke();", "}", "ctx.restore();"], 10)
    el["x_9_16"] = 0.0; el["y_9_16"] = 0.0; el["x_16_9"] = 0.0; el["y_16_9"] = 0.0; return el

def breaking_pill(label="BREAKING · 2026.07"):
    safe = label.replace("'", "\\'")
    return scene(["var cy=cursorY+52;", "ctx.save();", "var txt='" + safe + "'.toUpperCase().split('').join('\\u200a');", "var pf=30;ctx.font='bold '+pf+'px Consolas';", "// thu nhỏ chữ nếu pill sắp tràn mép", "while(ctx.measureText(txt).width+118>W-MX*2&&pf>20){pf-=2;ctx.font='bold '+pf+'px Consolas';}", "var tw=ctx.measureText(txt).width+118;", "var x=W/2-tw/2;", "var ap=EB(CL(P*2.2));", "ctx.globalAlpha=Math.min(1,P*3);", "ctx.save();ctx.translate(W/2,cy);ctx.scale(ap,1);ctx.translate(-W/2,-cy);", "ctx.strokeStyle='rgba(140,170,255,0.55)';ctx.lineWidth=2.5;", "RR(x,cy-34,tw,68,34);ctx.stroke();", "ctx.fillStyle='rgba(20,28,58,0.55)';RR(x,cy-34,tw,68,34);ctx.fill();", "// chấm xanh nhấp nháy", "var blink=0.5+0.5*Math.sin(time*4.5);", "ctx.fillStyle='rgba(52,211,153,'+(0.5+0.5*blink)+')';", "ctx.shadowColor='#34d399';ctx.shadowBlur=12*blink;", "ctx.beginPath();ctx.arc(x+40,cy,8,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;", "ctx.fillStyle='#dbe3ff';ctx.textAlign='left';ctx.textBaseline='middle';", "ctx.fillText(txt,x+66,cy+2);", "ctx.restore();ctx.restore();"], 110)

def gradient_title(lines, struck=None, size=118, c1="#5b7cfa", c2="#22d3ee"):
    payload = json.dumps(lines if isinstance(lines, list) else [lines], ensure_ascii=False); struck_js = []; extra_h = 0
    if struck:
        extra_h = 96
        struck_js = ["// chữ cũ bị gạch đỏ", "var sp2=CL(P*2.4);", "ctx.globalAlpha=Math.min(1,sp2*2);", "var st='" + struck.replace("'", "\\'") + "'.toUpperCase().split('').join('\\u200a');", "ctx.font='bold 46px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';", "var sg=ctx.createLinearGradient(W/2-160,0,W/2+160,0);", "sg.addColorStop(0,'#4a6cf7');sg.addColorStop(1,'#38bdf8');", "ctx.fillStyle=sg;ctx.globalAlpha=0.75*Math.min(1,sp2*2);", "ctx.fillText(st,W/2,y);", "var sw=ctx.measureText(st).width;", "// slash đỏ quét qua theo P", "var slp=CL(P*2.2-0.35);", "if(slp>0){ctx.strokeStyle='rgba(239,68,68,0.95)';ctx.lineWidth=7;ctx.lineCap='round';", "  ctx.shadowColor='#ef4444';ctx.shadowBlur=10;", "  ctx.save();ctx.translate(W/2,y);ctx.rotate(-0.09);", "  ctx.beginPath();ctx.moveTo(-sw/2-26,10);ctx.lineTo((-sw/2-26)+(sw+52)*slp,10-14*slp);ctx.stroke();", "  ctx.restore();ctx.shadowBlur=0;}", "ctx.globalAlpha=1;", "y+=96;"]
    return scene(["var LINES=" + payload + ";", "var fs=" + str(size) + ";", "var y=cursorY+58;", "ctx.save();"] + struck_js + ["// các dòng gradient lớn", "LINES.forEach(function(ln,li){", "  var txt=String(ln).toUpperCase();", "  var chars=txt.split('');", "  var f=fs;", "  ctx.font='bold '+f+'px sans-serif';", "  var track=Math.round(f*0.10);", "  function totalW(){var s=0;chars.forEach(function(c){s+=ctx.measureText(c).width+track;});return s-track;}", "  while(totalW()>W-MX*2-20&&f>44){f-=6;ctx.font='bold '+f+'px sans-serif';}", "  var tw=totalW(), x=W/2-tw/2;", "  var grad=ctx.createLinearGradient(x,0,x+tw,0);", "  grad.addColorStop(0,'" + c1 + "');grad.addColorStop(0.55,'" + c2 + "');grad.addColorStop(1,'#a78bfa');", "  var ly=y+f*0.62+li*(f*1.22);", "  ctx.textAlign='left';ctx.textBaseline='alphabetic';", "  var cx2=x;", "  chars.forEach(function(c,ci){", "    var cp=CL(P*2.2-(li*chars.length+ci)*0.045);", "    if(cp>0){", "      ctx.save();ctx.globalAlpha=Math.min(1,cp*1.8);", "      ctx.translate(0,(1-EZ(cp))*26);", "      ctx.shadowColor='rgba(80,140,255,0.85)';ctx.shadowBlur=cp>=1?26:0;", "      ctx.fillStyle=grad;ctx.fillText(c,cx2,ly);", "      ctx.restore();}", "    cx2+=ctx.measureText(c).width+track;", "  });", "});", "ctx.restore();"], extra_h + 40 + int(size * 1.28 * (len(lines) if isinstance(lines, list) else 1)) + 30)

def merge_nodes(left="ChatGPT", right="Codex", caption="chính thức hợp nhất"):
    l = left.replace("'", "\\'"); r = right.replace("'", "\\'"); cap = caption.replace("'", "\\'")
    return scene(["var cy=cursorY+70;", "ctx.save();", "// đường ngang", "var lw2=W*0.42;", "ctx.strokeStyle='rgba(140,170,255,0.4)';ctx.lineWidth=3;", "ctx.beginPath();ctx.moveTo(W/2-lw2/2,cy);ctx.lineTo(W/2+lw2/2,cy);ctx.stroke();", "// phần line xanh phải sáng dần", "var mp=EZ(CL(P*1.5));", "var grd=ctx.createLinearGradient(W/2,cy,W/2+lw2/2,cy);", "grd.addColorStop(0,'rgba(52,211,153,0)');grd.addColorStop(1,'rgba(52,211,153,0.95)');", "ctx.strokeStyle=grd;ctx.lineWidth=4;", "ctx.beginPath();ctx.moveTo(W/2,cy);ctx.lineTo(W/2+lw2/2*mp,cy);ctx.stroke();", "// 2 vòng tròn trượt lại gần nhau", "var gap=(1-mp)*170+62;", "var r1x=W/2-gap/2, r2x=W/2+gap/2;", "ctx.strokeStyle='rgba(96,165,250,0.8)';ctx.lineWidth=3.5;", "ctx.beginPath();ctx.arc(r1x,cy,40,0,Math.PI*2);ctx.stroke();", "ctx.strokeStyle='#34d399';ctx.lineWidth=4;", "ctx.shadowColor='#34d399';ctx.shadowBlur=18+8*Math.sin(time*3);", "ctx.beginPath();ctx.arc(r2x,cy,46,0,Math.PI*2);ctx.stroke();ctx.shadowBlur=0;", "// chữ 'L x R' gradient", "var t2='" + l + " x " + r + "';", "ctx.font='bold 58px Consolas';", "var chars=t2.split(''), track=6;", "var tw=0;chars.forEach(function(c){tw+=ctx.measureText(c).width+track;});tw-=track;", "var gx=W/2-tw/2;", "var gr2=ctx.createLinearGradient(gx,0,gx+tw,0);", "gr2.addColorStop(0,'#38bdf8');gr2.addColorStop(1,'#a78bfa');", "ctx.textAlign='left';ctx.textBaseline='middle';", "var ap2=CL(P*2-0.5);ctx.globalAlpha=ap2;", "var cx3=gx;chars.forEach(function(c){ctx.fillStyle=gr2;ctx.fillText(c,cx3,cy+112);cx3+=ctx.measureText(c).width+track;});", "// caption trắng đậm lớn", "ctx.globalAlpha=CL(P*2-0.9);", "ctx.fillStyle='#f2f6ff';ctx.font='bold 76px sans-serif';ctx.textAlign='center';", "ctx.shadowColor='rgba(150,190,255,0.6)';ctx.shadowBlur=22;", "ctx.fillText('" + cap + "',W/2,cy+226);ctx.shadowBlur=0;", "ctx.globalAlpha=1;ctx.restore();"], 360)

def node_line(items, done=99):
    payload = json.dumps(items, ensure_ascii=False)
    return scene(["var ITEMS=" + payload + ";", "var n=ITEMS.length, cy=cursorY+96;", "var x0=MX+64, x1=W-MX-64, step=(x1-x0)/Math.max(1,n-1);", "var DONE=" + str(done) + ";", "ctx.save();", "ctx.strokeStyle='rgba(140,170,255,0.35)';ctx.lineWidth=3;", "ctx.beginPath();ctx.moveTo(x0,cy);ctx.lineTo(x1,cy);ctx.stroke();", "var lit=CL(P*1.25);", "var gl=ctx.createLinearGradient(x0,cy,x1,cy);", "gl.addColorStop(0,'#38bdf8');gl.addColorStop(1,'#34d399');", "ctx.strokeStyle=gl;ctx.lineWidth=4;ctx.shadowColor='#38bdf8';ctx.shadowBlur=8;", "ctx.beginPath();ctx.moveTo(x0,cy);ctx.lineTo(x0+(x1-x0)*lit,cy);ctx.stroke();ctx.shadowBlur=0;", "ITEMS.forEach(function(it,i){", "  var t=n===1?0:i/(n-1);", "  var nx=x0+step*i, on=lit>=t-0.02&&i<DONE;", "  var ap=EB(CL(P*2.4-i*0.35));if(ap<=0)return;", "  ctx.save();ctx.translate(nx,cy);ctx.scale(ap,ap);", "  ctx.fillStyle='rgba(10,16,34,0.95)';", "  ctx.beginPath();ctx.arc(0,0,34,0,Math.PI*2);ctx.fill();", "  ctx.strokeStyle=on?'#34d399':'rgba(140,170,255,0.5)';ctx.lineWidth=3;", "  if(on){ctx.shadowColor='#34d399';ctx.shadowBlur=14;}", "  ctx.beginPath();ctx.arc(0,0,34,0,Math.PI*2);ctx.stroke();ctx.shadowBlur=0;", "  ctx.font='30px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';", "  ctx.fillText(it.icon||String(i+1),0,1);", "  ctx.restore();", "  // label mono so le trên/dưới", "  ctx.globalAlpha=Math.min(1,ap);", "  ctx.font='bold 23px Consolas';", "  var lb=it.label, lw3=ctx.measureText(lb).width+30;", "  var lx=Math.max(MX-24,Math.min(nx-lw3/2,W-MX+24-lw3));", "  var ly=(i%2===0)?cy-98:cy+62;", "  ctx.fillStyle='rgba(16,24,48,0.92)';RR(lx,ly,lw3,44,10);ctx.fill();", "  ctx.strokeStyle=on?'rgba(52,211,153,0.5)':'rgba(140,170,255,0.35)';ctx.lineWidth=1.5;RR(lx,ly,lw3,44,10);ctx.stroke();", "  ctx.fillStyle=on?'#d9fbe9':'#dbe3ff';ctx.textAlign='center';ctx.textBaseline='middle';", "  ctx.fillText(lb,lx+lw3/2,ly+23);", "  ctx.globalAlpha=1;", "});", "ctx.restore();"], 220)

def announce_block(lines, header="ANNOUNCEMENT"):
    payload = json.dumps(
        [[[t, c] for t, c in ln] for ln in lines], ensure_ascii=False
    )
    h = 96 + len(lines) * 52 + 20
    return scene(["var LINES=" + payload + ";", "var COLS={w:'#eef2ff',cyan:'#38bdf8',green:'#34d399',purple:'#a78bfa',mut:'rgba(200,212,255,0.55)'};", "var y=cursorY+34;", "ctx.save();", "// header // NAME letterspaced", "var hd=('// ' + '" + header.replace("'", "\\'") + "').toUpperCase().split('').join('\\u200a');", "ctx.globalAlpha=CL(P*3);", "ctx.font='bold 26px Consolas';ctx.textAlign='center';ctx.textBaseline='middle';", "ctx.fillStyle='rgba(160,178,230,0.75)';ctx.fillText(hd,W/2,y);", "ctx.strokeStyle='rgba(140,170,255,0.25)';ctx.lineWidth=1.5;", "var hw=ctx.measureText(hd).width;", "ctx.beginPath();ctx.moveTo(W/2-hw/2-70,y);ctx.lineTo(W/2-hw/2-20,y);", "ctx.moveTo(W/2+hw/2+20,y);ctx.lineTo(W/2+hw/2+70,y);ctx.stroke();", "ctx.globalAlpha=1;", "// các dòng nội dung, segment màu", "for(var li=0;li<LINES.length;li++){", "  var lp=CL(P*2.6-0.4-li*0.4);if(lp<=0)continue;", "  var ly=y+72+li*52;", "  ctx.font='bold 33px sans-serif';", "  var tw=0;LINES[li].forEach(function(s){tw+=ctx.measureText(s[0]).width;});", "  var x=W/2-tw/2;", "  ctx.globalAlpha=Math.min(1,lp*1.6);", "  ctx.save();ctx.translate(0,(1-EZ(lp))*24);", "  ctx.textAlign='left';", "  LINES[li].forEach(function(s){", "    ctx.fillStyle=COLS[s[1]]||COLS.w;ctx.fillText(s[0],x,ly);", "    x+=ctx.measureText(s[0]).width;});", "  ctx.restore();ctx.globalAlpha=1;", "}", "ctx.restore();"], h)
    
def breaking_news(label="BREAKING · 2026.07", struck="TIN CŨ", word="TIN CÔNG NGHỆ", left="A", right="B", caption="chính thức hợp nhất"):
    bg = news_backdrop(); pill = breaking_pill(label); title = gradient_title([word], struck=struck, size=96); merge = merge_nodes(left, right, caption); off_title = 118; off_merge = off_title + title["height"] - 26; total = off_merge + merge["height"]
    def iife(code, offset):
        return "(function(cursorY){" + code + "})(cursorY+" + str(int(offset)) + ");"
    
    code = "(function(cursorY){" + bg["code"] + "})(0);" + iife(pill["code"], 0) + iife(title["code"], off_title) + iife(merge["code"], off_merge)
    return {"type": "custom_js", "code": code, "height": int(total)}

GLASS = "function GC(x,y,w,h,r){ctx.save();ctx.shadowColor='rgba(0,0,0,0.5)';ctx.shadowBlur=34;ctx.shadowOffsetY=10;ctx.fillStyle='rgba(22,20,45,0.55)';RR(x,y,w,h,r);ctx.fill();ctx.restore();ctx.fillStyle='rgba(255,255,255,0.055)';RR(x,y,w,h,r);ctx.fill();ctx.strokeStyle='rgba(255,255,255,0.20)';ctx.lineWidth=1.6;RR(x,y,w,h,r);ctx.stroke();var sh=ctx.createLinearGradient(0,y,0,y+h*0.5);sh.addColorStop(0,'rgba(255,255,255,0.10)');sh.addColorStop(1,'rgba(255,255,255,0)');ctx.save();RR(x,y,w,h,r);ctx.clip();ctx.fillStyle=sh;ctx.fillRect(x,y,w,h*0.5);ctx.restore();}"
def cosmic_backdrop():
    el = scene(["ctx.save();", "// các đám tinh vân — blob gradient lớn xoay chậm", "var BLOBS=[[0.24,0.20,520,'168,120,255',0.20],[0.80,0.38,460,'96,120,255',0.16],", "  [0.50,0.60,600,'216,96,220',0.13],[0.18,0.82,420,'80,160,255',0.14],[0.86,0.88,380,'190,90,255',0.12]];", "BLOBS.forEach(function(b,i){", "  var wob=Math.sin(time*0.22+i*1.9);", "  var bx=b[0]*W+wob*26, by=b[1]*H+Math.cos(time*0.18+i)*20;", "  var g=ctx.createRadialGradient(bx,by,0,bx,by,b[2]);", "  g.addColorStop(0,'rgba('+b[3]+','+(b[4]+0.04*wob)+')');", "  g.addColorStop(0.6,'rgba('+b[3]+','+(b[4]*0.4)+')');", "  g.addColorStop(1,'rgba('+b[3]+',0)');", "  ctx.fillStyle=g;ctx.beginPath();ctx.arc(bx,by,b[2],0,Math.PI*2);ctx.fill();});", "// sao: nhiều tầng, lấp lánh", "for(var i=0;i<130;i++){", "  var sx=((i*197)%(W));var sy=((i*389)%(H));", "  var tw=0.2+0.65*Math.abs(Math.sin(time*1.1+i*2.3));", "  var big=i%13===0;", "  ctx.fillStyle=['rgba(255,255,255,','rgba(255,214,165,','rgba(165,196,255,','rgba(255,170,220,'][i%4]+tw+')';", "  ctx.beginPath();ctx.arc(sx,sy,big?2.8:1.4,0,Math.PI*2);ctx.fill();", "  if(big){ctx.strokeStyle='rgba(255,255,255,'+(tw*0.55)+')';ctx.lineWidth=1;", "    ctx.beginPath();ctx.moveTo(sx-9,sy);ctx.lineTo(sx+9,sy);ctx.moveTo(sx,sy-9);ctx.lineTo(sx,sy+9);ctx.stroke();}", "}", "ctx.restore();"], 10)
    el["x_9_16"] = 0.0; el["y_9_16"] = 0.0; el["x_16_9"] = 0.0; el["y_16_9"] = 0.0; return el

def hotlist_board(big="AI HOT LIST", pill="AI HOTLIST", head="🔥", items=None):
    items = (items or [])[:5]
    payload = json.dumps(items, ensure_ascii=False)
    n = max(1, len(items))
    h = 328 + n * 100 + 46
    return scene([GLASS, "var ITEMS=" + payload + ";", "var cw=W-MX*2-40, x=W/2-cw/2, y=cursorY+8;", "var ch=" + str(h - 16) + ";", "var ap=EB(CL(P*1.8));", "ctx.save();ctx.translate(W/2,y+ch/2);ctx.scale(ap,ap);ctx.translate(-(W/2),-(y+ch/2));", "GC(x,y,cw,ch,40);", "// đầu thẻ: lửa + tiêu đề + pill", "ctx.font='72px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';", "ctx.fillText('" + head + "',W/2,y+86);", "ctx.fillStyle='#f4f7ff';ctx.font='bold 64px sans-serif';", "ctx.shadowColor='rgba(150,180,255,0.8)';ctx.shadowBlur=26;", "ctx.fillText('" + big.replace("'", "\\'") + "',W/2,y+176);ctx.shadowBlur=0;", "var pt='" + pill.replace("'", "\\'") + "'.toUpperCase().split('').join('\\u200a');",
    
    "ctx.font='bold 25px Consolas';", "var pw=ctx.measureText(pt).width+64;", "ctx.fillStyle='rgba(10,12,30,0.75)';RR(W/2-pw/2,y+222,pw,52,26);ctx.fill();", "ctx.strokeStyle='rgba(255,255,255,0.3)';ctx.lineWidth=1.4;RR(W/2-pw/2,y+222,pw,52,26);ctx.stroke();",
    
    "ctx.fillStyle='#e8edff';ctx.fillText(pt,W/2,y+249);", "// các dòng TOP", "ITEMS.forEach(function(it,i){", "  var rp=CL(P*2.6-0.4-i*0.28);if(rp<=0)return;", "  var ry=y+300+i*100;", "  var slide=(1-EZ(rp))*70;", "  ctx.globalAlpha=Math.min(1,rp*1.5);", "  ctx.fillStyle='rgba(10,14,36,0.6)';RR(x+34+slide,ry,cw-68,84,14);ctx.fill();", "  ctx.strokeStyle='rgba(255,255,255,0.13)';ctx.lineWidth=1.2;RR(x+34+slide,ry,cw-68,84,14);ctx.stroke();", "  // thanh accent xanh trái", "  ctx.fillStyle='#5b9dff';RR(x+34+slide,ry+16,7,52,4);ctx.fill();", "  ctx.fillStyle='#ffffff';ctx.font='bold 33px sans-serif';ctx.textAlign='left';", "  ctx.fillText('TOP'+(i+1),x+66+slide,ry+43);", "  ctx.font='27px sans-serif';ctx.fillStyle='rgba(238,242,255,0.94)';", "  ctx.fillText(it.name+'  ·  '+it.desc,x+196+slide,ry+43);", "  ctx.globalAlpha=1;", "});", "ctx.restore();"], h)

def rank_card(rank, name, desc, metric=0, metric_label="github", accent="#ef4444"):
    return scene([GLASS, "var cw=W-MX*2-120, x=W/2-cw/2, y=cursorY+14, ch=560;", "var ap=EB(CL(P*1.8));", "ctx.save();ctx.translate(W/2,y+ch/2);ctx.scale(ap,ap);ctx.translate(-(W/2),-(y+ch/2));", "GC(x,y,cw,ch,36);", "// badge hạng đỏ", "ctx.font='bold 30px sans-serif';", "var bt='#" + str(rank) + "';var lt='  HẠNG " + str(rank) + "';", "var bw=ctx.measureText(bt).width+34;", "var ltw=ctx.measureText(lt).width;", "var totalW=bw+ltw;", "var bx=W/2-totalW/2;", "ctx.fillStyle='" + accent + "';RR(bx,y+56,bw,46,10);ctx.fill();", "ctx.fillStyle='#fff';ctx.textAlign='center';ctx.textBaseline='middle';", "ctx.fillText(bt,bx+bw/2,y+80);", "ctx.fillStyle='" + accent + "';ctx.textAlign='left';", "ctx.fillText(lt,bx+bw,y+80);", "// tên lớn", "ctx.textAlign='center';ctx.fillStyle='#ffffff';", "var nm='" + name.replace("'", "\\'") + "';", "var nf=76;ctx.font='bold '+nf+'px sans-serif';", "while(ctx.measureText(nm).width>cw-80&&nf>40){nf-=4;ctx.font='bold '+nf+'px sans-serif';}", "ctx.shadowColor='rgba(160,190,255,0.75)';ctx.shadowBlur=24;", "ctx.fillText(nm,W/2,y+188);ctx.shadowBlur=0;", "// mô tả", "ctx.fillStyle='rgba(235,240,255,0.85)';ctx.font='31px sans-serif';", "var dl=wrapText('" + desc.replace("'", "\\'") + "',cw-90,'31px sans-serif');", "dl.slice(0,2).forEach(function(l,i){ctx.fillText(l,W/2,y+252+i*42);});", "// 🔥 + số đếm tăng", "var val=Math.round(" + str(int(metric)) + "*CL(P*1.5));", "var vs='+'+String(val).replace(/\\B(?=(\\d{3})+(?!\\d))/g,',');",
    
    "ctx.font='40px sans-serif';", "var fw=ctx.measureText('🔥 ').width;", "ctx.font='bold 52px sans-serif';", "var vw=ctx.measureText(vs).width;",
    
    "var sx0=W/2-(fw+vw)/2;", "ctx.font='40px sans-serif';ctx.textAlign='left';", "ctx.fillText('🔥',sx0,y+378);", "ctx.fillStyle='#ffffff';ctx.font='bold 52px sans-serif';", "ctx.fillText(vs,sx0+fw,y+378);", "ctx.textAlign='center';ctx.fillStyle='rgba(220,228,255,0.55)';ctx.font='24px sans-serif';", "ctx.fillText('" + metric_label.replace("'", "\\'") + "',W/2,y+424);", "// progress line", "ctx.fillStyle='rgba(255,255,255,0.18)';RR(x+120,y+474,cw-240,7,4);ctx.fill();", "ctx.fillStyle='rgba(255,255,255,0.85)';RR(x+120,y+474,(cw-240)*CL(P*1.4),7,4);ctx.fill();", "ctx.restore();"], 600)

def glass_list(title, rows):
    payload = json.dumps(rows, ensure_ascii=False); n = max(1, len(rows)); h = 150 + n * 86 + 34
    return scene([GLASS, "var ROWS=" + payload + ";", "var cw=W-MX*2-70, x=W/2-cw/2, y=cursorY+10, ch=" + str(h - 22) + ";", "var ap=EB(CL(P*1.9));", "ctx.save();ctx.translate(W/2,y+ch/2);ctx.scale(ap,ap);ctx.translate(-(W/2),-(y+ch/2));", "GC(x,y,cw,ch,32);", "ctx.fillStyle='#f2f5ff';ctx.font='bold 36px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';", "ctx.shadowColor='rgba(150,180,255,0.6)';ctx.shadowBlur=16;", "ctx.fillText('" + title.replace("'", "\\'") + "',W/2,y+62);ctx.shadowBlur=0;", "ctx.strokeStyle='rgba(255,255,255,0.16)';ctx.lineWidth=1.2;", "ctx.beginPath();ctx.moveTo(x+50,y+102);ctx.lineTo(x+cw-50,y+102);ctx.stroke();", "ROWS.forEach(function(r,i){", "  var rp=CL(P*2.6-0.3-i*0.3);if(rp<=0)return;", "  var ry=y+128+i*86;", "  ctx.globalAlpha=Math.min(1,rp*1.5);", "  var slide=(1-EZ(rp))*46;", "  ctx.font='36px sans-serif';ctx.textAlign='left';", "  ctx.fillText(r.icon||'•',x+44+slide,ry+30);", "  ctx.fillStyle='rgba(240,244,255,0.95)';ctx.font='bold 29px sans-serif';", "  ctx.fillText(r.label,x+106+slide,ry+30);", "  if(r.value){ctx.textAlign='right';", "    ctx.fillStyle=['#5eead4','#93c5fd','#fbbf24','#f0abfc','#86efac'][i%5];", "    ctx.font='bold 27px sans-serif';ctx.fillText(r.value,x+cw-44,ry+30);}", "  ctx.globalAlpha=1;", "});", "ctx.restore();"], h)

def glass_duel(lname, ltag, rname, rtag, verdict=""):
    v_js = []
    if verdict:
        v_js = ["var vp=CL(P*2.2-0.8);ctx.globalAlpha=vp;", "ctx.font='bold 28px sans-serif';", "var vt='" + verdict.replace("'", "\\'") + "';", "var vw2=ctx.measureText(vt).width+70;", "ctx.fillStyle='rgba(12,14,34,0.8)';RR(W/2-vw2/2,cy+ch2/2+34,vw2,56,28);ctx.fill();", "ctx.strokeStyle='rgba(251,191,36,0.55)';ctx.lineWidth=1.5;RR(W/2-vw2/2,cy+ch2/2+34,vw2,56,28);ctx.stroke();", "ctx.fillStyle='#fbbf24';ctx.textAlign='center';ctx.textBaseline='middle';", "ctx.fillText(vt,W/2,cy+ch2/2+63);ctx.globalAlpha=1;"]
    return scene([GLASS, "var cw2=(W-MX*2-130)/2, ch2=300, cy=cursorY+175;", "var lx=W/2-cw2-42, rx=W/2+42;", "var sl=EB(CL(P*1.8));", "// thẻ trái", "ctx.save();ctx.translate(-(1-sl)*280,0);", "GC(lx,cy-ch2/2,cw2,ch2,26);", "ctx.fillStyle='#ffffff';ctx.font='bold 44px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';", "ctx.fillText('" + lname.replace("'", "\\'") + "',lx+cw2/2,cy-36);", "ctx.fillStyle='rgba(147,197,253,0.92)';ctx.font='26px sans-serif';", "wrapText('" + ltag.replace("'", "\\'") + "',cw2-44,'26px sans-serif').slice(0,2).forEach(function(l,i){", "  ctx.fillText(l,lx+cw2/2,cy+30+i*36);});", "ctx.restore();", "// thẻ phải", "ctx.save();ctx.translate((1-sl)*280,0);", "GC(rx,cy-ch2/2,cw2,ch2,26);", "ctx.fillStyle='#ffffff';ctx.font='bold 44px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';", "ctx.fillText('" + rname.replace("'", "\\'") + "',rx+cw2/2,cy-36);", "ctx.fillStyle='rgba(240,171,252,0.92)';ctx.font='26px sans-serif';", "wrapText('" + rtag.replace("'", "\\'") + "',cw2-44,'26px sans-serif').slice(0,2).forEach(function(l,i){", "  ctx.fillText(l,rx+cw2/2,cy+30+i*36);});", "ctx.restore();", "// VS lửa giữa", "var vp2=EB(CL(P*2.2-0.5));", "if(vp2>0){ctx.save();ctx.translate(W/2,cy);ctx.scale(vp2,vp2);", "ctx.font='52px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';", "ctx.fillText('🔥',0,-24);", "ctx.fillStyle='#ffffff';ctx.font='bold 40px sans-serif';", "ctx.shadowColor='rgba(255,120,80,0.9)';ctx.shadowBlur=18;", "ctx.fillText('VS',0,34);ctx.shadowBlur=0;ctx.restore();}"] + v_js, 470)

def cosmic_caption(segments):
    payload = json.dumps([[t, c] for t, c in segments], ensure_ascii=False)
    return scene(["var SEGS=" + payload + ";", "var COLS={purple:'#a78bfa',red:'#f87171',orange:'#fbbf24',cyan:'#38bdf8',green:'#34d399',white:'#f4f7ff'};", "var y=cursorY+66;", "ctx.font='bold 46px sans-serif';ctx.textBaseline='middle';", "var tw=0;SEGS.forEach(function(s){tw+=ctx.measureText(s[0]).width;});", "var x=W/2-tw/2;", "SEGS.forEach(function(s,i){", "  var sp=CL(P*2.4-i*0.35);", "  if(sp>0){", "    ctx.save();ctx.globalAlpha=Math.min(1,sp*1.7);", "    ctx.translate(0,(1-EZ(sp))*30);", "    ctx.fillStyle=COLS[s[1]]||COLS.white;", "    ctx.shadowColor=COLS[s[1]]||COLS.white;ctx.shadowBlur=sp>=1?20:0;", "    ctx.textAlign='left';ctx.fillText(s[0],x,y);", "    ctx.restore();}", "  x+=ctx.measureText(s[0]).width;", "});"], 130)
    
def light_backdrop():
    el = scene(["ctx.save();", "// nền giấy sáng gradient dọc", "var bg=ctx.createLinearGradient(0,0,0,H);", "bg.addColorStop(0,'#fdfdff');bg.addColorStop(0.5,'#f3f6ff');bg.addColorStop(1,'#edf0fb');", "ctx.fillStyle=bg;ctx.fillRect(0,0,W,H);", "// mesh blobs pastel trôi chậm", "var BL=[[0.15,0.12,430,'191,219,254',0.55],[0.85,0.24,390,'221,214,254',0.50],[0.50,0.55,540,'251,207,232',0.34],[0.18,0.85,410,'187,247,208',0.40],[0.88,0.80,370,'254,215,170',0.34]];", "BL.forEach(function(b,i){var wob=Math.sin(time*0.2+i*2.1);", "  var bx=b[0]*W+wob*30, by=b[1]*H+Math.cos(time*0.16+i)*24;", "  var g=ctx.createRadialGradient(bx,by,0,bx,by,b[2]);", "  g.addColorStop(0,'rgba('+b[3]+','+b[4]+')');g.addColorStop(1,'rgba('+b[3]+',0)');", "  ctx.fillStyle=g;ctx.beginPath();ctx.arc(bx,by,b[2],0,Math.PI*2);ctx.fill();});", "// bokeh nổi nhẹ", "for(var i=0;i<24;i++){var bx2=((i*233)%W);var by2=(((i*541)%H)+time*10)%H;", "  var fl=0.05+0.09*Math.abs(Math.sin(time*0.7+i*1.3));", "  var r=(i%5===0)?24:(i%3===0?13:7);", "  ctx.fillStyle='rgba(255,255,255,'+fl+')';ctx.beginPath();ctx.arc(bx2,by2,r,0,Math.PI*2);ctx.fill();", "  ctx.strokeStyle='rgba(148,163,216,'+(fl*0.9)+')';ctx.lineWidth=1;", "  ctx.beginPath();ctx.arc(bx2,by2,r,0,Math.PI*2);ctx.stroke();}", "// vệt sáng chéo quét chậm", "var swp=((time*0.06)%1.4)-0.2;", "var g2=ctx.createLinearGradient(W*(swp-0.18),0,W*(swp+0.18),H*0.5);", "g2.addColorStop(0,'rgba(255,255,255,0)');g2.addColorStop(0.5,'rgba(255,255,255,0.33)');g2.addColorStop(1,'rgba(255,255,255,0)');", "ctx.save();ctx.rotate(-0.18);ctx.fillStyle=g2;ctx.fillRect(-W*0.3,-H*0.2,W*1.8,H*1.6);ctx.restore();", "ctx.restore();"], 10)
    el["x_9_16"] = 0.0; el["y_9_16"] = 0.0; el["x_16_9"] = 0.0; el["y_16_9"] = 0.0; return el

def headline_card(kicker, lines, sub="", accent="#e11d48"):
    lines = [str(x) for x in (lines or ["TIÊU ĐỀ"])][:3]
    n = len(lines)
    ch = 170 + n * 100 + (60 if sub else 0) + 50
    return scene(["var ACC='" + accent.replace("'", "") + "';", "var LINES=" + json.dumps(lines, ensure_ascii=False) + ";", "var SUB='" + (sub or "").replace("'", "\\'") + "';", "var KICK='" + (kicker or "TIN MỚI").replace("'", "\\'") + "';", "var cw=W-MX*2-30, x=W/2-cw/2, y=cursorY+16, ch=" + str(ch) + ";", "var ap=EZ(CL(P*1.8));", "ctx.save();ctx.globalAlpha=Math.min(1,P*2.2);ctx.translate(0,(1-ap)*70);", "// bóng mềm + thẻ trắng kính", "ctx.save();ctx.shadowColor='rgba(30,43,74,0.16)';ctx.shadowBlur=44;ctx.shadowOffsetY=18;", "ctx.fillStyle='rgba(255,255,255,0.94)';RR(x,y,cw,ch,38);ctx.fill();ctx.restore();",
    
    "ctx.strokeStyle='rgba(30,43,74,0.08)';ctx.lineWidth=1.5;RR(x,y,cw,ch,38);ctx.stroke();", "// dải accent mảnh trên mép thẻ", "ctx.save();RR(x,y,cw,ch,38);ctx.clip();", "var tg=ctx.createLinearGradient(x,0,x+cw,0);tg.addColorStop(0,ACC);tg.addColorStop(1,'rgba(255,255,255,0)');", "ctx.fillStyle=tg;ctx.fillRect(x,y,cw,8);ctx.restore();", "// pill kicker + chấm nhấp nháy", "var kt=KICK.toUpperCase().split('').join('\\u200a');ctx.font='bold 26px Consolas';", "var kw=ctx.measureText(kt).width+86;var kx=W/2-kw/2,ky=y+46;",
    
    "ctx.fillStyle=ACC;RR(kx,ky,kw,54,27);ctx.fill();", "var blink=0.5+0.5*Math.sin(time*4);", "ctx.fillStyle='rgba(255,255,255,'+(0.6+0.4*blink)+')';ctx.beginPath();ctx.arc(kx+34,ky+27,7,0,Math.PI*2);ctx.fill();", "ctx.fillStyle='#ffffff';ctx.textAlign='left';ctx.textBaseline='middle';ctx.fillText(kt,kx+58,ky+29);", "// tiêu đề mực tối, hiện lần lượt", "ctx.textAlign='center';", "LINES.forEach(function(ln,li){", "  var rp=CL(P*2.4-0.3-li*0.35);if(rp<=0)return;", "  ctx.save();ctx.globalAlpha=Math.min(1,rp*1.6);ctx.translate(0,(1-EZ(rp))*30);", "  var f=84;ctx.font='900 '+f+'px sans-serif';", "  while(ctx.measureText(ln).width>cw-90&&f>44){f-=4;ctx.font='900 '+f+'px sans-serif';}", "  ctx.fillStyle='#0f172a';ctx.fillText(ln,W/2,y+168+li*100);", "  ctx.restore();});", "// gạch accent quét dưới tiêu đề", "var uy=y+150+LINES.length*100;var uw=(cw-260)*EZ(CL(P*1.4-0.4));", "if(uw>4){var ug=ctx.createLinearGradient(W/2-uw/2,0,W/2+uw/2,0);", "  ug.addColorStop(0,'rgba(255,255,255,0)');ug.addColorStop(0.5,ACC);ug.addColorStop(1,'rgba(255,255,255,0)');", "  ctx.fillStyle=ug;RR(W/2-uw/2,uy,uw,7,4);ctx.fill();}", "if(SUB){ctx.fillStyle='rgba(30,43,74,0.62)';ctx.font='500 31px sans-serif';ctx.fillText(SUB,W/2,uy+54);}", "ctx.restore();"], ch + 44)
    
def bento_stats(items):
    items = (items or [])[:4]
    rows = max(1, (len(items) + 1) // 2)
    h = rows * 260 + (rows - 1) * 26 + 56
    return scene(["var IT=" + json.dumps(items, ensure_ascii=False) + ";", "var ACCS=['#2563eb','#7c3aed','#059669','#ea580c'];", "var TINT=['239,246,255','245,243,255','236,253,245','255,247,237'];", "var gap=26;var cw2=(W-MX*2-30-gap)/2;var chh=260;", "var x0=W/2-(cw2*2+gap)/2;var y0=cursorY+14;", "IT.forEach(function(it,i){", "  var col=i%2,row=Math.floor(i/2);", "  var cx2=x0+col*(cw2+gap),cy2=y0+row*(chh+gap);", "  var rp=CL(P*2.4-i*0.3);if(rp<=0)return;var sc=EB(rp);", "  ctx.save();ctx.globalAlpha=Math.min(1,rp*1.6);", "  ctx.translate(cx2+cw2/2,cy2+chh/2);ctx.scale(sc,sc);ctx.translate(-(cx2+cw2/2),-(cy2+chh/2));", "  ctx.save();ctx.shadowColor='rgba(30,43,74,0.14)';ctx.shadowBlur=30;ctx.shadowOffsetY=12;", "  ctx.fillStyle='#ffffff';RR(cx2,cy2,cw2,chh,30);ctx.fill();ctx.restore();", "  ctx.fillStyle='rgba('+TINT[i%4]+',0.9)';RR(cx2,cy2,cw2,chh,30);ctx.fill();", "  ctx.strokeStyle='rgba(30,43,74,0.07)';ctx.lineWidth=1.4;RR(cx2,cy2,cw2,chh,30);ctx.stroke();", "  // icon trong squircle trắng", "  ctx.save();ctx.shadowColor='rgba(30,43,74,0.10)';ctx.shadowBlur=12;", "  ctx.fillStyle='#ffffff';RR(cx2+24,cy2+24,64,64,18);ctx.fill();ctx.restore();", "  ctx.font='34px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';", "  ctx.fillText(it.icon||'✨',cx2+56,cy2+58);", "  // số lớn đếm tăng (nếu là số)", "  var big=String(it.big||'');var m=big.match(/^([^0-9]*)([0-9][0-9.,]*)(.*)$/);var show=big;", "  if(m){var num=parseFloat(m[2].replace(/,/g,''));if(!isNaN(num)){var v=num*CL(P*1.5);", "    var dec=(m[2].indexOf('.')>=0)?1:0;", "    show=m[1]+v.toFixed(dec).replace(/\\B(?=(\\d{3})+(?!\\d))/g,',')+m[3];}}", "  ctx.fillStyle=ACCS[i%4];ctx.font='900 58px sans-serif';ctx.textAlign='left';", "  ctx.fillText(show,cx2+26,cy2+142);", "  ctx.fillStyle='rgba(30,43,74,0.66)';ctx.font='600 26px sans-serif';", "  ctx.fillText(it.label||'',cx2+26,cy2+198);", "  ctx.restore();});"], h)

def light_list(title, rows):
    rows = (rows or [])[:5]
    n = max(1, len(rows))
    head = 92 if title else 20
    h = head + n * 114 + 26
    return scene(["var TITLE='" + (title or "").replace("'", "\\'") + "';", "var ROWS=" + json.dumps(rows, ensure_ascii=False) + ";", "var ACCS=['#2563eb','#7c3aed','#059669','#ea580c','#e11d48'];", "var TINT=['239,246,255','245,243,255','236,253,245','255,247,237','255,241,242'];", "var cw=W-MX*2-40,x=W/2-cw/2,y0=cursorY+10;", "ctx.save();", "if(TITLE){ctx.fillStyle='#0f172a';ctx.font='900 44px sans-serif';", "  ctx.textAlign='center';ctx.textBaseline='middle';", "  ctx.globalAlpha=Math.min(1,P*2.5);ctx.fillText(TITLE,W/2,y0+34);ctx.globalAlpha=1;}", "var ys=y0+" + str(head) + ";", "ROWS.forEach(function(it,i){", "  var rp=CL(P*2.6-0.2-i*0.3);if(rp<=0)return;", "  var ry=ys+i*114;var slide=(1-EZ(rp))*80;", "  ctx.save();ctx.globalAlpha=Math.min(1,rp*1.6);", "  ctx.save();ctx.shadowColor='rgba(30,43,74,0.12)';ctx.shadowBlur=24;ctx.shadowOffsetY=8;", "  ctx.fillStyle='rgba(255,255,255,0.96)';RR(x+slide,ry,cw,98,24);ctx.fill();ctx.restore();", "  ctx.strokeStyle='rgba(30,43,74,0.07)';ctx.lineWidth=1.3;RR(x+slide,ry,cw,98,24);ctx.stroke();", "  // icon squircle tint", "  ctx.fillStyle='rgba('+TINT[i%5]+',1)';RR(x+slide+18,ry+17,64,64,18);ctx.fill();", "  ctx.font='32px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';", "  ctx.fillText(it.icon||'•',x+slide+50,ry+51);", "  // nhãn + phụ", "  ctx.textAlign='left';ctx.fillStyle='#0f172a';ctx.font='bold 32px sans-serif';", "  ctx.fillText(it.label||'',x+slide+104,ry+(it.sub?36:49));", "  if(it.sub){ctx.fillStyle='rgba(30,43,74,0.55)';ctx.font='500 24px sans-serif';", "    ctx.fillText(it.sub,x+slide+104,ry+70);}", "  // chip số thứ tự", "  ctx.fillStyle=ACCS[i%5];ctx.globalAlpha*=0.12;RR(x+slide+cw-76,ry+27,44,44,14);ctx.fill();", "  ctx.globalAlpha=Math.min(1,rp*1.6);ctx.fillStyle=ACCS[i%5];", "  ctx.font='900 26px sans-serif';ctx.textAlign='center';", "  ctx.fillText(String(i+1),x+slide+cw-54,ry+50);",
    
    "  ctx.restore();});", "ctx.restore();"], h)

def _tuplify_lines(lines):
    return [[(seg[0], seg[1]) for seg in ln] for ln in (lines or [])]

_TD_REGISTRY = None
_SCENE_MODULES = (
    [f"core.scenes_td_{i}" for i in range(1, 6)]
    + [f"core.scenes_wp_{i}" for i in range(1, 5)]
    + [f"core.scenes_mn_{i}" for i in range(1, 9)]
)


def _td_scenes():
    global _TD_REGISTRY
    if _TD_REGISTRY is None:
        _TD_REGISTRY = {}
        for mod in _SCENE_MODULES:
            try:
                m = __import__(mod, fromlist=["SCENES"])
                _TD_REGISTRY.update(m.SCENES)
            except Exception:
                continue
    return _TD_REGISTRY

import re as _re

_SUP = {"0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹", "+": "⁺", "-": "⁻", "−": "⁻", "=": "⁼", "(": "⁽", ")": "⁾", "a": "ᵃ", "b": "ᵇ", "c": "ᶜ", "d": "ᵈ", "e": "ᵉ", "f": "ᶠ", "g": "ᵍ", "h": "ʰ", "i": "ⁱ", "j": "ʲ", "k": "ᵏ", "l": "ˡ", "m": "ᵐ", "n": "ⁿ", "o": "ᵒ", "p": "ᵖ", "r": "ʳ",
    
    "s": "ˢ",
    "t": "ᵗ", "u": "ᵘ", "v": "ᵛ", "w": "ʷ", "x": "ˣ", "y": "ʸ", "z": "ᶻ"}
_SUB = {"0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉", "+": "₊",
    "-": "₋", "(": "₍", ")": "₎", "a": "ₐ", "e": "ₑ", "h": "ₕ",
    "i": "ᵢ", "j": "ⱼ", "k": "ₖ", "l": "ₗ", "m": "ₘ", "n": "ₙ", "o": "ₒ", "p": "ₚ", "r": "ᵣ", "s": "ₛ", "t": "ₜ", "u": "ᵤ", "v": "ᵥ", "x": "ₓ"}; _SCRIPT_PASS = {"→", " ", "'", ",", ".", "/", "°", "·"}
def _to_script(txt, table):
    out = []
    for ch in txt:
        if ch in _SCRIPT_PASS:
            out.append(ch)
            continue
        key = ch.lower() if ch.isalpha() else ch
        rep = table.get(key)
        if rep is None:
            return None
        out.append(rep)
    return "".join(out)

def mathify(s):
    if not isinstance(s, str) or not s:
        return s
    def _rep(table):
        def go(m):
            body = next(g for g in m.groups() if g is not None)
            conv = _to_script(body, table)
            if conv is None:
                return m.group(0)
            mixed = any((ch in _SCRIPT_PASS for ch in body))
            if mixed:
                return table["("] + conv + table[")"]
            elif m.group(0)[1] in "{(" or len(body) == 1:
                return conv
            
            return table["("] + conv + table[")"]
        
        return go
    
    s = _re.sub("\\\\?sqrt\\s*\\{([^{}]*)\\}", "√(\\1)", s); s = _re.sub("\\bsqrt\\s*\\(", "√(", s); s = _re.sub("\\be\\^\\{([^{}]{5,})\\}", "exp(\\1)", s); s = _re.sub("\\be\\^\\(([^()]{5,})\\)", "exp(\\1)", s); s = _re.sub("\\^\\{([^{}]+)\\}|\\^\\(([^()]+)\\)|\\^([0-9a-zA-Z+\\-−]{1,8})", _rep(_SUP), s)
    
    s = _re.sub("_\\{([^{}]+)\\}|_\\(([^()]+)\\)|_([0-9a-zA-Z+\\-−]{1,6})", _rep(_SUB), s)
    
    s = s.replace(" * ", " · ").replace("<=", "≤").replace(">=", "≥").replace("!=", "≠").replace("+-", "±").replace("+/-", "±")
    return s

def _mathify_params(v):
    if isinstance(v, str):
        return mathify(v)
    elif isinstance(v, list):
        return [_mathify_params(x) for x in v]
    elif isinstance(v, dict):
        return {k: _mathify_params(x) for k, x in v.items()}
    
    return v
    
def td_prompt_doc(prefix: str="td_") -> str:
    return "\n".join(
        m.get("doc", "")
        for name, m in _td_scenes().items()
        if name.startswith(prefix)
    )


def _scene_text(value) -> str:
    """Turn a common AI object-shaped label into bounded display text.

    Providers occasionally return component-style values such as
    ``{"text": "NGUỒN TIN", "color": "orange"}``.  Canvas scene factories
    need strings; passing that dict through eventually paints its Python/JS
    representation.  Prefer an explicit visible field, never ``str(dict)``.
    """
    if isinstance(value, dict):
        for key in ("text", "label", "name", "title", "value", "head", "word", "sub", "desc", "rule", "content", "description", "body"):
            if value.get(key) not in (None, ""):
                return _scene_text(value[key])
        # Preserve a provider's unknown-but-benign label field instead of
        # silently dropping the whole card.  Style/boolean fields are not
        # visible content and are deliberately skipped.
        for key, item in value.items():
            if key.lower() not in {"color", "icon", "active", "enabled", "seed", "columns"}:
                text = _scene_text(item)
                if text:
                    return text
        return ""
    if isinstance(value, (list, tuple)):
        return " · ".join(part for part in (_scene_text(item) for item in value) if part)
    return _safe_text(value)


def _scene_list(value) -> list:
    if isinstance(value, (list, tuple)):
        return [_scene_text(item) for item in value if _scene_text(item)]
    text = _scene_text(value)
    return [text] if text else []


def normalize_scene_params(template_name, params) -> dict:
    """Normalize benign AI aliases into each shipped scene's public schema.

    This is deliberately a data-only adapter at the trust boundary.  It does
    not accept model-authored drawing code and preserves the local scene
    factory as the sole owner of geometry.
    """
    p = sanitize_params(params)
    name = str(template_name or "").strip().lower()

    for key in ("tag", "title", "kicker", "brand", "tagline", "en", "check", "footer", "color"):
        if key in p and isinstance(p[key], (dict, list, tuple)):
            p[key] = _scene_text(p[key])

    if name == "wp_title_stack":
        p.setdefault("tag", _scene_text(p.pop("kicker", "")))
        if "title_lines" in p and "lines" not in p:
            p["lines"] = p.pop("title_lines")
        if "subtitle" in p and "subs" not in p:
            p["subs"] = p.pop("subtitle")
        if isinstance(p.get("lines"), list):
            p["lines"] = [
                {"text": _scene_text(item), "color": item.get("color", "") if isinstance(item, dict) else ""}
                for item in p["lines"] if _scene_text(item)
            ]
        if "subs" in p:
            p["subs"] = _scene_list(p["subs"])

    elif name == "wp_rules":
        if "rules" in p and "items" not in p:
            p["items"] = p.pop("rules")
        if isinstance(p.get("items"), list):
            p["items"] = [
                {
                    "lead": _scene_text(item.get("lead", item.get("text", item.get("label", item.get("rule", item.get("name", item.get("title", ""))))))) if isinstance(item, dict) else _scene_text(item),
                    "desc": _scene_text(item.get("desc", item.get("detail", item.get("sub", item.get("description", item.get("body", "")))))) if isinstance(item, dict) else "",
                }
                for item in p["items"] if _scene_text(item)
            ]

    elif name == "wp_grid" and isinstance(p.get("items"), list):
        p["items"] = [
            {"name": _scene_text(item.get("name", item.get("label", item.get("text", "")))) if isinstance(item, dict) else _scene_text(item)}
            for item in p["items"] if _scene_text(item)
        ]

    elif name == "wp_before_after":
        if not isinstance(p.get("old"), dict):
            p["old"] = {
                "head": _scene_text(p.pop("before_label", "")),
                "boxes": _scene_list(p.pop("before_items", [])),
            }
        if not isinstance(p.get("new"), dict):
            p["new"] = {
                "head": _scene_text(p.pop("after_label", "")),
                "left": _scene_list(p.pop("after_items", [])),
            }

    elif name == "wp_outro":
        if "cta_buttons" in p and "actions" not in p:
            p["actions"] = p.pop("cta_buttons")
        if isinstance(p.get("actions"), list):
            p["actions"] = [
                {
                    "label": _scene_text(item.get("label", item.get("text", ""))) if isinstance(item, dict) else _scene_text(item),
                    "icon": "" if isinstance(item, dict) and str(item.get("icon", "")).endswith("Icon") else _scene_text(item.get("icon", "")) if isinstance(item, dict) else "",
                    "color": _scene_text(item.get("color", "")) if isinstance(item, dict) else "",
                }
                for item in p["actions"] if _scene_text(item)
            ]
    return p

def has_scene(name) -> bool:
    return str(name or "").strip().lower() in _td_scenes()

def expand(template_name, params):
    """Expand a named scene template into the renderer's ``custom_js`` dict."""
    t = (template_name or "").strip().lower()
    p = normalize_scene_params(t, params)

    td = _td_scenes()
    if t in td:
        try:
            import inspect

            fn = td[t]["fn"]
            allowed = set(inspect.signature(fn).parameters)
            kwargs = {k: v for k, v in p.items() if k in allowed}
            if t.startswith("mn_"):
                kwargs = {k: _mathify_params(v) for k, v in kwargs.items()}
            return fn(**kwargs)
        except Exception:
            pass

    try:
        if t == "neon_sprite_panel":
            return neon_sprite_panel(
                p.get("sprite", "idea"),
                p.get("kicker", ""),
                p.get("title", ""),
                p.get("rows") or p.get("items") or [],
            )
        if t == "episode_ring":
            return episode_ring(int(p.get("n", 1)), int(p.get("total", 13)))
        if t == "phone_hero":
            icons = p.get("icons") or p.get("orbit_icons") or ["🛒", "📦", "🧠", "🔐"]
            return phone_hero(tuple(icons))
        if t == "code_typing":
            return code_typing(
                p.get("title", "terminal"),
                _tuplify_lines(p.get("lines", [[("...", "txt")]])),
            )
        if t == "edge_globe":
            return edge_globe(
                p.get("center", p.get("center_emoji", "⚡")),
                p.get("label", ""),
            )
        if t == "data_river":
            return data_river(
                p.get("left_emoji", "📱"),
                p.get("left_label", "APP"),
                p.get("mid_emoji", "☁️"),
                p.get("mid_label", "WORKER"),
                p.get("right_kind", "db"),
                p.get("right_label", "D1"),
                p.get("right_emoji", "📦"),
            )
        if t == "shield_wall":
            return shield_wall(
                p.get("icon", "🛡️"),
                p.get("left_label", "BOT: CHẶN"),
                p.get("right_label", "NGƯỜI THẬT: QUA"),
            )
        if t == "neuro_stream":
            return neuro_stream(p.get("answer", "Xin chào! Tôi là trợ lý AI."))
        if t == "laser_scan":
            return laser_scan(
                p.get("product", "PARA 500"),
                p.get("name", "Paracetamol 500mg"),
                p.get("price", "2.000đ / viên"),
                p.get("stock", "Tồn: 128 vỉ"),
            )
        if t == "metric_grid":
            return metric_grid(p.get("metrics") or p.get("items") or [])
        if t == "rocket_finale":
            return rocket_finale()
        if t == "forge_apk":
            return forge_apk()
        if t == "journey_path":
            return journey_path(p.get("items", []), p.get("walker", "🚶"))
        if t == "tool_dock":
            return tool_dock(p.get("tools") or p.get("items") or [])
        if t == "keycaps":
            return keycaps(p.get("word", "LÀM!"))
        if t == "stamp_done":
            return stamp_done(p.get("text", "XONG!"))
        if t == "versus_split":
            return versus_split(
                p.get("left_title", "A"),
                p.get("left_sub", ""),
                p.get("right_title", "B"),
                p.get("right_sub", ""),
                p.get("left_icon", "❌"),
                p.get("right_icon", "✅"),
            )
        if t == "web_window":
            return web_window(
                p.get("url", "localhost:3000"),
                p.get("title", ""),
                p.get("badge", "LIVE"),
                p.get("badge_color", "green"),
            )
        if t == "check_sweep":
            items = []
            for item in p.get("items", []):
                if isinstance(item, dict) and "text" in item:
                    items.append(
                        {"text": item["text"], "ok": bool(item.get("ok", True))}
                    )
                else:
                    items.append({"text": str(item), "ok": True})
            return check_sweep(items)
        if t == "style_sync":
            return style_sync(p.get("caption", "Cùng 1 phong cách"))
        if t == "big_word":
            return big_word(
                p.get("kicker", ""),
                p.get("word", "..."),
                p.get("sub", ""),
                p.get("color", "title"),
            )
        if t == "progress_map":
            return progress_map(
                int(p.get("n", 1)),
                int(p.get("total", 13)),
                p.get("done_text", ""),
                p.get("remain_text", ""),
            )
        if t == "stairs_steps":
            return stairs_steps(p.get("items", []))
        if t == "domino_flow":
            return domino_flow(p.get("items", []))
        if t == "orbit_cycle":
            return orbit_cycle(p.get("items", []), p.get("center_label", "LẶP LẠI"))
        if t == "news_backdrop":
            return news_backdrop()
        if t == "breaking_pill":
            return breaking_pill(p.get("label", "BREAKING"))
        if t == "gradient_title":
            return gradient_title(
                p.get("lines") or [p.get("word", "BREAKING")],
                p.get("struck"),
                int(p.get("size", 118)),
                p.get("c1", "#5b7cfa"),
                p.get("c2", "#22d3ee"),
            )
        if t == "merge_nodes":
            return merge_nodes(
                p.get("left", "A"),
                p.get("right", "B"),
                p.get("caption", "chính thức hợp nhất"),
            )
        if t == "node_line":
            return node_line(p.get("items", []), int(p.get("done", 99)))
        if t == "announce_block":
            return announce_block(
                _tuplify_lines(p.get("lines", [])),
                p.get("header", "ANNOUNCEMENT"),
            )
        if t == "breaking_news":
            return breaking_news(
                p.get("label", "BREAKING · 2026"),
                p.get("struck", "TIN CŨ"),
                p.get("word", "TIN CÔNG NGHỆ"),
                p.get("left", "A"),
                p.get("right", "B"),
                p.get("caption", "chính thức hợp nhất"),
            )
        if t == "cosmic_backdrop":
            return cosmic_backdrop()
        if t == "hotlist_board":
            return hotlist_board(
                p.get("big", "AI HOT LIST"),
                p.get("pill", "HOTLIST"),
                p.get("head", "🔥"),
                p.get("items", []),
            )
        if t == "rank_card":
            return rank_card(
                int(p.get("rank", 1)),
                p.get("name", "?"),
                p.get("desc", ""),
                int(p.get("metric", 0)),
                p.get("metric_label", "điểm hot"),
                p.get("accent", "#ef4444"),
            )
        if t == "glass_list":
            return glass_list(p.get("title", ""), p.get("rows", []))
        if t == "glass_duel":
            return glass_duel(
                p.get("lname", "A"),
                p.get("ltag", ""),
                p.get("rname", "B"),
                p.get("rtag", ""),
                p.get("verdict", ""),
            )
        if t == "cosmic_caption":
            segments = [
                (segment[0], segment[1])
                for segment in p.get("segments", [["...", "white"]])
            ]
            return cosmic_caption(segments)
        if t == "light_backdrop":
            return light_backdrop()
        if t == "headline_card":
            return headline_card(
                p.get("kicker", "TIN MỚI"),
                p.get("lines") or [p.get("headline", "TIÊU ĐỀ")],
                p.get("sub", ""),
                p.get("accent", "#e11d48"),
            )
        if t == "bento_stats":
            return bento_stats(p.get("items") or [])
        if t == "light_list":
            return light_list(
                p.get("title", ""),
                p.get("rows") or p.get("items") or [],
            )
        effect = _registered_effect(t)
        if effect is not None:
            return effect
    except Exception:
        return None
    return None


TEMPLATE_NAMES = ["neon_sprite_panel", "episode_ring", "phone_hero", "code_typing", "edge_globe", "data_river", "shield_wall", "neuro_stream", "laser_scan", "metric_grid", "rocket_finale", "forge_apk", "journey_path", "tool_dock", "keycaps", "stamp_done", "versus_split", "web_window", "check_sweep", "style_sync", "big_word", "progress_map", "stairs_steps", "domino_flow", "orbit_cycle", "news_backdrop", "breaking_pill", "gradient_title", "merge_nodes", "node_line", "announce_block", "breaking_news", "cosmic_backdrop", "hotlist_board", "rank_card", "glass_list", "glass_duel", "cosmic_caption", "light_backdrop", "headline_card", "bento_stats", "light_list"]


def _code_height(code: str, default: int = 520) -> int:
    match = re.search(r"\breturn\s+(\d+(?:\.\d+)?)\s*;\s*$", code or "")
    if not match:
        return default
    return max(80, min(1_500, int(float(match.group(1)))))


def _registered_effect(name: str):
    """Expose shipped effect snippets as named, declarative templates."""
    try:
        from core.effects_catalog import EFFECTS
        wanted = str(name or "").strip().lower()
        for effect in EFFECTS:
            if str(effect.get("name") or "").strip().lower() != wanted:
                continue
            code = effect.get("code")
            if isinstance(code, str) and code.strip():
                return {"type": "custom_js", "code": code, "height": _code_height(code)}
    except Exception:
        pass
    return None


def legacy_template_for_code(code: str) -> str | None:
    """Map an exact, shipped legacy effect string to its safe template name.

    This is deliberately an exact match: formatting variants or appended code
    are untrusted input, not a compatibility case.
    """
    candidate = str(code or "").strip()
    if not candidate:
        return None
    try:
        from core.effects_catalog import EFFECTS
        for effect in EFFECTS:
            source = effect.get("code")
            if isinstance(source, str) and candidate == source.strip():
                return str(effect.get("name") or "").strip().lower() or None
    except Exception:
        pass
    return None
_DEMO_ITEMS = [{"icon": "🎯", "label": "Xác định mục tiêu"},
    {"icon": "⚡", "label": "Hành động ngay"},
    {"icon": "📈", "label": "Đo lường kết quả"}]

_DEMOS = [("episode_ring", "vòng số tập + cung tiến độ series (mở bài)", {"n": 3, "total": 10}), ("big_word", "chữ lớn neon typographic — hook mở bài / khái niệm chính", {"kicker": "TẬP 3 / 10", "word": "TĂNG TỐC", "sub": "Học nhanh gấp đôi"}), ("keycaps", "phím bàn phím nhấn lần lượt (chủ đề gõ phím/hành động)", {"word": "HỌC!"}), ("stamp_done", "con dấu slam xác nhận hoàn thành", {"text": "XONG TẬP 3"}),
    
    ("progress_map", "bản đồ tiến độ series sáng dần (kết bài, thay đổi theo tập)",
    {"n": 3, "total": 10}), ("rocket_finale", "tên lửa bay lên giữa trường sao (kết series)", {}),
    ("journey_path", "hành trình dài uốn lượn có cột mốc + cờ đích",
    {"items": _DEMO_ITEMS, "walker": "🚶"}),
    
    ("stairs_steps", "cầu thang số bước đi lên (thứ tự tăng dần)",
    {"items": _DEMO_ITEMS}), ("domino_flow", "chuỗi 3 thẻ ngang nhân quả, chevron sáng dần", {"items": _DEMO_ITEMS}), ("orbit_cycle", "quy trình LẶP vòng tròn, node sáng luân phiên", {"items": _DEMO_ITEMS, "center_label": "LẶP LẠI"}), ("code_typing", "cửa sổ editor gõ code từng ký tự, syntax màu", {"title": "vi_du.ts", "lines": [[("const", "kw"), (" x = ", "txt"), ("1", "num")],
    [("// chú thích", "cm")], [("✓ chạy OK", "ok")]]}),
    ("web_window", "cửa sổ trình duyệt loading + skeleton trang", {"url": "vidu.com", "title": "Trang của bạn đã lên sóng", "badge": "LIVE", "badge_color": "green"}), ("phone_hero", "điện thoại tự dựng UI, icon bay quanh", {"icons": ["🎯", "⚡", "📈", "💡"]}),
    ("edge_globe", "địa cầu mạng lưới, gói tin bay từ tâm ra các điểm", {"center": "⚡", "label": "Phủ sóng toàn cầu"}),
    
    ("data_river", "luồng dữ liệu 3 trạm (nguồn → xử lý → kho)",
    {"left_emoji": "📱", "left_label": "NGUỒN", "mid_emoji": "⚙️", "mid_label": "XỬ LÝ", "right_kind": "db", "right_label": "KHO DỮ LIỆU"}), ("shield_wall", "lá chắn: chặn xấu bên trái, cho tốt qua bên phải", {"icon": "🛡️", "left_label": "RỦI RO: CHẶN", "right_label": "GIÁ TRỊ: QUA"}), ("neuro_stream", "não neuron phát token vào bubble chat AI gõ chữ dần", {"answer": "AI phân tích dữ liệu của bạn và trả lời theo ngữ cảnh thực tế."}), ("laser_scan", "laser quét mã vạch sản phẩm → thẻ kết quả bật ra", {"product": "SP 01", "name": "Sản phẩm mẫu", "price": "99.000đ", "stock": "Còn: 128"}),
    ("forge_apk", "file bay vào máy đóng gói rung lắc → app hoàn chỉnh",
    {}),
    ("versus_split", "2 thẻ đối đầu VS (cũ/mới, sai/đúng)",
    {"left_title": "Cách cũ", "left_sub": "chậm và tốn kém", "right_title": "Cách mới", "right_sub": "nhanh gấp ba lần", "left_icon": "🐌", "right_icon": "🚀"}),
    
    ("metric_grid",
    
    "lưới 2-4 ô số liệu đếm tăng dần",
    {"metrics": [{"icon": "📅", "v": 30, "suffix": "", "label": "ngày thử thách"},
    {"icon": "⚡", "v": 100, "suffix": "%", "label": "năng suất", "color": "green"},
    {"icon": "💰", "v": 5_000_000, "suffix": "", "label": "tiết kiệm/tháng"},
    {"icon": "🎯", "v": 12, "suffix": "", "label": "mục tiêu đạt"}]}),
    
    ("check_sweep", "checklist vẽ nét ✓/✗ từng dòng trượt vào",
    {"items": [{"text": "Chuẩn bị đầy đủ?", "ok": True},
    {"text": "Bỏ qua bước nền tảng", "ok": False},
    {"text": "Kiên trì mỗi ngày", "ok": True}]}), ("tool_dock", "2-4 tile công cụ rơi xuống + thanh cài đặt", {"tools": [{"icon": "🟢", "name": "Công cụ A", "sub": "nền tảng chính"},
    {"icon": "💙", "name": "Công cụ B", "sub": "hỗ trợ đắc lực"},
    {"icon": "🌿", "name": "Công cụ C", "sub": "miễn phí trọn đời"}]}),
    
    ("style_sync",
    
    "4 thẻ đồng bộ về một phong cách (tính nhất quán)",
    {"caption": "Đồng bộ một phong cách"}), ("news_backdrop", "nền full màn: lưới mờ + sao lấp lánh + sao băng (đặt ĐẦU elements của step)", {}), ("breaking_pill", "pill ● BREAKING chấm xanh nhấp nháy, chữ giãn ký tự", {"label": "BREAKING · CẬP NHẬT NÓNG"}),
    
    ("gradient_title", "tiêu đề gradient xanh→tím cực lớn, tuỳ chọn chữ cũ gạch đỏ phía trên",
    {"lines": ["TIN CÔNG NGHỆ"], "struck": "TIN CŨ", "size": 108}), ("merge_nodes", "2 vòng tròn hợp nhất trên 1 đường + chữ 'A x B' gradient + câu chốt", {"left": "SẢN PHẨM", "right": "AI", "caption": "chính thức hợp nhất"}), ("node_line", "dải node ngang tech, nhãn mono so le trên/dưới", {"items": _DEMO_ITEMS}), ("announce_block", "khối // ANNOUNCEMENT: header giãn ký tự + dòng nội dung tô màu từ khoá", {"lines": [[["Cập nhật ", "w"], ["quan trọng nhất", "cyan"], [" trong tháng", "w"]], [["Hiệu lực ", "w"], ["ngay hôm nay", "green"]]], "header": "ANNOUNCEMENT"}), ("breaking_news", "POSTER tin nóng hoàn chỉnh trong 1 cảnh: nền sao + pill BREAKING + gạch đỏ tin cũ + tiêu đề gradient + 2 vòng tròn hợp nhất 'A x B'", {"label": "BREAKING · 2026.07", "struck": "TIN CŨ", "word": "TIN CÔNG NGHỆ", "left": "SẢN PHẨM", "right": "AI", "caption": "chính thức ra mắt"}), ("cosmic_backdrop", "nền vũ trụ tinh vân full màn: blob nebula + sao lấp lánh + xoáy thiên hà (đặt ĐẦU elements)", {}),
    
    ("hotlist_board", "bảng xếp hạng TOP 1-5 trên thẻ kính mờ, 🔥 + tiêu đề + pill + dòng trượt vào",
    {"big": "AI HOT LIST", "pill": "HOTLIST TUẦN NÀY", "items": [{"name": "Chủ đề A", "desc": "mô tả ngắn"},
    {"name": "Chủ đề B", "desc": "mô tả ngắn"},
    {"name": "Chủ đề C", "desc": "mô tả ngắn"},
    {"name": "Chủ đề D", "desc": "mô tả ngắn"},
    {"name": "Chủ đề E", "desc": "mô tả ngắn"}]}),
    ("rank_card", "thẻ hạng đếm ngược: badge đỏ #N + tên lớn + 🔥 số đếm tăng + vạch tiến độ",
    {"rank": 3, "name": "Ứng viên", "desc": "một dòng mô tả điểm mạnh", "metric": 88_000, "metric_label": "điểm hot · BXH của kênh"}),
    
    ("glass_list", "thẻ kính danh sách chi tiết: tiêu đề + các dòng icon·label·value màu",
    {"title": "VÌ SAO ĐÁNG CHÚ Ý?", "rows": [{"icon": "⚡", "label": "Điểm mạnh nổi bật", "value": "top 1"},
    {"icon": "💡", "label": "Phù hợp với ai", "value": "người mới"},
    {"icon": "🎯", "label": "Khi nào nên dùng", "value": "hằng ngày"}]}), ("glass_duel", "2 thẻ kính đối đầu + 🔥 VS giữa + pill phán quyết", {"lname": "Phe A", "ltag": "nhanh và rẻ", "rname": "Phe B", "rtag": "sâu và chắc", "verdict": "Việc thường → A · việc khó → B"}),
    
    ("cosmic_caption", "dòng chốt đa màu neon cuối màn (segments: purple/red/orange/cyan/green/white)",
    {"segments": [["Chốt hạ ", "white"], ["cực cháy ", "orange"], ["🔥", "red"]]})]
def demo_effects():
    out = []
    for name, when, params in _DEMOS:
        el = expand(name, params)
        if not el:
            continue
        out.append({"name": name, "when": when, "code": el["code"] + "\nreturn " + str(int(el["height"])) + ";"})
    return out

PROMPT_DOC = 'episode_ring     {"n":3,"total":10}                          — vòng số tập + cung tiến độ (mở bài)\nbig_word         {"kicker":"TẬP 3","word":"TĂNG TỐC","sub":"..."} — chữ lớn neon hook\nkeycaps          {"word":"HỌC!"}                              — phím gõ lần lượt\nstamp_done       {"text":"XONG TẬP 3"}                        — con dấu slam kết bài\nprogress_map     {"n":3,"total":10,"done_text":"✓ XONG BÀI 3","remain_text":"Còn 7 bài nữa!"} — bản đồ tiến độ series (kết bài; done_text/remain_text VIẾT BẰNG NGÔN NGỮ ĐẦU RA)\nrocket_finale    {}                                           — tên lửa (chỉ tập cuối)\njourney_path     {"items":[{"icon":"🎯","label":"..."}],"walker":"🚶"} — hành trình cột mốc\nstairs_steps     {"items":[{"icon":"1️⃣","label":"..."}]}       — cầu thang thứ tự tăng\ndomino_flow      {"items":[{"icon":"🎫","label":"..."}]}       — chuỗi nhân quả 3 thẻ\norbit_cycle      {"items":[...],"center_label":"LẶP LẠI"}      — quy trình lặp vòng tròn\ncode_typing      {"title":"file.ts","lines":[[["const x=","txt"],["1","num"]]]} — editor gõ chữ (màu kw/str/fn/txt/cm/num/err/ok)\nweb_window       {"url":"...","title":"...","badge":"LIVE"}    — cửa sổ trình duyệt\nphone_hero       {"icons":["🎯","⚡"]}                          — điện thoại dựng UI\nedge_globe       {"center":"⚡","label":"..."}                  — địa cầu mạng lưới\ndata_river       {"left_label":"NGUỒN","mid_label":"XỬ LÝ","right_kind":"db|box","right_label":"KHO"} — luồng 3 trạm\nshield_wall      {"icon":"🛡️","left_label":"...","right_label":"..."} — lá chắn chặn/cho qua\nneuro_stream     {"answer":"..."}                              — não AI + bubble chat\nlaser_scan       {"product":"...","name":"...","price":"...","stock":"..."} — laser quét mã vạch\nforge_apk        {}                                            — máy đóng gói file → app\nversus_split     {"left_title":"...","left_sub":"...","right_title":"...","right_sub":"..."} — 2 thẻ VS\nmetric_grid      {"metrics":[{"icon":"⚡","v":100,"suffix":"%","label":"..."}]} — số liệu đếm tăng\ncheck_sweep      {"items":[{"text":"...","ok":true}]}          — checklist ✓/✗\ntool_dock        {"tools":[{"icon":"🟢","name":"...","sub":"..."}]} — tile công cụ rơi\nstyle_sync       {"caption":"..."}                             — 4 thẻ đồng bộ phong cách\nnews_backdrop    {}                                            — nền lưới+sao breaking news (đặt ĐẦU elements)\nbreaking_pill    {"label":"BREAKING · 2026"}                    — pill ● chấm xanh nhấp nháy\ngradient_title   {"lines":["TIN LỚN"],"struck":"TIN CŨ","size":108} — tiêu đề gradient, gạch đỏ chữ cũ\nmerge_nodes      {"left":"A","right":"B","caption":"..."}       — 2 vòng tròn hợp nhất "A x B"\nnode_line        {"items":[{"icon":"⚡","label":"..."}]}         — dải node ngang tech\nannounce_block   {"lines":[[["từ ","w"],["khoá","cyan"]]],"header":"ANNOUNCEMENT"} — khối // thông báo (màu: w/cyan/green/purple/mut)\nbreaking_news    {"label":"BREAKING","struck":"TIN CŨ","word":"TIN LỚN","left":"A","right":"B","caption":"..."} — POSTER tin nóng trọn bộ 1 cảnh\ncosmic_backdrop  {}                                            — nền vũ trụ tinh vân (đặt ĐẦU elements)\nhotlist_board    {"big":"HOT LIST","pill":"TUẦN NÀY","items":[{"name":"A","desc":"..."}×5]} — bảng TOP 1-5 thẻ kính\nrank_card        {"rank":3,"name":"...","desc":"...","metric":88000,"metric_label":"điểm hot"} — thẻ hạng + 🔥 đếm tăng\nglass_list       {"title":"...","rows":[{"icon":"⚡","label":"...","value":"..."}]} — thẻ kính chi tiết\nglass_duel       {"lname":"A","ltag":"...","rname":"B","rtag":"...","verdict":"..."} — 2 thẻ kính VS 🔥\ncosmic_caption   {"segments":[["chữ ","white"],["màu","orange"]]}  — dòng chốt neon đa màu'; i = None; i = None; i = None
