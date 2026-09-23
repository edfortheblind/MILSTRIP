"""Build the offline operating guide and editable SVG charts from repository sources.

Install docs/operations-guide/requirements.txt first. PDF rendering is optional
and uses an isolated headless browser, never the owner's signed-in browser.
"""
from __future__ import annotations

import argparse
import base64
from html import escape
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET

import markdown

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "operations-guide"
DIAGRAMS = OUT / "diagrams"
DATE = "September 23, 2026"
PALETTE = {
    "dev": ("#e8f5f1", "#087f6c", "CURRENT DEV"),
    "manual": ("#f0f3f7", "#53657d", "EXISTING MANUAL"),
    "future": ("#ecf2ff", "#315fc1", "PROPOSED"),
    "gate": ("#fff3da", "#a86b0c", "GATE"),
}


class Chart:
    def __init__(self, filename, title, subtitle, height, kind="dev"):
        self.filename, self.title, self.height = filename, title, height
        self.parts = []
        self.nodes = []
        self.text(30, 48, title, 29, weight=700)
        _, color, label = PALETTE[kind]
        self.parts.append(f'<rect x="30" y="68" width="{len(label)*10+28}" height="30" rx="15" fill="{color}"/>')
        self.text(44, 89, label, 15, fill="#ffffff", weight=700)
        self.text(30, 126, subtitle, 18, fill="#52657d")

    def text(self, x, y, value, size=19, fill="#142b45", weight=400, anchor="start"):
        self.parts.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{escape(value)}</text>')

    def panel(self, x, y, w, h, label, kind="dev"):
        bg, color, _ = PALETTE[kind]
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{bg}" stroke="{color}" stroke-opacity=".25"/>')
        self.text(x+16, y+28, label, 17, fill=color, weight=700)

    def node(self, key, x, y, w, h, title, lines, kind="dev"):
        _, color, _ = PALETTE[kind]
        self.nodes.append({"id": key, "x": x, "y": y, "w": w, "h": h})
        self.parts.append(f'<g data-node="{key}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="#ffffff" stroke="{color}" stroke-width="1.7"/>')
        self.parts.append(f'<rect x="{x}" y="{y+12}" width="4" height="{h-24}" rx="2" fill="{color}"/>')
        title_size = min(21, (w-32) / (max(1,len(title)) * .57))
        self.text(x+16, y+30, title, title_size, weight=700)
        for index, line in enumerate(lines):
            self.text(x+16, y+56+index*23, line, 18)
        self.parts.append("</g>")
        assert y+56+max(0,len(lines)-1)*23 < y+h, key
        assert x>=0 and y>=0 and x+w<=1000 and y+h<self.height, key

    def arrow(self, points, label="", label_at=None, dashed=False):
        encoded=" ".join(f"{x},{y}" for x,y in points)
        dash=' stroke-dasharray="6 5"' if dashed else ''
        self.parts.append(f'<polyline points="{encoded}" fill="none" stroke="#60758c" stroke-width="2" marker-end="url(#arrow)"{dash}/>')
        if label:
            assert label_at
            x,y=label_at
            self.parts.append(f'<rect x="{x-len(label)*4.5-6}" y="{y-17}" width="{len(label)*9+12}" height="23" rx="5" fill="#ffffff"/>')
            self.text(x,y,label,16,anchor="middle")

    def save(self):
        self.text(30,self.height-18,f"MILSTRIP  |  {DATE}  |  See guide.md for evidence and acceptance limits",14,fill="#60758c")
        description=f"{self.title}. {PALETTE['future' if 'phase2' in self.filename else 'dev'][2]}. Full text equivalent is in the operating guide."
        svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="{self.height}" viewBox="0 0 1000 {self.height}" role="img" aria-labelledby="title desc">
<title id="title">{escape(self.title)}</title><desc id="desc">{escape(description)}</desc>
<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#60758c"/></marker></defs>
<rect width="1000" height="{self.height}" fill="#ffffff"/>
<g font-family="Segoe UI, Arial, sans-serif">{''.join(self.parts)}</g></svg>'''
        ET.fromstring(svg)
        (DIAGRAMS / self.filename).write_text(svg,encoding="utf-8")
        return {"file":self.filename,"title":self.title,"nodes":self.nodes}


def charts():
    manifests=[]
    c=Chart("01-current-functional.svg","Functional flow: what the app does today","The app ends at review and audit. The manual production route is separate.",850)
    c.panel(20,150,960,400,"CURRENT DEV  /  implemented and tested with synthetic input")
    c.node("source",40,205,280,102,"Original source",["Email or ticket text","Pasted by the operator"])
    c.node("intake",360,205,280,102,"Submit intake",["Save Request ID and source","Local application metadata"])
    c.node("parser",680,205,280,102,"Parse and validate",["Conservative normalization","Preserve / pad to 80 chars"])
    c.arrow([(320,255),(360,255)]);c.arrow([(640,255),(680,255)])
    c.node("results",680,390,280,122,"Record results",["VALID / REQUIRES_REVIEW","or REJECTED","Issues stay visible"])
    c.node("review",360,390,280,122,"Human review",["APPROVED or REJECTED","Reason + version required","Invalid approval blocked"])
    c.node("audit",40,390,280,122,"Audit and history",["Authenticated actor saved","Review is not delivery","No operational write"])
    c.arrow([(820,307),(820,390)]);c.arrow([(680,451),(640,451)]);c.arrow([(360,451),(320,451)])
    c.panel(20,590,960,200,"EXISTING MANUAL  /  recorded production context, not invoked by this app","manual")
    for key,x,title,lines in [("raw",40,"Raw MILS",["SQL raw staging","Shawn prepares input"]),("batch",280,"Manual SQL batch",["Reference checks","ERP-order duplicates"]),("940",520,"download_ship940",["Direct insert target","Not 940 staging"]),("downstream",760,"Existing downstream",["ADF / ShipMaster","Boomi / SCALE"])]:
        c.node(key,x,645,200,108,title,lines,"manual")
    for x in [240,480,720]:c.arrow([(x,699),(x+40,699)])
    manifests.append(c.save())

    c=Chart("02-current-architecture.svg","Technical architecture: current development","Existing Default environment, MILSTRIP solution, app, connector and gateway.",835)
    c.panel(20,150,960,190,"POWER PLATFORM CLOUD  /  saved, unpublished app")
    c.node("app",50,205,370,100,"MILSTRIP Intake Dev",["Four canvas screens; in-memory inputs","Power Apps user sign-in"])
    c.node("connector",570,205,370,100,"MILSTRIP Local Dev API",["Seven typed API operations","Dedicated Basic connection identity"])
    c.arrow([(420,255),(570,255)])
    c.panel(20,380,960,315,"ED'S LAPTOP  /  required for current execution")
    c.node("gateway",40,440,280,105,"Standard gateway",["MILSTRIP-DEV-LAPTOP","Existing cloud-to-local bridge"])
    c.node("api",360,440,280,105,"FastAPI + parser",["127.0.0.1:8000 / api/v1","Basic auth; loopback guard"])
    c.node("pg",680,440,280,105,"Local PostgreSQL",["trav3pl-psqldb-stage","milstrip_app metadata"])
    c.arrow([(755,305),(755,357),(180,357),(180,440)])
    c.arrow([(320,492),(360,492)]);c.arrow([(640,492),(680,492)])
    c.text(48,590,"Gateway → API: HTTP on loopback only. API → DB: psycopg / localhost:5432.",20)
    c.text(48,622,"Review audit actor: milstrip-app. Power Apps sign-in is not per-user API identity.",20)
    c.text(48,654,"Private credentials stay in restricted .cred storage; they are not shipped in the app.",19)
    c.panel(20,727,960,63,"NO RUNTIME LINK TO PRODUCTION SQL  /  no legacy writer, CSV export or FTP delivery","manual")
    manifests.append(c.save())

    c=Chart("03-current-user-sop.svg","End-user SOP: use the current app","Authorized development testing only. Exact button names match the existing screens.",1040)
    steps=[("open",155,"1  Open Preview",["Owner confirms API, database and gateway are ready.","Use approved test input; start on MILSTRIP intake."]),
           ("submit",280,"2  Paste, then Submit intake",["Click once. Keep the original text.","Continue only when a Request ID is returned."]),
           ("load",405,"3  Load / refresh results",["Inspect every record and issue.","Use Next results page when enabled."]),
           ("inspect",530,"4  Inspect / review",["Read canonical length and validation status.","Do not edit, trim or invent business values."]),
           ("save",655,"5  Save review",["Choose APPROVED or REJECTED; enter a reason.","Check the saved message and review version."]),
           ("history",780,"6  History → Load / refresh history",["Verify the event; use More history if enabled.","Refresh Results before relying on old review rows."]),
           ("finish",905,"7  Keep the Request ID",["Current app has no release or shipment action.","Approval does not mean sent or shipped."])]
    for key,y,title,lines in steps:c.node(key,30,y,570,104,title,lines)
    for y in [259,384,509,634,759,884]:c.arrow([(315,y),(315,y+21)])
    c.node("unknown",650,280,320,127,"Submission uncertain",["Load recent requests; match","the displayed source ID.","Confirm absence before retry."],"gate")
    c.arrow([(600,332),(650,332)],dashed=True)
    c.node("invalid",650,450,320,127,"Validation REJECTED",["Obtain corrected source.","Submit a new intake.","Approval is disabled."],"gate")
    c.arrow([(600,582),(625,582),(625,514),(650,514)],dashed=True)
    c.node("retry",650,640,320,127,"Review exception",["Unknown: Retry same command.","Conflict: Reload after conflict;","inspect, then decide again."],"gate")
    c.arrow([(600,707),(650,707)],dashed=True)
    c.node("restart",650,830,320,149,"If the app closes",["Pending inputs are in memory.","Reconcile requests / history.","Give support IDs and errors;","never passwords or raw orders."],"gate")
    manifests.append(c.save())

    c=Chart("04-phase2-azure-sql.svg","P2.1 architecture: Azure SQL production","PROPOSED. Published app is assumed; production hosting and adapters are not implemented.",880,"future")
    c.node("app",30,160,280,126,"Published canvas app",["Same intake / review contract","Per-user Entra sign-in","Production release gate"],"future")
    c.node("api",360,160,280,126,"Managed API host",["Proposed Azure App Service","HTTPS + Entra authorization","Python parser; role checks"],"future")
    c.node("adapter",690,160,280,126,"SQL repository",["New T-SQL persistence adapter","Stable IDs / review versions","Bounded pools + transactions"],"future")
    c.arrow([(310,223),(360,223)]);c.arrow([(640,223),(690,223)])
    c.panel(20,355,960,285,"EXISTING AZURE SQL WORKBENCH  /  new application objects need explicit approval","future")
    c.node("metadata",45,415,275,126,"milstrip_app",["Intake, review and audit","Durable command ledger","Proposed application schema"],"future")
    c.node("release",365,415,275,126,"Gated release adapter",["Latest approved version","Reference / duplicate checks","One atomic business effect"],"gate")
    c.node("legacy",685,415,275,126,"Existing dbo contract",["staging_download_shipMILS","direct to download_ship940","Not staging_download_ship940"],"manual")
    c.arrow([(830,286),(830,323),(182,323),(182,415)])
    c.arrow([(320,478),(365,478)],dashed=True);c.arrow([(640,478),(685,478)],dashed=True)
    c.text(45,583,"Target database: trav3pl-sqldb-eastus-prod  |  Identity recorded September 21",20)
    c.text(45,615,"G0: reconcile SQL freeze. G1: select SQL or Rainbow delivery. No dual release route.",19)
    c.node("ops",30,701,460,126,"Production operations",["Individual audit; service-to-DB identity","Monitoring, restores, bounded capacity","No dependency on the DEV laptop"],"future")
    c.node("downstream",545,701,425,126,"Existing downstream owners",["ADF / ShipMaster / Boomi / SCALE","Observe agreed acknowledgement","SQL commit is not shipment confirmation"],"manual")
    c.arrow([(820,541),(990,541),(990,674),(757,674),(757,701)],dashed=True)
    manifests.append(c.save())

    c=Chart("05-phase2-functional.svg","Phase 2 flow: review, release, acknowledge","PROPOSED controls and states. None of the release/delivery actions exists today.",890,"future")
    c.node("intake",30,160,280,104,"Intake and validation",["Parse / canonicalize","Check live reference data"],"future")
    c.node("review",360,160,280,104,"Authorized review",["Decision + reason + version","Reject unresolved business data"],"future")
    c.node("gate",690,160,280,104,"Release eligibility",["Current approval and role","Accepted delivery contract"],"gate")
    c.arrow([(310,212),(360,212)]);c.arrow([(640,212),(690,212)])
    c.node("hold",30,350,280,125,"Hold and correct",["Invalid / missing references","No business write","Preserve evidence"],"gate")
    c.node("command",360,350,280,125,"Durable release command",["Unique ID + payload + version","One authoritative DB writer","Atomic claim / transaction"],"future")
    c.node("stop",690,350,280,125,"Not eligible",["Do not release","Resolve role, review or data","then re-evaluate eligibility"],"gate")
    c.arrow([(170,264),(170,350)],"invalid",(170,315),True)
    c.arrow([(830,264),(830,350)],"no",(830,315),True)
    c.arrow([(830,264),(830,304),(500,304),(500,350)],"eligible",(535,298))
    c.node("commit",360,555,280,125,"Verified handoff",["Inserted / duplicate / rejected","Read back committed outcome","Never infer from SENT alone"],"future")
    c.node("uncertain",690,555,280,125,"Outcome uncertain",["Reconcile SAME command","No blind retry / manual insert","Escalate unresolved state"],"gate")
    c.arrow([(500,475),(500,555)]);c.arrow([(640,618),(690,618)],dashed=True)
    c.node("ack",360,740,610,100,"Downstream acknowledgement + audit",["Record the agreed receipt / rejection separately from DB commit.","Only a defined, observed acknowledgement establishes delivery."],"future")
    c.arrow([(500,680),(500,740)])
    c.node("route",30,555,280,193,"Exactly one route",["SQL contract is the proposed","baseline for planning.","If Rainbow is selected:","outbox + serializer + transport","need separate acceptance."],"gate")
    manifests.append(c.save())

    c=Chart("06-phase2-postgresql.svg","P2.2 architecture: PostgreSQL production","PROPOSED. Switch only after migration, business parity and production acceptance.",920,"future")
    c.node("app",30,155,280,103,"Same published app",["Stable workflow and IDs","Individual reviewer identity"],"future")
    c.node("api",360,155,280,103,"Same API contract",["Qualified PG repository","Accepted release adapter"],"future")
    c.node("config",690,155,280,103,"One writer setting",["Server-side configuration","SQL writers fenced at cutover"],"gate")
    c.arrow([(310,207),(360,207)]);c.arrow([(640,207),(690,207)])
    c.panel(20,330,960,345,"MIGRATION TARGET  /  one Azure Windows VM; distinct PostgreSQL services","future")
    c.node("stage",45,395,430,126,"PostgreSQL Stage",["Isolated port, data, identity and backup","Restore accepted artifact; qualify behavior","Not a production writer"],"future")
    c.node("prod",525,395,430,126,"PostgreSQL Production",["milstrip_app + accepted dbo compatibility","Migrated history / commands / releases","Production identity recorded before GO"],"future")
    c.arrow([(830,258),(830,300),(740,300),(740,395)])
    c.arrow([(475,458),(525,458)],dashed=True)
    c.text(45,568,"Separate services on one VM are not high availability; the failure domain is shared.",19)
    c.text(45,602,"Backups / WAL / configuration recovery must meet agreed and rehearsed RPO/RTO.",19)
    c.text(45,636,"The current localhost development database is not the future production service.",19)
    c.node("sql",30,735,440,130,"Azure SQL rollback baseline",["Frozen after writer cutover","30 stable days after PG acceptance","No blind failback after new PG writes"],"gate")
    c.node("downstream",530,735,440,130,"Qualified downstream contract",["Consumer / connection changes accepted","No replacement of SCALE or Boomi","Observed acknowledgements retained"],"manual")
    c.arrow([(740,521),(985,521),(985,706),(750,706),(750,735)])
    manifests.append(c.save())

    c=Chart("07-phase2-transition.svg","Two periods: qualify, switch, stabilize","Q4 2026 is the owner's target. Dates never override the acceptance gates.",860,"future")
    c.node("now",30,165,280,145,"NOW / September 23",["Unpublished working DEV app","SQL manual authority retained","Freeze, route, identity gates","Finish canvas acceptance"],"dev")
    c.node("p21",360,165,280,145,"P2.1 / target October",["Published production pilot","Existing Azure SQL DB","API moved off laptop","Measured load and operations"],"future")
    c.node("p22",690,165,280,145,"P2.2 / target December",["Accepted PG Production","One writer switch","Stable IDs / history / commands","Qualified downstream flow"],"future")
    c.arrow([(310,237),(360,237)],dashed=True);c.arrow([(640,237),(690,237)],dashed=True)
    c.panel(20,365,960,155,"BEFORE CUTOVER  /  two-month MILSTRIP controlled comparison","gate")
    c.text(45,424,"SQL remains authoritative; PG comparison does not create duplicate production effects.",20)
    c.text(45,457,"Start no later than October 31 for a full two-month window ending December 31.",20)
    c.text(45,490,"Late readiness means a later date or an explicit gate change, not skipped evidence.",19)
    c.panel(20,550,960,155,"AFTER PG PRODUCTION ACCEPTANCE  /  30 stable days of SQL retention","gate")
    c.text(45,608,"Frozen SQL is a rollback baseline, not an automatic live fallback for new PG writes.",20)
    c.text(45,641,"December 31 go-live pushes this window into January 2027.",20)
    c.text(45,674,"End-Q4 retirement instead requires acceptance around December 1 and a stable window.",19)
    c.node("cutover",30,744,940,72,"Cutover sequence",["Quiesce → capture → reconcile → switch once → observe → separately approve retirement"],"future")
    manifests.append(c.save())
    return manifests


CSS = """
:root{--ink:#142b45;--muted:#53657d;--line:#d8e2ed;--accent:#087f6c;--paper:#fff}
*{box-sizing:border-box}body{margin:0;color:var(--ink);background:#edf2f7;font:16px/1.6 'Segoe UI',Arial,sans-serif}
.topbar{position:sticky;top:0;z-index:5;background:#102a43;color:white;padding:12px 24px;display:flex;align-items:center;justify-content:space-between;gap:12px}
.topbar a{color:#fff;margin-right:18px;font-size:14px}.topbar button{background:#fff;color:#102a43;border:0;border-radius:5px;padding:9px 16px;cursor:pointer;font-weight:700}
.cover{max-width:1180px;margin:28px auto 0;padding:44px 52px;background:#102a43;color:#fff;border-radius:16px 16px 0 0;display:flex;gap:28px;align-items:center}.cover img{width:105px;height:105px;border-radius:14px}.cover h1{font-size:36px;line-height:1.2;margin:8px 0 12px}.cover p{margin:0;color:#d4e4f3}.eyebrow{letter-spacing:2px;text-transform:uppercase;font-weight:700;font-size:12px;color:#8ed7c7}
main{max-width:1180px;margin:0 auto 36px;background:#fff;padding:38px 52px 60px;border-radius:0 0 16px 16px}
article>h1{display:none}h2{font-size:28px;line-height:1.25;margin:52px 0 20px;padding-top:12px;border-top:3px solid #d8e2ed;scroll-margin-top:82px}h3{font-size:21px;margin-top:28px}p{margin:14px 0}a{color:#2455a6;text-decoration-thickness:1px;text-underline-offset:3px}code{font-size:.88em;background:#edf2f7;padding:2px 4px;border-radius:3px;overflow-wrap:anywhere}table{border-collapse:collapse;width:100%;font-size:14px;margin:20px 0 26px;table-layout:fixed}th,td{padding:12px 13px;border:1px solid var(--line);vertical-align:top;overflow-wrap:anywhere}th{background:#102a43;color:#fff;text-align:left}tbody tr:nth-child(even){background:#f5f8fb}td:first-child{font-weight:600}strong{font-weight:700}li{margin:7px 0}figure{margin:24px 0 28px;border:1px solid var(--line);border-radius:12px;padding:14px;background:#fff;break-inside:avoid}figure svg{width:100%;height:auto;display:block}figcaption{font-size:13px;color:var(--muted);padding:8px 8px 0}figcaption a{float:right}.toc{padding:16px 22px;background:#f1f7fa;border-left:4px solid #087f6c;border-radius:4px;font-size:14px}.toc ul{columns:2;padding-left:20px}.toc a{color:#25435d}footer{font-size:13px;color:var(--muted);margin-top:36px;border-top:1px solid var(--line);padding-top:18px}
@media(max-width:750px){.cover{margin:0;border-radius:0;padding:24px;align-items:flex-start}.cover img{width:65px;height:65px}.cover h1{font-size:27px}main{padding:20px}.topbar{position:relative;flex-wrap:wrap}.toc ul{columns:1}table{font-size:12px}th,td{padding:7px}h2{font-size:24px}figure{padding:3px}}
@page{size:A4;margin:15mm 14mm 17mm}
@media print{body{background:white;font-size:10pt;line-height:1.45}.topbar,.toc{display:none}.cover{margin:0;padding:24px;border-radius:0;print-color-adjust:exact}.cover h1{font-size:25pt}.cover img{width:85px;height:85px}main{max-width:none;margin:0;padding:0;border-radius:0}h2{font-size:18pt;break-before:page;margin:0 0 15px;padding-top:0;border-top:0;break-after:avoid}h3{font-size:13pt;break-after:avoid}table{font-size:8.5pt}th,td{padding:7px}tr{break-inside:avoid}thead{display:table-header-group}figure{padding:0;border:0;break-inside:avoid;margin:16px 0}figure svg{max-height:230mm}figcaption{font-size:8pt}figcaption a{display:none}p,li{orphans:3;widows:3}a{color:inherit}th,.cover{print-color-adjust:exact}article>p:first-of-type{margin-top:24px}footer{font-size:8pt}}
@media print{.toc{display:block;margin:20px 0;font-size:9pt;break-inside:avoid;print-color-adjust:exact}.toc li{margin:5px 0;break-inside:avoid}}
"""


def build_html():
    import re
    source=(OUT/"guide.md").read_text(encoding="utf-8")
    body=markdown.markdown(source,extensions=["tables","toc","fenced_code"],extension_configs={"toc":{"permalink":False}})
    def embed(match):
        alt,path=match.groups()
        svg=(OUT/path).read_text(encoding="utf-8")
        return f'<figure>{svg}<figcaption>{alt} <a href="{path}" download>Download SVG</a></figcaption></figure>'
    body=re.sub(r'<p><img alt="([^"]*)" src="(diagrams/[^"]+)"\s*/></p>',embed,body)
    # Inline SVG identifiers must be unique in the combined document.
    for i,match in reversed(list(enumerate(re.finditer(r'<svg\b.*?</svg>',body,re.S)))):
        svg=match.group().replace('id="title"',f'id="title-{i}"').replace('id="desc"',f'id="desc-{i}"').replace('id="arrow"',f'id="arrow-{i}"').replace('aria-labelledby="title desc"',f'aria-labelledby="title-{i} desc-{i}"').replace('url(#arrow)',f'url(#arrow-{i})')
        body=body[:match.start()]+svg+body[match.end():]
    toc='<div class="toc"><strong>In this guide</strong><ul>'+''.join(
        f'<li><a href="#{key}">{title}</a></li>'
        for key,title in re.findall(r'<h2 id="([^"]+)">(.*?)</h2>',body)
    )+'</ul></div>'
    logo=base64.b64encode((ROOT/"assets/milstrip-app.png").read_bytes()).decode()
    html=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>MILSTRIP | Current operation and Phase 2</title><style>{CSS}</style></head><body>
<nav class="topbar" aria-label="Guide navigation"><div><a href="#1-what-exists-today">Current state</a><a href="#4-end-user-sop-current-development-app">User SOP</a><a href="#5-phase-2-published-app-two-production-periods">Phase 2</a></div><button type="button" onclick="window.print()">Print / save PDF</button></nav>
<header class="cover"><img src="data:image/png;base64,{logo}" alt="MILSTRIP Intake App icon"><div><span class="eyebrow">Operations &amp; architecture / 2026</span><h1>One workflow.<br>Two production periods.</h1><p>Current development app · Azure SQL first · PostgreSQL after migration acceptance</p></div></header>
<main><aside aria-label="Contents">{toc}</aside><article>{body}</article><footer>Internal working document · Status date {DATE} · Prepared from repository evidence and the owner's Phase 2 assumptions. Production changes remain gated.</footer></main></body></html>'''
    (OUT/"index.html").write_text(html,encoding="utf-8")


def render_pdf(browser_path):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=browser_path,headless=True)
        page=browser.new_page(viewport={"width":1440,"height":1050},device_scale_factor=1)
        errors=[]
        page.on("pageerror",lambda e:errors.append(str(e)))
        page.goto((OUT/"index.html").as_uri(),wait_until="load")
        page.evaluate("document.fonts.ready")
        assert page.locator("figure svg").count()==7
        # Validate rendered text against its node box and the chart viewport.
        problems=page.evaluate('''() => {const bad=[]; document.querySelectorAll('svg').forEach(svg=>{
          const vb=svg.viewBox.baseVal;
          svg.querySelectorAll('text').forEach(t=>{const b=t.getBBox(); if(b.x<0||b.x+b.width>vb.width+1||b.y<0||b.y+b.height>vb.height+1)bad.push('viewport: '+t.textContent);});
          svg.querySelectorAll('[data-node]').forEach(g=>{const r=g.querySelector('rect').getBBox();g.querySelectorAll('text').forEach(t=>{const b=t.getBBox();if(b.x+b.width>r.x+r.width-8||b.y+b.height>r.y+r.height-4)bad.push(g.dataset.node+': '+t.textContent);});});
        });return bad;}''')
        assert not problems,problems
        assert not errors,errors
        broken_anchors=page.evaluate("Array.from(document.querySelectorAll('a[href^=\"#\"]')).filter(a=>!document.getElementById(decodeURIComponent(a.hash.slice(1)))).map(a=>a.hash)")
        assert not broken_anchors,broken_anchors
        page.screenshot(path=str(OUT/"preview.png"),full_page=False)
        page.pdf(path=str(OUT/"MILSTRIP-current-and-phase2.pdf"),print_background=True,prefer_css_page_size=True,display_header_footer=True,header_template='<span></span>',footer_template='<div style="font-size:8px;width:100%;padding:0 45px;color:#60758c;display:flex;justify-content:space-between"><span>MILSTRIP · September 23, 2026 · Current vs proposed</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>')
        for width in [390,1440]:
            page.set_viewport_size({"width":width,"height":1000})
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth+1"),f"Page overflow at {width}px"
        browser.close()
    print("PASS: seven diagrams, SVG text bounds, HTML anchors, browser rendering and responsive overflow.")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf",action="store_true")
    parser.add_argument("--browser",default=str(Path(os.environ.get("LOCALAPPDATA",""))/"BraveSoftware/Brave-Browser/Application/brave.exe"))
    args=parser.parse_args()
    DIAGRAMS.mkdir(parents=True,exist_ok=True)
    manifest=charts()
    (OUT/"diagram-manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    build_html()
    if args.pdf:render_pdf(args.browser)
    print(f"Built {OUT/'index.html'}")


if __name__=="__main__":
    main()
