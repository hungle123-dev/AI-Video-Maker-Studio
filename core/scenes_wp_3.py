"""core/scenes_wp_3.py — Bộ scene warmpaper (nhóm 3): wp_duo_cards,
wp_layer_table. Phong cách poster tin công nghệ NỀN KEM ẤM (renderer lo nền):
chip chương màu + tiêu đề đen đậm tự chứa, card trắng bo tròn active/mờ
luân phiên, bảng đối chiếu 2 cột theo layer với dấu '≈' giữa 2 ô.
"""
import json
from core.custom_scenes import scene; ACCENT = {"orange": "#e8590c", "red": "#d9480f", "blue": "#1c7ed6", "green": "#2f9e44", "gray": "#adb5bd"}; INK = "#211a12"; GRAY = "#8a7a66"; MONO = "#b0a08c"; EDGE = "rgba(160,110,60,0.18)"; HXA = "function HXA(h,a){return 'rgba('+parseInt(h.substr(1,2),16)+','+parseInt(h.substr(3,2),16)+','+parseInt(h.substr(5,2),16)+','+a+')';}"; WPH = "function WPH(tag,title,ac){var ha=EZ(CL(P*1.8));ctx.save();ctx.textAlign='center';ctx.textBaseline='middle';ctx.globalAlpha=ha;if(tag){ctx.font='bold 30px Segoe UI, sans-serif';var tw=ctx.measureText(tag).width+44;ctx.fillStyle=HXA(ac,0.12);RR(W/2-tw/2,cursorY,tw,56,10);ctx.fill();ctx.strokeStyle=HXA(ac,0.45);ctx.lineWidth=1.5;RR(W/2-tw/2,cursorY,tw,56,10);ctx.stroke();ctx.fillStyle=ac;ctx.fillText(tag,W/2,cursorY+29);}var fs=64;ctx.font='bold '+fs+'px Segoe UI, sans-serif';while(ctx.measureText(title).width>W-160&&fs>54){fs-=2;ctx.font='bold '+fs+'px Segoe UI, sans-serif';}var tls=wrapText(title,W-160,'bold '+fs+'px Segoe UI, sans-serif').slice(0,2);ctx.fillStyle='#211a12';var ty=cursorY+84+(1-ha)*14;tls.forEach(function(l,i){ctx.fillText(l,W/2,ty+fs/2+i*(fs+8));});ctx.restore();}"
def wp_duo_cards(tag="PHÂN HOÁ", color="blue", title="Hai triết lý ngược nhau", top=None, bottom=None):
    if not top:
        top = {"name": "ANTHROPIC", "head": "Trọn gói", "sub": "hạ tầng lo hết", "rows": ["Não đóng nguồn", "Sandbox tự nhà", "Trả phí trọn gói"], "note": "như Apple", "color": "orange"}
    if not bottom:
        bottom = {"name": "OPENAI", "head": "Mở + tự chọn", "sub": "bạn chọn cloud, họ bán token", "rows": ["Mã nguồn mở", "7 sandbox tuỳ chọn", "Trả theo token"], "note": "như Android", "color": "blue"}
    def norm(c, defc):
        rows = c.get("rows") or []
        return {
            "name": str(c.get("name", "")),
            "head": str(c.get("head", "")),
            "sub": str(c.get("sub", "")),
            "rows": [str(r) for r in rows][:3],
            "note": str(c.get("note", "")),
            "c": ACCENT.get(c.get("color", defc), ACCENT["orange"]),
        }
    
    payload = json.dumps([norm(top, "orange"), norm(bottom, "blue")], ensure_ascii=False); acc = ACCENT.get(color, ACCENT["blue"])
    return scene([HXA, WPH, "var CARDS=" + payload + ";", "var TAG=" + json.dumps(tag, ensure_ascii=False) + ";", "var TITLE=" + json.dumps(title, ensure_ascii=False) + ";",
    
    "var AC=" + json.dumps(acc) + ";", "WPH(TAG,TITLE,AC);", "var bx=70,bw=W-140,chh=540,gap=20,base=cursorY+230;", "/* card active luân phiên theo time, 2.5s đổi một lần */", "var act=Math.floor(time/2.5)%2;", "ctx.save();ctx.textAlign='center';ctx.textBaseline='middle';", "CARDS.forEach(function(c,i){", "  var e=EZ(CL(P*2-0.3-i*0.35));if(e<=0)return;", "  var y=base+i*(chh+gap)+(1-e)*26;", "  var on=(act===i);", "  /* vỏ card: active nền trắng .92, inactive nền trắng .45 */", "  ctx.globalAlpha=e;", "  ctx.shadowColor='rgba(160,110,60,0.18)';ctx.shadowBlur=18;ctx.shadowOffsetY=6;", "  ctx.fillStyle=on?'rgba(255,255,255,0.92)':'rgba(255,255,255,0.45)';", "  RR(bx,y,bw,chh,22);ctx.fill();", "  ctx.shadowBlur=0;ctx.shadowOffsetY=0;", "  ctx.strokeStyle='rgba(160,110,60,0.18)';ctx.lineWidth=1.5;", "  RR(bx,y,bw,chh,22);ctx.stroke();", "  /* mọi chữ trong card mờ: alpha .35 */", "  var ta=e*(on?1:0.35);", "  ctx.globalAlpha=ta;", "  ctx.fillStyle=c.c;ctx.font='bold 30px Consolas, monospace';", "  ctx.fillText(c.name,W/2,y+58);", "  var hf=52;ctx.font='bold '+hf+'px Segoe UI, sans-serif';", "  while(ctx.measureText(c.head).width>bw-120&&hf>36){hf-=2;ctx.font='bold '+hf+'px Segoe UI, sans-serif';}", "  ctx.fillStyle='#211a12';ctx.fillText(c.head,W/2,y+124);", "  ctx.fillStyle='#8a7a66';ctx.font='26px Segoe UI, sans-serif';", "  ctx.fillText(c.sub,W/2,y+172);", "  /* 3 hàng pill */", "  var pw=bw-200;", "  c.rows.forEach(function(r,j){", "    var py=y+210+j*84;", "    ctx.fillStyle=HXA(c.c,0.07);RR(W/2-pw/2,py,pw,64,12);ctx.fill();", "    ctx.strokeStyle=HXA(c.c,0.25);ctx.lineWidth=1.5;RR(W/2-pw/2,py,pw,64,12);ctx.stroke();", "    var rf=28;ctx.font=rf+'px Segoe UI, sans-serif';", "    while(ctx.measureText(r).width>pw-48&&rf>20){rf-=2;ctx.font=rf+'px Segoe UI, sans-serif';}", "    ctx.fillStyle='#211a12';ctx.fillText(r,W/2,py+33);", "  });", "  ctx.font='italic bold 30px Segoe UI, sans-serif';ctx.fillStyle=c.c;", "  ctx.fillText(c.note,W/2,y+chh-44);", "  ctx.globalAlpha=1;", "});", "ctx.restore();"], 1330)

def wp_layer_table(tag="ĐỐI CHIẾU", color="blue", title="Cùng một bài giải", left_head=None, right_head=None, rows=None):
    if not left_head:
        left_head = {"name": "ANTHROPIC", "date": "04·08", "color": "orange"}
    if not right_head:
        right_head = {"name": "OPENAI", "date": "04·15", "color": "blue"}
    if not rows:
        rows = [{"label": "Trạng thái", "left": "Session log", "right": "Memory + Session"},
        {"label": "Bộ não", "left": "Harness đóng", "right": "Harness mở"},
        {"label": "Đôi tay", "left": "Sandbox nhà", "right": "Sandbox 7 nhà"},
        {"label": "Khoá", "left": "Không vào sandbox", "right": "Không vào sandbox"}]
    rows = list(rows)[:5]
    def head(hd, defc):
        return {"t": str(hd.get("name", "")) + " · " + str(hd.get("date", "")), "c": ACCENT.get(hd.get("color", defc), ACCENT["orange"])}
    
    payload = json.dumps({
        "lh": head(left_head, "orange"),
        "rh": head(right_head, "blue"),
        "rows": [{"label": str(r.get("label", "")), "left": str(r.get("left", "")), "right": str(r.get("right", ""))} for r in rows],
    }, ensure_ascii=False)
    acc = ACCENT.get(color, ACCENT["blue"])
    h = 210 + (len(rows) + 1) * 96 + 20
    return scene([HXA, WPH, "var D=" + payload + ";", "var TAG=" + json.dumps(tag, ensure_ascii=False) + ";", "var TITLE=" + json.dumps(title, ensure_ascii=False) + ";", "var AC=" + json.dumps(acc) + ";", "WPH(TAG,TITLE,AC);", "/* cột: label 190 + 2 cột chia đều, khe giữa 2 ô so sánh rộng 28 */", "var x0=70,lw=190,g1=12,g2=28;", "var colw=(W-140-lw-g1-g2)/2;",
    
    "var x1=x0+lw+g1,x2=x1+colw+g2;", "var base=cursorY+210,rp=96,chh=84;", "ctx.save();ctx.textAlign='center';ctx.textBaseline='middle';", "function wcell(x,y,w){", "  ctx.shadowColor='rgba(160,110,60,0.18)';ctx.shadowBlur=12;ctx.shadowOffsetY=4;", "  ctx.fillStyle='rgba(255,255,255,0.92)';RR(x,y,w,chh,14);ctx.fill();", "  ctx.shadowBlur=0;ctx.shadowOffsetY=0;", "  ctx.strokeStyle='rgba(160,110,60,0.18)';ctx.lineWidth=1.5;RR(x,y,w,chh,14);ctx.stroke();}", "function fitT(t,mw,fs,pre){ctx.font=pre+fs+'px Segoe UI, sans-serif';", "  while(ctx.measureText(t).width>mw&&fs>18){fs-=1;ctx.font=pre+fs+'px Segoe UI, sans-serif';}}", "/* hàng đầu: ô LAYER + 2 header màu accent */", "var e0=EZ(CL(P*2.2));", "if(e0>0){var y0=base+(1-e0)*16;ctx.globalAlpha=e0;", "  wcell(x0,y0,lw);", "  ctx.fillStyle='#b0a08c';ctx.font='bold 26px Consolas, monospace';", "  ctx.fillText('LAYER',x0+lw/2,y0+chh/2+1);", "  [[x1,D.lh],[x2,D.rh]].forEach(function(hd){", "    /* lót trắng để tint accent lên màu sạch trên nền kem */", "    ctx.fillStyle='rgba(255,255,255,0.85)';RR(hd[0],y0,colw,chh,14);ctx.fill();", "    ctx.fillStyle=HXA(hd[1].c,0.14);RR(hd[0],y0,colw,chh,14);ctx.fill();", "    ctx.strokeStyle=HXA(hd[1].c,0.35);ctx.lineWidth=1.5;RR(hd[0],y0,colw,chh,14);ctx.stroke();", "    var hf=28;ctx.font='bold '+hf+'px Consolas, monospace';", "    while(ctx.measureText(hd[1].t).width>colw-28&&hf>18){hf-=1;ctx.font='bold '+hf+'px Consolas, monospace';}", "    ctx.fillStyle=hd[1].c;ctx.fillText(hd[1].t,hd[0]+colw/2,y0+chh/2+1);", "  });ctx.globalAlpha=1;}", "/* các hàng dữ liệu: label + 2 ô trắng + dấu xấp xỉ giữa */", "D.rows.forEach(function(r,i){", "  var e=EZ(CL(P*2.2-0.25-i*0.16));if(e<=0)return;", "  var y=base+(i+1)*rp+(1-e)*16;", "  ctx.globalAlpha=e;", "  wcell(x0,y,lw);wcell(x1,y,colw);wcell(x2,y,colw);", "  fitT(r.label,lw-24,26,'bold ');ctx.fillStyle='#211a12';", "  ctx.fillText(r.label,x0+lw/2,y+chh/2+1);", "  fitT(r.left,colw-32,26,'');ctx.fillStyle='#211a12';", "  ctx.fillText(r.left,x1+colw/2,y+chh/2+1);", "  fitT(r.right,colw-32,26,'');", "  ctx.fillText(r.right,x2+colw/2,y+chh/2+1);", "  ctx.fillStyle='#a4917a';ctx.font='bold 30px Segoe UI, sans-serif';", "  ctx.fillText('\\u2248',x1+colw+g2/2,y+chh/2+1);", "  ctx.globalAlpha=1;", "});", "ctx.restore();"], h)
    
SCENES = {"wp_duo_cards": {"fn": wp_duo_cards, "doc": 'wp_duo_cards {"tag":"PHÂN HOÁ","color":"blue","title":"Hai triết lý ngược nhau","top":{"name":"ANTHROPIC","head":"Trọn gói","sub":"hạ tầng lo hết","rows":["Não đóng nguồn","Sandbox tự nhà","Trả phí trọn gói"],"note":"như Apple","color":"orange"},"bottom":{"name":"OPENAI","head":"Mở + tự chọn","sub":"bạn chọn cloud, họ bán token","rows":["Mã nguồn mở","7 sandbox tuỳ chọn","Trả theo token"],"note":"như Android","color":"blue"}} — 2 card triết lý đối lập xếp dọc, card active/mờ luân phiên theo time (2.5s), mỗi card: name mono màu + head đậm + sub + 3 pill + note nghiêng (cao ~1330)', "demo": {"tag": "PHÂN HOÁ", "color": "blue", "title": "Hai triết lý ngược nhau", "top": {"name": "ANTHROPIC", "head": "Trọn gói", "sub": "hạ tầng lo hết", "rows": ["Não đóng nguồn", "Sandbox tự nhà", "Trả phí trọn gói"], "note": "như Apple", "color": "orange"}, "bottom": {"name": "OPENAI", "head": "Mở + tự chọn", "sub": "bạn chọn cloud, họ bán token", "rows": ["Mã nguồn mở", "7 sandbox tuỳ chọn", "Trả theo token"], "note": "như Android", "color": "blue"}}}, "wp_layer_table": {"fn": wp_layer_table, "doc": 'wp_layer_table {"tag":"ĐỐI CHIẾU","color":"blue","title":"Cùng một bài giải","left_head":{"name":"ANTHROPIC","date":"04·08","color":"orange"},"right_head":{"name":"OPENAI","date":"04·15","color":"blue"},"rows":[{"label":"Trạng thái","left":"Session log","right":"Memory + Session"}]} — bảng đối chiếu 3 cột theo layer: ô LAYER + 2 header màu, mỗi hàng label + 2 ô trắng có dấu ≈ giữa, reveal từng hàng (4-5 hàng)', "demo": {"tag": "ĐỐI CHIẾU", "color": "blue", "title": "Cùng một bài giải", "left_head": {"name": "ANTHROPIC", "date": "04·08", "color": "orange"}, "right_head": {"name": "OPENAI", "date": "04·15", "color": "blue"}, "rows": [{"label": "Trạng thái", "left": "Session log", "right": "Memory + Session"},
    {"label": "Bộ não", "left": "Harness đóng", "right": "Harness mở"},
    {"label": "Đôi tay", "left": "Sandbox nhà", "right": "Sandbox 7 nhà"},
    {"label": "Khoá", "left": "Không vào sandbox", "right": "Không vào sandbox"}]}}}
