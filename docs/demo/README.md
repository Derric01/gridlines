# Gridline demonstration

The preferred revision is now the **2:10 actual-application walkthrough** in [`short/`](short/README.md). It uses fresh recordings of the running deployment, a conversational Indian-English HeyGen voice and optional captions. Added presentation banners, title cards and code slides have been removed. The earlier 9:30 materials below are retained as the full-length reference.

This folder contains the timecoded narration, English subtitles and production plan for a 9:30 demonstration: a 4:50 client walkthrough followed by a 4:40 technical review. The final user preference is narration only, using a local Indian-English synthetic voice. No personal presenter or voice clone is used.

The MP4 is a separate generated deliverable and is not committed here. It combines genuine captured views from https://gridlines-beta.vercel.app/ with readable excerpts from reviewed commit `00a6cd043021be32e44cd5977700c5e6fd15e43b`. Captured UI frames are held during explanation; source excerpts are rendered with paths and line numbers. This is an edited demonstration, not an unedited live presentation.

## Accuracy

The live 15:30 scenario and local calculation agree on the rounded dashboard values: MAE 1,873 MW; RMSE 2,327 MW; bias +1,709 MW; WAPE 16.6%. Coverage is 744 matched hourly pairs with 1,488 half-hour actuals.

The review describes the actual archived-data implementation. It does not claim there is a committed data-download implementation, true half-hour forecast accuracy, proven source-population equivalence, or demonstrated financial savings. AI-assisted narration and assembly are disclosed.

## Validation performed

- Frontend production build completed, with 28 modules transformed.
- Existing Python suite: 16 passed after building the frontend.
- Existing CSV suite: 4 passed, 0 failed.
- Docker execution and a new deployment were not performed.

No application code or tests were changed. Do not infer that publishing or deploying is authorized by the presence of these materials. YouTube upload and assignment submission remain with the user.
