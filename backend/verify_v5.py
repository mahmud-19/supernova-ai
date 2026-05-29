"""End-to-end verification of v5 changes."""
import time, requests, base64, io

BASE = "http://localhost:8000/api"

# Wait for server
for _ in range(10):
    try:
        requests.get(f"http://localhost:8000/health", timeout=2).raise_for_status()
        break
    except Exception:
        time.sleep(1)

# ---- Sonologist login ----
r = requests.post(f"{BASE}/auth/login", json={"identifier": "sonologist@supernova.com", "password": "12345678", "role": "sonologist"})
r.raise_for_status()
s_token = r.json()["access_token"]
s_headers = {"Authorization": f"Bearer {s_token}"}
print("PASS: Sonologist login")

# ---- Upload with PT- prefix patient ID ----
with open("sample.png", "rb") as f:
    r = requests.post(f"{BASE}/cases/upload", headers=s_headers,
                      files={"file": ("sample.png", f, "image/png")},
                      data={"patient_id": "PT-99999", "patient_name": "v5 Test", "age": "30",
                            "gender": "male", "exam_date": "2026-05-26", "sonologist_note": "v5 note"})
r.raise_for_status()
case = r.json()
case_id = case["id"]
assert case["patient_id"] == "PT-99999", f"patient_id: {case['patient_id']}"
assert case["status"] == "pending", f"status after upload should be pending, got {case['status']}"
print(f"PASS: Upload -> status=pending, patient_id={case['patient_id']}")

# ---- Run inference -> status stays pending ----
r = requests.post(f"{BASE}/cases/{case_id}/infer", headers=s_headers)
r.raise_for_status()
r2 = requests.get(f"{BASE}/cases/{case_id}", headers=s_headers)
assert r2.json()["status"] == "pending", f"After infer: {r2.json()['status']}"
print("PASS: After inference -> status still pending")

# ---- Submit -> status becomes in_review ----
r = requests.post(f"{BASE}/cases/{case_id}/submit", headers=s_headers)
r.raise_for_status()
assert r.json()["status"] == "in_review", f"After submit: {r.json()['status']}"
print(f"PASS: After submit -> status=in_review")

# ---- Check sonologist dashboard shows in_review ----
r = requests.get(f"{BASE}/cases/mine", headers=s_headers)
r.raise_for_status()
my_case = next((c for c in r.json() if c["id"] == case_id), None)
assert my_case is not None
assert my_case["status"] == "in_review"
print("PASS: Sonologist /cases/mine shows status=in_review")

# ---- Reviewer sees it ----
r = requests.post(f"{BASE}/auth/login", json={"identifier": "reviewer@supernova.com", "password": "12345678", "role": "expert_reviewer"})
r.raise_for_status()
rev_token = r.json()["access_token"]
rev_headers = {"Authorization": f"Bearer {rev_token}"}
print("PASS: Reviewer login")

r = requests.get(f"{BASE}/cases", headers=rev_headers)
r.raise_for_status()
all_cases = r.json()
rev_case = next((c for c in all_cases if c["id"] == case_id), None)
assert rev_case is not None, "Case not visible to reviewer"
assert rev_case["status"] == "in_review"
assert rev_case["patient_id"] == "PT-99999"
assert rev_case["patient_name"] == "v5 Test"
assert rev_case["sonologist_note"] == "v5 note"
print(f"PASS: Reviewer sees case (status=in_review, patient details present)")

# ---- Annotate + Final Approval -> status becomes approved ----
from PIL import Image
img = Image.new("L", (512, 512), 0)
buf = io.BytesIO(); img.save(buf, format="PNG")
mask_b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

r = requests.post(f"{BASE}/cases/{case_id}/annotate", headers=rev_headers,
                  json={"contour_json": [], "mask_png_base64": mask_b64, "reviewer_note": "looks fine"})
r.raise_for_status()
print("PASS: Annotate succeeded")

r = requests.post(f"{BASE}/cases/{case_id}/finalize", headers=rev_headers)
r.raise_for_status()
assert r.json()["status"] == "approved", f"After finalize: {r.json()['status']}"
print("PASS: After Final Approval -> status=approved")

# ---- Verify approved case NO longer shows Review button (status=approved -> not in_review) ----
r = requests.get(f"{BASE}/cases", headers=rev_headers)
approved_case = next((c for c in r.json() if c["id"] == case_id), None)
assert approved_case is not None, "Approved case should still be visible to reviewer"
assert approved_case["status"] == "approved"
print("PASS: Approved case still visible to reviewer (status=approved, no Review button logic correct)")

# ---- Verify ONLY in_review + approved appear in reviewer list (not plain pending) ----
# Upload a second case but don't submit it
with open("sample.png", "rb") as f:
    r2 = requests.post(f"{BASE}/cases/upload", headers=s_headers,
                       files={"file": ("sample.png", f, "image/png")},
                       data={"patient_id": "PT-00001", "patient_name": "Not Submitted"})
r2.raise_for_status()
pending_case_id = r2.json()["id"]
requests.post(f"{BASE}/cases/{pending_case_id}/infer", headers=s_headers)

r = requests.get(f"{BASE}/cases", headers=rev_headers)
visible_ids = [c["id"] for c in r.json()]
assert pending_case_id not in visible_ids, "Plain pending case should NOT be visible to reviewer"
print(f"PASS: Plain pending case NOT visible to reviewer (only in_review/approved shown)")

print("\nAll v5 verifications PASSED!")
