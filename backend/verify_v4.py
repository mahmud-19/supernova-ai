"""End-to-end verification of v4 changes."""
import sys
import requests

BASE = "http://localhost:8000/api"

# -- Sonologist flow --
r = requests.post(f"{BASE}/auth/login", json={"identifier": "sonologist@supernova.com", "password": "12345678", "role": "sonologist"})
r.raise_for_status()
s_token = r.json()["access_token"]
s_headers = {"Authorization": f"Bearer {s_token}"}
print("PASS: Sonologist login")

# Check /cases/mine returns empty list for fresh sonologist
r = requests.get(f"{BASE}/cases/mine", headers=s_headers)
r.raise_for_status()
mine_before = r.json()
print(f"PASS: /cases/mine returns {len(mine_before)} case(s) (expected 0 initially or from previous runs)")

# Upload a case with patient fields
with open("sample.png", "rb") as f:
    r = requests.post(f"{BASE}/cases/upload", headers=s_headers, files={"file": ("sample.png", f, "image/png")},
                      data={"patient_id": "PT-TEST", "patient_name": "Jane Smith", "age": "42", "gender": "female",
                            "exam_date": "2026-05-26", "sonologist_note": "Test case for v4 verification"})
r.raise_for_status()
case = r.json()
case_id = case["id"]
assert case["patient_id"] == "PT-TEST", f"patient_id mismatch: {case['patient_id']}"
assert case["patient_name"] == "Jane Smith", f"patient_name mismatch: {case['patient_name']}"
assert case["age"] == 42, f"age mismatch: {case['age']}"
assert case["gender"] == "female"
assert case["submitted"] == False
print(f"PASS: Upload case {case_id} with patient data: patient_id={case['patient_id']}, patient_name={case['patient_name']}")

# Run inference
r = requests.post(f"{BASE}/cases/{case_id}/infer", headers=s_headers)
r.raise_for_status()
infer = r.json()
conf = round(infer["confidence_score"] * 100)
print(f"PASS: Inference run, confidence={conf}%")

# Submit for review
r = requests.post(f"{BASE}/cases/{case_id}/submit", headers=s_headers)
r.raise_for_status()
submitted = r.json()
assert submitted["submitted"] == True, "submitted should be True"
assert submitted["status"] == "in_review", f"status should be in_review, got {submitted['status']}"
print(f"PASS: Case submitted: submitted={submitted['submitted']}, status={submitted['status']}")

# Verify it appears in /cases/mine
r = requests.get(f"{BASE}/cases/mine", headers=s_headers)
r.raise_for_status()
mine_after = r.json()
my_case = next((c for c in mine_after if c["id"] == case_id), None)
assert my_case is not None, "Case not found in /cases/mine"
print(f"PASS: Case appears in /cases/mine with {len(mine_after)} total case(s)")

# -- Expert Reviewer flow --
r = requests.post(f"{BASE}/auth/login", json={"identifier": "reviewer@supernova.com", "password": "12345678", "role": "expert_reviewer"})
r.raise_for_status()
rev_token = r.json()["access_token"]
rev_headers = {"Authorization": f"Bearer {rev_token}"}
print("PASS: Reviewer login")

# Reviewer sees submitted cases
r = requests.get(f"{BASE}/cases", headers=rev_headers)
r.raise_for_status()
all_cases = r.json()
rev_case = next((c for c in all_cases if c["id"] == case_id), None)
assert rev_case is not None, f"Case {case_id} not visible to reviewer"
assert rev_case["status"] == "in_review"
assert rev_case["patient_id"] == "PT-TEST"
print(f"PASS: Reviewer sees {len(all_cases)} submitted case(s); our case is present (status=in_review)")

# -- Annotate with reviewer_note --
import base64
# Create a tiny 512x512 black PNG mask
try:
    from PIL import Image
    import io
    img = Image.new("L", (512, 512), 0)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    mask_b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
except ImportError:
    # Fallback: minimal valid 1x1 PNG
    mask_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAAAAAA6fptVAAAACklEQVQI12NgAAAAAgAB4iG8MwAAAABJRU5ErkJggg=="

r = requests.post(f"{BASE}/cases/{case_id}/annotate", headers=rev_headers,
                  json={"contour_json": [], "mask_png_base64": mask_b64, "reviewer_note": "Boundary looks clear"})
r.raise_for_status()
print("PASS: Annotate with reviewer_note succeeded")

# Check reviewer_note saved
r = requests.get(f"{BASE}/cases/{case_id}", headers=rev_headers)
r.raise_for_status()
detail = r.json()
assert detail["reviewer_note"] == "Boundary looks clear", f"reviewer_note mismatch: {detail['reviewer_note']}"
print(f"PASS: reviewer_note saved: '{detail['reviewer_note']}'")

print("\nAll v4 verifications passed!")
