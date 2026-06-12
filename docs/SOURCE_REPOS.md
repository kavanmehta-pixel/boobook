# Source data and open-source repo map

These are the public sources Boobook should anchor to.

| Layer | Source / repo | Why it matters | MVP use |
|---|---|---|---|
| Australian AIS source data | AMSA Spatial / Digital Data — Craft Tracking System datasets | CTS is AMSA's vessel traffic database and includes terrestrial + satellite shipborne AIS extracts for Australian regions. | Primary public/source-data validation input. |
| AIS decoding library | `M0r13n/pyais` | Python AIS/NMEA encode/decode library; useful once live NMEA sentences are available. | Optional hardware extra, not required for CSV validation. |
| Live SDR AIS receiver | `dgiardini/rtl-ais` | Receives AIS via RTL-SDR and outputs AIVDM/AIVDO NMEA sentences. | First live RF/AIS hardware proof point. |
| GNU Radio AIS decoder | `bistromath/gr-ais` | GNU Radio AIS decoder for deeper SDR pipelines. | Later RF engineering pathway. |
| AIS database/scaling | `AISViz/AISdb` | Open-source AIS database management for storing/retrieving/analyzing/visualizing AIS data. | Later scale-up once raw AIS volumes become large. |

## Recommended implementation sequence

1. Public/source AIS CSV validation using AMSA/CTS files.
2. Local live AIS receive with `rtl-ais` and cheap RTL-SDR hardware.
3. Decode/structure live NMEA with `pyais`.
4. Persist larger datasets in SQLite/Postgres or evaluate AISdb.
5. Move from AIS-only analytics to RF/AIS mismatch detection after legal and hardware validation.
