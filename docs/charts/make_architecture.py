import base64, os
L="/home/claude/elnino/docs/logos/"; F="gf/ofl/lato/"
b64=lambda p: base64.b64encode(open(p,'rb').read()).decode()
logo=lambda n,s=34: f'<img src="data:image/png;base64,{b64(L+n+".png")}" style="width:{s}px;height:{s}px;object-fit:contain">'
font=lambda n,w: f"@font-face{{font-family:Lato;font-weight:{w};src:url(data:font/ttf;base64,{b64(F+n)})}}"
src=lambda name,what,ico: f'<div class="src">{ico}<div><b>{name}</b><span>{what}</span></div></div>'
html=f"""<html><head><meta charset="utf-8"><style>{font('Lato-Regular.ttf',400)}{font('Lato-Bold.ttf',700)}{font('Lato-Black.ttf',900)}
*{{box-sizing:border-box;margin:0}} body{{width:1700px;height:780px;background:#FAFAFA;font-family:Lato;color:#16222C;position:relative}}
.card{{position:absolute;border-radius:22px;padding:22px}}
.phone{{left:20px;top:150px;width:300px;height:250px;background:#fff;border:2px solid #D9E1E7}}
.server{{left:470px;top:60px;width:520px;height:420px;background:#0B3349;color:#fff}}
.db{{left:470px;top:560px;width:520px;height:120px;background:#fff;border:2px solid #D9E1E7;display:flex;gap:18px;align-items:center}}
.srcs{{left:1140px;top:20px;width:540px;height:478px;background:#fff;border:2px solid #D9E1E7}}
h3{{font-size:25px;font-weight:900;margin-bottom:6px}} p{{font-size:19px;color:#5A6873;line-height:1.3}}
.server p{{color:#C9DEE5}} .row{{display:flex;gap:10px;align-items:center;margin:12px 0}}
.chip{{background:rgba(255,255,255,.12);border-radius:12px;padding:12px 16px;font-size:20px;font-weight:700;margin-top:12px}}
.src{{display:flex;gap:14px;align-items:center;padding:11px 0;border-bottom:1px solid #E6ECF0}} .src:last-child{{border:0}}
.src b{{display:block;font-size:20px}} .src span{{font-size:17px;color:#5A6873}}
.ico{{width:40px;height:40px;border-radius:10px;display:grid;place-items:center;font-weight:900;font-size:13px;color:#fff;flex:none}}
.num{{position:absolute;width:40px;height:40px;border-radius:50%;background:#E2892A;color:#fff;font-weight:900;font-size:21px;display:grid;place-items:center}}
.lab{{position:absolute;font-size:18px;font-weight:700;color:#16222C;text-align:center}}
.gl{{position:absolute;top:720px;font-size:17px;color:#5A6873}} .gl b{{color:#0E7486}}
svg{{position:absolute;left:0;top:0}}
</style></head><body>
<svg width="1700" height="780"><defs><marker id="a" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto"><path d="M0,0 L12,6 L0,12 z" fill="#9AA7B0"/></marker></defs>
<line x1="322" y1="245" x2="462" y2="245" stroke="#9AA7B0" stroke-width="3" marker-end="url(#a)"/>
<line x1="468" y1="320" x2="328" y2="320" stroke="#9AA7B0" stroke-width="3" marker-end="url(#a)"/>
<line x1="992" y1="200" x2="1132" y2="200" stroke="#9AA7B0" stroke-width="3" marker-end="url(#a)"/>
<line x1="992" y1="440" x2="1132" y2="440" stroke="#9AA7B0" stroke-width="3" marker-end="url(#a)"/>
<line x1="730" y1="482" x2="730" y2="552" stroke="#9AA7B0" stroke-width="3" marker-end="url(#a)"/>
</svg>
<div class="card phone"><h3>Your phone</h3><p>The website or the iPhone app</p>
 <div class="row">{logo('html5')}{logo('javascript')}{logo('swift')}{logo('apple')}</div><p>You type an address and who lives there.</p></div>
<div class="num" style="left:372px;top:198px">1</div><div class="lab" style="left:330px;top:255px;width:130px">sends your address</div>
<div class="num" style="left:372px;top:332px">5</div><div class="lab" style="left:330px;top:380px;width:130px">sends back your plan</div>
<div class="card server"><div class="row" style="margin-top:0">{logo('python',40)}{logo('flask',40)}<h3 style="margin:0 0 0 6px">Swell server</h3></div>
 <p>A Python program (Flask) that does all the work</p>
 <div class="chip">Risk score from 0 to 100</div><div class="chip">Checklist rules for each home or farm</div><div class="chip">Flood plan or drought plan, from NOAA’s El Niño map</div><div class="chip">Guardrail that checks every AI answer</div></div>
<div class="num" style="left:1042px;top:150px">2</div><div class="lab" style="left:996px;top:212px;width:140px">asks official sources</div>
<div class="num" style="left:1042px;top:390px">3</div><div class="lab" style="left:996px;top:452px;width:140px">asks the AI</div>
<div class="card srcs">
 {src('U.S. Census','Finds the exact place','<div class="ico" style="background:#4D86B8">GEO</div>')}
 {src('FEMA','Is it in a flood zone?','<div class="ico" style="background:#0E7486">FEMA</div>')}
 {src('USGS','How high is the ground?','<div class="ico" style="background:#3E7D3A">USGS</div>')}
 {src('National Weather Service','Live storm alerts and rain','<div class="ico" style="background:#0B3349">NWS</div>')}
 {src('OpenStreetMap','Finds places outside the U.S.','<div class="ico" style="background:#7A8B99">OSM</div>')}
 {src('Google Gemini AI','Translates the plan and checks photos',logo('google',40))}
</div>
<div class="num" style="left:750px;top:497px">4</div><div class="lab" style="left:800px;top:506px;width:200px;text-align:left">saves it</div>
<div class="card db">{logo('postgresql',58)}<div><h3>PostgreSQL database</h3><p>Stores every plan, account, community and report</p></div></div>
<div class="gl" style="left:20px;width:520px"><b>Server:</b> a computer that does the heavy work, so your phone doesn’t have to.</div>
<div class="gl" style="left:590px;width:520px"><b>API:</b> how one program asks another for data, like asking FEMA for a flood zone.</div>
<div class="gl" style="left:1160px;width:520px"><b>Database:</b> organized tables, like a giant spreadsheet with rules, that keep data safe.</div>
</body></html>"""
open('arch.html','w').write(html)
