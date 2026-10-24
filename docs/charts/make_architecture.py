import base64
# Builds docs/charts/how-swell-works.png (run from the scratchpad that has gf/ fonts, then screenshot arch.html at 1700x800).
L="/home/claude/elnino/docs/logos/"; F="gf/ofl/lato/"
b64=lambda p: base64.b64encode(open(p,'rb').read()).decode()
logo=lambda n,s=38: f'<img src="data:image/png;base64,{b64(L+n+".png")}" style="width:{s}px;height:{s}px;object-fit:contain">'
tile=lambda n,s=34: f'<span class="tile">{logo(n,s)}</span>'
font=lambda n,w: f"@font-face{{font-family:Lato;font-weight:{w};src:url(data:font/ttf;base64,{b64(F+n)})}}"
src=lambda name,what,ico: f'<div class="src">{ico}<div><b>{name}</b><span>{what}</span></div></div>'
html=f"""<html><head><meta charset="utf-8"><style>{font('Lato-Regular.ttf',400)}{font('Lato-Bold.ttf',700)}{font('Lato-Black.ttf',900)}
*{{box-sizing:border-box;margin:0}} body{{width:1700px;height:800px;background:#FAFAFA;font-family:Lato;color:#16222C;position:relative}}
.card{{position:absolute;border-radius:24px;padding:24px}}
.phone{{left:10px;top:150px;width:330px;height:300px;background:#fff;border:2px solid #D9E1E7}}
.server{{left:480px;top:30px;width:560px;height:470px;background:#0B3349;color:#fff}}
.db{{left:480px;top:590px;width:560px;height:120px;background:#fff;border:2px solid #D9E1E7;display:flex;gap:20px;align-items:center}}
.srcs{{left:1180px;top:30px;width:510px;height:478px;background:#fff;border:2px solid #D9E1E7;padding:14px 24px}}
h3{{font-size:31px;font-weight:900;margin-bottom:6px}} p{{font-size:23px;color:#5A6873;line-height:1.3}}
.server p{{color:#C9DEE5}} .row{{display:flex;gap:10px;align-items:center;margin:14px 0}}
.tile{{background:#fff;border-radius:12px;width:52px;height:52px;display:grid;place-items:center}}
.chip{{background:rgba(255,255,255,.13);border-radius:14px;padding:13px 18px;font-size:24px;font-weight:700;margin-top:12px}}
.src{{display:flex;gap:16px;align-items:center;padding:12px 0;border-bottom:1px solid #E6ECF0}} .src:last-child{{border:0}}
.src b{{display:block;font-size:24px}} .src span{{font-size:20px;color:#5A6873}}
.ico{{width:46px;height:46px;border-radius:11px;display:grid;place-items:center;font-weight:900;font-size:14px;color:#fff;flex:none}}
.num{{position:absolute;width:48px;height:48px;border-radius:50%;background:#E2892A;color:#fff;font-weight:900;font-size:26px;display:grid;place-items:center}}
.lab{{position:absolute;font-size:21px;font-weight:700;color:#16222C;text-align:center;line-height:1.2}}
.gl{{position:absolute;top:740px;font-size:21px;color:#5A6873;line-height:1.25}} .gl b{{color:#0E7486}}
svg{{position:absolute;left:0;top:0}}
</style></head><body>
<svg width="1700" height="800"><defs><marker id="a" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto"><path d="M0,0 L12,6 L0,12 z" fill="#9AA7B0"/></marker></defs>
<line x1="342" y1="250" x2="470" y2="250" stroke="#9AA7B0" stroke-width="4" marker-end="url(#a)"/>
<line x1="478" y1="360" x2="350" y2="360" stroke="#9AA7B0" stroke-width="4" marker-end="url(#a)"/>
<line x1="1042" y1="190" x2="1170" y2="190" stroke="#9AA7B0" stroke-width="4" marker-end="url(#a)"/>
<line x1="1042" y1="440" x2="1170" y2="440" stroke="#9AA7B0" stroke-width="4" marker-end="url(#a)"/>
<line x1="760" y1="502" x2="760" y2="580" stroke="#9AA7B0" stroke-width="4" marker-end="url(#a)"/>
</svg>
<div class="card phone"><h3>Your phone</h3><p>The website or the iPhone app</p>
 <div class="row">{logo('html5')}{logo('javascript')}{logo('swift')}{logo('apple')}</div><p>You type an address and who lives there.</p></div>
<div class="num" style="left:382px;top:196px">1</div><div class="lab" style="left:345px;top:266px;width:125px">sends your address</div>
<div class="num" style="left:382px;top:374px">5</div><div class="lab" style="left:345px;top:430px;width:125px">sends back your plan</div>
<div class="card server"><div class="row" style="margin-top:0">{tile('python')}{tile('flask')}<h3 style="margin:0 0 0 8px">Swell server</h3></div>
 <p>A Python program built with Flask</p>
 <div class="chip">Risk score from 0 to 100</div><div class="chip">Checklist rules for each home or farm</div><div class="chip">Flood plan or drought plan</div><div class="chip">Guardrail that checks every AI answer</div></div>
<div class="num" style="left:1082px;top:132px">2</div><div class="lab" style="left:1042px;top:204px;width:130px">asks official sources</div>
<div class="num" style="left:1082px;top:382px">3</div><div class="lab" style="left:1042px;top:454px;width:130px">asks the AI</div>
<div class="card srcs">
 {src('U.S. Census','Finds the exact place','<div class="ico" style="background:#4D86B8">GEO</div>')}
 {src('FEMA','Is it in a flood zone?','<div class="ico" style="background:#0E7486">FEMA</div>')}
 {src('USGS','How high is the ground?','<div class="ico" style="background:#3E7D3A">USGS</div>')}
 {src('National Weather Service','Live storm alerts and rain','<div class="ico" style="background:#0B3349">NWS</div>')}
 {src('OpenStreetMap','Places outside the U.S.','<div class="ico" style="background:#7A8B99">OSM</div>')}
 {src('Google Gemini AI','Translates plans, checks photos',logo('google',46))}
</div>
<div class="num" style="left:784px;top:518px">4</div><div class="lab" style="left:844px;top:530px;width:200px;text-align:left">saves it</div>
<div class="card db">{logo('postgresql',64)}<div><h3>PostgreSQL database</h3><p>Keeps every plan, account and report</p></div></div>
<div class="gl" style="left:10px;width:520px"><b>Server:</b> a computer that does the heavy work, so your phone doesn’t have to.</div>
<div class="gl" style="left:590px;width:520px"><b>API:</b> how one program asks another for data, like asking FEMA for a flood zone.</div>
<div class="gl" style="left:1170px;width:520px"><b>Database:</b> organized tables, like a giant spreadsheet, that keep data safe.</div>
</body></html>"""
open('arch.html','w').write(html)
