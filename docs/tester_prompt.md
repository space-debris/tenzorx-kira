# Comprehensive Production Test Scenario for KIRA Platform

> **Tester Persona:** You are a senior Risk Manager at an Indian NBFC transitioning fully into the AI-first KIRA Underwriting system. You will extensively test the platform strictly across UI elements, edge cases, data flows from image to the final document exports, and stress scenarios without hand-holding. **Act autonomously, use the web interface as much as possible, and do not simulate tests; execute them globally.**

---

### Phase A: End-to-End Application Integrity (Origination to Assessment)
**Objective:** Verify that the system handles real-world imperfect data to scaffold an assessment and link it to a persistent database case seamlessly.
1. **Case Creation:** Go to the web dashboard and create a new tracking case for a borrower (e.g., "Maha-Laxmi Supermarket", Owner: "Anil Sharma"). Look at the dropdowns and visual interface mapping to the backend. Is it seamless?
2. **AI Underwriting:** Launch the "Run AI Assessment" from the case detail. Provide real, imperfect images representing an unorganized general store to test the Gemini spatial processing. Provide latitude/longitude to test area extraction logic. 
3. **Validation:** Review the output. Is the risk score generated deterministic? Is the bounding box/shelf density mathematically rigorous? Link it explicitly back to your case. 

### Phase B: Decisioning, Access, and Overrides
**Objective:** Verify access control paradigms and override integrity. 
4. **Data Verification:** Confirm that the persistent case inherits the details from the transient AI run.  
5. **System Override:** Challenge the AI. Assume you found external bureau data that changes things. Perform a manual **Underwriting Override** using the web interface to change the credit allocation (Amount & EMI). 
6. **Audit Check:** Ensure the system recorded `underwriting_overridden` against the exact user payload. You cannot afford shadow changes in a live banking environment!

### Phase C: Portfolio & Compliance (Post-Sanction)
**Objective:** Confirm KIRA scales up across an org and successfully maps legal documents.
7. **Document Assembly:** Export the deterministic compliance bundle for your approved case. 
8. **Legal Fidelity:** Analyze the exported payload (JSON/Markdown bundles from the "Documents" module). Is everything generated with 100% deterministic fidelity with no hallucination injected across the transaction variables? (Feel free to run `backend/scripts/generate_sanction_letter.py <case_id>` locally to verify India-standard physical representation).
9. **Portfolio Health:** Check the unified Portfolio UI grid map. Does it correctly integrate and aggregate the new case volume to active exposure limit KPI? Check Cohorts.

### Phase D: Advance Intelligence & Fraud Monitoring
**Objective:** Run dynamic monitoring to prove out Phase 14 AI heuristics.
10. **Behavioral Fraud Validation:** Provide a mock bank statement showing extreme standard volume (baseline), and then upload a subsequent statement for the same case with 300% Supplier Spikes.
11. **Outcome:** Does the UI correctly flag a "Behavioral Anomaly Detected"? Is the dynamic stress testing score directly updated in the monitoring tab? Run the "Scenario Simulator" inside the borrower's Case Detail page to shock their underlying revenue by 30%. Show your final verdict.

---
**Instruction to AI:** Treat this prompt as a master production-readiness check. Go step-by-step through the live application. Stop automatically if the schema crashes or the UI refuses navigation. Output a professional system review when finished.
