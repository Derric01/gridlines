# Short actual-application walkthrough

The current preferred media is the **2:10 version with full local voice conversion**, described in [`full-clone.md`](full-clone.md). Every narration section uses the approved reference voice profile; it is a synthetic approximation. Earlier recorded-clip and catalog-voice versions remain as references.

An earlier local media revision is approximately **2:15**, with an 11.4-second user-confirmed recorded passage inserted near the beginning. In that earlier version, the surrounding narration is retained, app footage is retimed at that passage, and optional captions are updated in `captions-with-recorded-voice.srt`. That audio edit was processed locally without cloning or uploading the recording. The export passed full decode and an audio comparison confirmed the recorded clip is present. Personal recordings and generated MP4s are not committed here.

The revised video is 2:10 and shows the running deployment at https://gridlines-beta.vercel.app/ throughout. Real interactions include selecting January 10, opening the hourly values and publication table, navigating Daily accuracy, opening a row, selecting January 31 for February 1 delivery, and reading Method & sources.

The revision removes added “Client demo” and “Technical review” banners, title cards, code slides and presentation-style closing cards. The user explicitly approved replacing the local Windows voice with a more natural Indian-English catalog voice from HeyGen. Narration and editing are AI-assisted; no voice clone or personal presenter is used.

- `narration.md` contains the shorter script.
- `captions.srt` contains subtitles aligned to provider word timestamps.
- The separate generated MP4 contains an optional English subtitle track; no captions are burned over the application.

Validation: the final video is 1920 × 1080 at 24 fps and exactly 130 seconds. Full audio/video decoding passed. The edit uses 1,893 genuine application capture frames; representative frames were inspected across all demonstrated pages. Measured integrated loudness is -16.04 LUFS and true peak is -1.76 dBTP.

The previous application validation remains unchanged: 16 Python tests and four CSV tests passed. No application code or tests changed in this media revision. No deployment, merge, YouTube upload or assignment submission was performed.
