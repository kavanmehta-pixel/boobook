# 90-day validation plan

## Phase 1 — source data proof (weeks 1-2)

- Download AMSA/CTS monthly vessel traffic dataset.
- Run `ninox validate-ais`.
- Generate dashboard and manually inspect flagged tracks.
- Record 5-10 alert examples with screenshots and source-row evidence.

## Phase 2 — live AIS proof (weeks 3-5)

- Buy RTL-SDR v4, marine VHF/AIS antenna and basic LNA/filter if needed.
- Run `rtl-ais` locally around Sydney Harbour.
- Decode AIVDM/AIVDO sentences with `pyais`.
- Persist local live AIS rows into the same canonical schema.
- Show the dashboard fed by live local RF/AIS reception.

## Phase 3 — controlled TDOA proof (weeks 6-9)

- Use 3 receivers and a known test emitter / known AIS vessel where lawful.
- Timestamp and compare arrivals.
- Measure actual error distribution, not just simulation.
- Produce a one-page RF validation note.

## Phase 4 — customer validation (weeks 8-12)

- Speak to AFMA/ABF/port/security/fisheries operators.
- Ask which alerts would change their workflow.
- Do not pitch as solved; pitch as a validation and cueing layer.
- Convert the strongest feedback into a paid pilot proposal.
