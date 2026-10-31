# Clinic service page: UI acceptance

Scope: /hp-management/clinic-service.html only. Preserve original clinic page and diagnosis / preview engines.

| Area | Standard |
| --- | --- |
| Main URL actions | Desktop input takes remaining width; button 220px. Equal upper/lower edges within 1px. Input at least 250px at supported widths. |
| Mobile URL actions | Full-width stacked input and button; 58px height, 17px text. |
| Desktop URL actions | 64px height, 18px text; visible focus outline. |
| Reading | Body 16px with 1.85 line height; secondary copy 14px. Illustration UI is not the main reading surface. |
| Contact | Input text 16px minimum, fields 56px minimum, textarea 120px; explicit labels, native required/email validation. |
| Story | Diagnosis → three service benefits → experience / discovery → pricing → migration / contact. Maintain existing content and functions. |
| Survey | Illustration and explanation first; graph below spans full block; source spans both columns. |
| Alignment | Matching input/button edges; equal desktop pricing card boundaries; consistent mobile outer margins. |
| Responsive | 320, 390, 768, 1024, 1440 CSS px: no document overflow, no collapsed fields. |
| Operation | Existing diagnosis, registration/PDF and preview handlers remain. No mock replaces production operations. |

Regression: scripts/check-clinic-service-layout.cjs (Playwright supplied via PLAYWRIGHT_MODULE; PAGE_URL optionally production).
