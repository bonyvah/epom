import json
import random
import urllib.parse


def lambda_handler(event, context):
    key = urllib.parse.unquote_plus(event["Records"][0]["s3"]["object"]["key"])

    print("[SCAN] Starting virus scan...")
    print(f"[SCAN] File: {key}")
    scan_result = random.choice(["clean", "clean", "clean", "quarantined"])
    print(f"[SCAN] Result: {scan_result}")

    return {"statusCode": 200, "body": json.dumps({"scan_result": scan_result})}