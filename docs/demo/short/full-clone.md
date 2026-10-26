# Full-video local voice clone

The latest local media is `gridline-full-cloned-voice.mp4`: a 2:10 actual-application walkthrough with **all nine narration sections converted using the user-approved voice reference**. This is an AI-generated approximation of the short recording, not an unedited human recording or a guarantee of an exact voice match.

The final pipeline uses [OpenVoice V2](https://github.com/myshell-ai/OpenVoice) locally on CPU. It extracts the target voice profile from the approved recording and converts the existing narration while retaining its words and timing. The actual application video stream and optional English captions are preserved. No avatars, presentation banners, title cards or generated UI screens are added.

The earlier authorized HeyGen attempt could not create a clone on the account's free tier. The local conversion made no additional voice upload. Personal recordings, voice profiles, model weights, generated audio and MP4s remain outside Git.

Validation of the finished file: 130 seconds, 1920 × 1080, 24 fps; full audio/video decoding passed; application frames matched the original at checked timestamps. Audio measured -16.02 LUFS integrated and -1.95 dBTP true peak. A local speech-recognition check was used as a content sanity check, and an AI audio watermark and metadata disclosure are included.

Application code and tests remain unchanged. The earlier 16 Python tests, four CSV tests and frontend production build remain the project validation evidence. No merge, deployment, YouTube upload or assignment submission was performed.
