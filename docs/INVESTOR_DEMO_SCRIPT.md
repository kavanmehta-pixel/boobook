# Investor demo script

## 60-second version

1. "This is not claiming live dark-vessel RF detection yet. This is the validation layer."
2. Open `artifacts/Boobook_Source_Data_Validation_Dashboard.html`.
3. Show AIS rows, vessels, alerts and tracks.
4. Click through high-risk alerts: AIS gap, impossible speed, loitering, rendezvous candidate.
5. Explain: "These are the same workflows that become materially stronger once we add independent RF detections."
6. Show `boobook coverage` output: choke-point cluster logic, not fantasy regional blanket coverage.
7. Show `boobook rf-demo` output: deterministic TDOA planning simulation, not field proof.
8. Close with next milestone: live Sydney Harbour AIS capture via RTL-SDR, then controlled 3-node TDOA.

## Exact language

> Boobook starts as an AIS source-data validation engine. It flags behaviour that a maritime enforcement analyst would want to review. The passive RF layer is the next proof point: instead of only saying AIS is suspicious, we add independent RF evidence that something was physically emitting in the area.

## Do not say

- "We detect all dark vessels."
- "This is live RF."
- "This alert proves illegal activity."
- "DIDG pays for all R&D."
