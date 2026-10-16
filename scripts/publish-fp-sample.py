"""Publish only the synthetic sample, preserving the actual live homepage routing."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import urllib.request
import urllib.error

def aws(*args):
    return json.loads(subprocess.check_output(["aws", *args, "--output", "json"], text=True))

root = Path(__file__).resolve().parents[1]
name = "simy-site-prod-redirect"
bucket = os.environ["SITE_S3_BUCKET"]
assert bucket == "simy-site-prod", "Unexpected production bucket"
guard = (root / "infra/cloudfront-functions/fp-sample-auth.js").read_text()
with tempfile.TemporaryDirectory() as folder:
    source = Path(folder) / "function.js"
    live = aws("cloudfront", "get-function", "--name", name, "--stage", "LIVE", str(source))
    code = source.read_text()
    if "// BEGIN FP SAMPLE AUTH" in code:
        start = code.index("// BEGIN FP SAMPLE AUTH")
        end = code.index("// END FP SAMPLE AUTH", start) + len("// END FP SAMPLE AUTH")
        code = code[:start] + guard.rstrip() + code[end:]
    else:
        marker = "function handler(event) {"
        assert code.count(marker) == 1, "Unknown live handler; do not overwrite routing"
        code = code.replace(marker, guard + "\n" + marker + "\n  var sampleResult = protectFpSample(event.request);\n  if (sampleResult) return sampleResult;")
    assert len(code.encode()) <= 10240, "CloudFront function exceeds size limit"
    source.write_text(code)
    dev = aws("cloudfront", "describe-function", "--name", name, "--stage", "DEVELOPMENT")
    updated = aws("cloudfront", "update-function", "--name", name, "--if-match", dev["ETag"],
        "--function-config", json.dumps(live["FunctionSummary"]["FunctionConfig"]),
        "--function-code", "fileb://" + str(source))
    aws("cloudfront", "publish-function", "--name", name, "--if-match", updated["ETag"])

# Wait for actual edge denial before sending any sample bytes to S3.
url = "https://simy.one/samples/fp-management/"
for attempt in range(30):
    try:
        urllib.request.urlopen(url, timeout=15)
    except urllib.error.HTTPError as error:
        if error.code == 401 and 'SIMY sample' in error.headers.get('WWW-Authenticate', ''):
            break
    time.sleep(5)
else:
    raise RuntimeError("Edge protection not observed; no sample objects uploaded")

for filename, content_type in [("index.html", "text/html; charset=utf-8"), ("app.js", "application/javascript"), ("app.css", "text/css")]:
    aws("s3api", "put-object", "--bucket", bucket, "--key", "samples/fp-management/" + filename,
        "--body", str(root / "samples/fp-management" / filename),
        "--content-type", content_type, "--cache-control", "no-store")
aws("cloudfront", "create-invalidation", "--distribution-id", os.environ["SITE_CF_DISTRIBUTION_ID"],
    "--paths", "/samples/fp-management", "/samples/fp-management/*")
print("Published only the protected synthetic sample; authenticated browser check remains required.")
