# pitchline
Football analytics pipeline: raw event data → canonical schema → match and scouting reports. First use case: Euro 2024 (StatsBomb open data).

## Data sources and credits
- **Event data:** [StatsBomb open data](https://github.com/statsbomb/open-data), Euro 2024. Every chart and report credits StatsBomb as the data source, as their user agreement requires.
- **xT grid:** Karun Singh, ["Introducing Expected Threat (xT)"](https://karun.in/blog/expected-threat.html). The published 12 × 8 grid, fitted on the 2017/18 Premier League season, is stored unchanged in `src/pitchline/metrics/xt_grid.json`.
- **SPADL vocabulary:** action types, results and body parts follow [socceraction](https://github.com/ML-KULeuven/socceraction) (MIT licence), from Decroos et al., "Actions Speak Louder than Goals: Valuing Player Actions in Soccer" (KDD 2019).
