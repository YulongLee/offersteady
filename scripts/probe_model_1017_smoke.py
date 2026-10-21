"""Bounded synthetic connectivity probe; feed to remote python3 via stdin.

Only reads the pinned running image's Settings and sends two provider requests.
Never writes configuration, imports app.deps, creates sessions or logs responses.
"""
from __future__ import annotations

import json
import subprocess
import sys

TARGET = "deepseek-v4.1-flash-1017"
BASELINES = {
    "cn": ("compose-backend-1", "sha256:2f2c89359d2268c460dabad38a4f9466e2af5610e730a94ded797586ef4c5e88"),
    "global": ("offersteady-global-backend-1", "sha256:f6a4dad4fb27222ca79f1fb5a86c23267093c741b4536c64ca76b83ac096ec19"),
}
VALIDATION_HELPERS = r'''
def vision_answer_correct(value):
    import re
    if not isinstance(value,str) or len(value)>200:
        return False
    text=value.strip().replace("＋","+").replace("＝","=")
    for delimiter in ("**", "$"):
        if text.startswith(delimiter) and text.endswith(delimiter) and len(text)>2*len(delimiter):
            text=text[len(delimiter):-len(delimiter)].strip()
    if re.fullmatch(r"(?:17\s*\+\s*25\s*=\s*)?42[.!。]?",text):
        return True
    return bool(re.fullmatch(r"(?:(?:The\s+)?answer\s+is\s*:?\s*|答案[是为：:]\s*)42[.!。]?",text,re.I))
'''
exec(VALIDATION_HELPERS)


def sanitize_record(row):
    if not isinstance(row, dict):
        raise ValueError("invalid record")
    if "operation" not in row:
        if set(row)!={"passed","checks","productionChanged"} or type(row["passed"]) is not bool or type(row["checks"]) is not int or row["checks"]!=2 or row["productionChanged"] is not False:
            raise ValueError("invalid summary")
        return row
    allowed={"operation","model","syntheticOnly","passed","httpStatus","expectedAnswerMatched",
             "exactFormatMatched","complete","usage","error","seconds","syntheticAnswerIntegers"}
    if set(row)-allowed or row.get("operation") not in {"text","vision"} or row.get("model")!=TARGET or row.get("syntheticOnly") is not True:
        raise ValueError("invalid operation")
    for name in ("passed","expectedAnswerMatched","exactFormatMatched","complete"):
        if name in row and type(row[name]) is not bool:
            raise ValueError("invalid bool")
    if "passed" not in row or type(row.get("seconds")) not in (int,float) or not 0<=row["seconds"]<=180:
        raise ValueError("invalid metrics")
    if "httpStatus" in row and (type(row["httpStatus"]) is not int or not 100<=row["httpStatus"]<=599):
        raise ValueError("invalid status")
    if row["passed"] and (row.get("httpStatus")!=200 or row.get("expectedAnswerMatched") is not True or row.get("complete") is not True or "error" in row):
        raise ValueError("inconsistent success")
    if "error" in row and row["error"] not in {"endpoint_not_configured","provider_http_error","ReadTimeout","ConnectTimeout","ConnectError","ReadError","RemoteProtocolError","HTTPError","KeyError","IndexError","TypeError","ValueError","JSONDecodeError","RuntimeError","AttributeError"}:
        row={**row,"error":"probe_error"}
    if "usage" in row and (not isinstance(row["usage"],dict) or set(row["usage"])-{"prompt_tokens","completion_tokens","total_tokens"} or any(type(v) is not int or not 0<=v<=10_000_000 for v in row["usage"].values())):
        raise ValueError("invalid usage")
    if "syntheticAnswerIntegers" in row and (not isinstance(row["syntheticAnswerIntegers"],list) or len(row["syntheticAnswerIntegers"])>6 or any(type(v) is not int or not -10_000_000<v<10_000_000 for v in row["syntheticAnswerIntegers"])):
        raise ValueError("invalid diagnostic")
    return row


INNER = VALIDATION_HELPERS + r'''
import base64
import io
import json
import logging
import re
import time
import httpx
from PIL import Image, ImageDraw, ImageFont
from app.core.config import Settings
logging.disable(logging.CRITICAL)
target = "deepseek-v4.1-flash-1017"
settings = Settings()
picture = Image.new("RGB", (900, 280), "white")
draw = ImageDraw.Draw(picture)
font = ImageFont.load_default(size=48)
draw.text((36, 65), "17 + 25 = ?", fill="black", font=font)
buffer = io.BytesIO()
picture.save(buffer, format="JPEG", quality=72, progressive=True)
url = "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
cases = (
    ("text", settings.chat_qwen_base_url, settings.chat_qwen_api_key,
     [{"role":"user", "content":"Reply with exactly MODEL1017_OK and nothing else."}], "MODEL1017_OK"),
    ("vision", settings.screenshot_vision_base_url, settings.screenshot_vision_api_key,
     [{"role":"user", "content":[{"type":"text", "text":"Solve the arithmetic in this image. Reply with the integer result only."},
                                   {"type":"image_url", "image_url":{"url":url}}]}], "42"),
)
passed = True
for role, base, key, messages, expected in cases:
    started = time.monotonic()
    row = {"operation":role, "model":target, "syntheticOnly":True}
    if not base or not key:
        row.update(passed=False, error="endpoint_not_configured")
    else:
        try:
            with httpx.Client(timeout=httpx.Timeout(30, connect=5)) as client:
                response=client.post(base.rstrip("/")+"/chat/completions",
                    headers={"Authorization":"Bearer "+key},
                    json={"model":target,"messages":messages,"enable_thinking":False,"stream":False,"max_tokens":64})
            row["httpStatus"] = response.status_code
            if response.status_code == 200:
                data=response.json()
                choice=data["choices"][0]
                content=choice["message"]["content"].strip()
                integers=re.findall(r"(?<![0-9.])-?\d+(?![0-9.])",content)
                answer_correct=(content==expected if role=="text" else vision_answer_correct(content))
                row.update(passed=(answer_correct and choice.get("finish_reason")=="stop"),
                           expectedAnswerMatched=answer_correct, exactFormatMatched=content==expected,
                           complete=choice.get("finish_reason")=="stop")
                if role=="vision":
                    row["syntheticAnswerIntegers"]=[int(x) for x in integers[:6] if len(x)<8]
                usage=data.get("usage",{})
                row["usage"]={k:usage[k] for k in ("prompt_tokens","completion_tokens","total_tokens") if type(usage.get(k)) is int}
            else:
                row.update(passed=False,error="provider_http_error")
        except Exception as error:
            row.update(passed=False,error=type(error).__name__)
    row["seconds"] = round(time.monotonic()-started,3)
    passed = passed and row.get("passed",False)
    print(json.dumps(row,sort_keys=True),flush=True)
print(json.dumps({"passed":passed,"checks":2,"productionChanged":False}),flush=True)
raise SystemExit(0 if passed else 1)
'''

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in BASELINES:
        raise SystemExit("expected cn or global")
    region = sys.argv[1]
    container, pinned = BASELINES[region]
    identity = subprocess.check_output(["docker", "inspect", "--format", "{{.Id}} {{.Image}}", container], text=True, timeout=15).strip().split()
    if len(identity)!=2 or identity[1] != pinned:
        print(json.dumps({"region":region,"passed":False,"error":"runtime_image_drift"}),flush=True)
        return 2
    result = subprocess.run(["docker","exec","-i","-w","/app/apps/backend",identity[0],"python","-B","-"],
                            input=INNER,text=True,capture_output=True,timeout=90)
    try:
        lines=result.stdout.splitlines()
        if len(lines)!=3 or len(result.stdout)>8192:
            raise ValueError("invalid record count")
        rows=[sanitize_record(json.loads(line)) for line in lines]
        if [row.get("operation") for row in rows]!=["text","vision",None] or rows[-1]["passed"]!=all(row["passed"] for row in rows[:-1]):
            raise ValueError("inconsistent summary")
    except (ValueError,TypeError,KeyError):
        print(json.dumps({"region":region,"passed":False,"error":"unexpected_probe_output"}),flush=True)
        return 2
    for row in rows:
        print(json.dumps({"region":region,**row},sort_keys=True),flush=True)
    return result.returncode or (0 if rows[-1]["passed"] else 1)


if __name__=="__main__":
    raise SystemExit(main())
