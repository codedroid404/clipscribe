# ClipScribe - Claude Code Project Instructions

## Mission
Build a privacy-first local automatic speech recognition application that accepts short video/audio files - especially iPhone `.MOV` screen recordings - and produces faithful, timestamped, exportable transcripts using `faster-whisper`.

The project began from a real personal workflow: useful advice and information is often trapped in short-form video audio. The previous workaround required playing the video on one phone while Notes transcribed it on another, which was slow, unreliable, and sometimes missed the beginning. ClipScribe should remove that friction.

## Correct terminology
This MVP is:
- a local AI application;
- an automatic speech recognition (ASR) application;
- a deterministic media-processing and inference pipeline;
- a Streamlit user interface over a local transcription service.

This MVP is **not**:
- RAG;
- an LLM application;
- an agent or agentic workflow;
- a multimodal LLM.

Do not use those labels unless later functionality actually satisfies them.

## Source of truth
Read `docs/ClipScribe_Project_Plan_v2.pdf` before planning or implementing. It contains the product story, requirements, architecture, trust controls, milestones, evaluation plan, and definition of done.

If the code, README, and plan conflict, stop and explain the conflict before changing behavior.

## Primary reference use cases
1. A three-minute screen-recorded advice video that triggered the project.
2. A screen recording of a corporate interview tip about answering “Tell me about yourself.”

These personal files must remain gitignored. Use them for manual local evaluation only. Use synthetic or redistributable fixtures for automated tests and public demos when rights are uncertain.

## Non-negotiable trust rules
- Preserve the raw ASR transcript as the source-of-truth output.
- Never silently rewrite the raw transcript with an LLM.
- Never use an LLM to guess inaudible or low-confidence speech.
- Do not claim hallucinations are eliminated. Mitigate, detect, flag, and test them.
- Prefer an explicit uncertainty warning over invented text.
- Preserve segment timestamps so users can replay uncertain regions.
- Keep any later cleaned transcript, summary, or research output clearly labeled as derived.

## Privacy and security
- Default operation is local-only and requires no API key.
- Do not send media or transcripts to external services.
- Use randomized temporary paths and delete uploaded media after success or failure.
- Do not log raw transcript content by default.
- Do not use `shell=True` with user-controlled values.
- Keep `samples/`, generated transcripts, and user media out of Git.

## MVP functionality
The completed MVP must:
- accept `.mov`, `.mp4`, `.m4a`, `.mp3`, and `.wav`;
- validate unsupported, empty, corrupt, oversized, or no-audio inputs;
- decode iPhone `.MOV` screen recordings locally;
- transcribe with `faster-whisper`;
- support model selection, language auto-detection/override, and optional VAD;
- display a timestamped raw transcript;
- surface suspicious, repeated, low-confidence, and no-speech segments;
- export TXT, JSON, SRT, and VTT;
- clean up temporary files;
- include automated tests and documented manual evaluation.

## Architecture boundaries
Use these modules or equivalent clear boundaries:
- `media.py`: validation, probing, decoding, audio extraction;
- `transcriber.py`: model loading and ASR inference;
- `models.py`: typed transcript and segment contracts;
- `diagnostics.py`: uncertainty, repetition, and no-speech checks;
- `exporters.py`: TXT/JSON/SRT/VTT formatting;
- `tempfiles.py`: safe lifecycle management;
- `service.py`: application orchestration;
- `app.py`: Streamlit presentation layer only.

Do not place all logic in `app.py`.

## Engineering standards
- Python 3.11+.
- Typed code using `pathlib` and dataclasses or Pydantic where useful.
- Use `faster-whisper` for ASR and Streamlit for the UI.
- Prefer a `src/` package layout.
- Keep dependencies minimal and version-bounded (upper/lower bounds; not exact pins or a lockfile).
- Use Ruff and pytest. Static type checking (mypy/Pyright) is a planned addition, not yet configured.
- Unit-test deterministic logic and exporters.
- Add integration coverage for the transcription service when practical.
- Provide actionable errors rather than raw stack traces in the UI.

## Required iterative workflow
Do not generate the entire application in one uncontrolled pass.

### M0 - Repository foundation
Create project structure, dependency management, lint/type/test configuration, `.gitignore`, and placeholder documentation. Verify the environment.

### M1 - CLI transcription spike
Prove that a real iPhone `.MOV` can be decoded and transcribed locally. Produce timestamped TXT and JSON. Stop for review.

### M2 - Core service layer
Implement typed media, ASR, diagnostics, temp-file, and exporter modules with tests. Stop for review.

### M3 - Streamlit MVP
Implement upload, settings, progress, transcript display, warnings, and downloads. Stop for review.

### M4 - Trust and evaluation
Create a repeatable manual evaluation workflow and document model/runtime/limitations. Stop for review.

### M5 - Portfolio polish
Improve README, architecture diagram, screenshots/demo instructions, privacy statement, limitations, and changelog.

After each milestone:
1. run the exact checks;
2. report the commands and results;
3. summarize changed files;
4. identify remaining risks;
5. wait for approval before broad work on the next milestone.

## Evaluation expectations
Evaluate at least:
- the corporate interview-advice clip;
- the three-minute advice clip;
- background music;
- fast speech or accent;
- long silence;
- corrupt or no-audio media.

Track processing time, real-time factor, observed transcription errors, repeated phrases, flagged uncertain segments, and manual corrections. Use word error rate only when a reliable reference transcript exists.

## Scope controls
Ask before adding:
- cloud services or hosted transcription APIs;
- authentication or user accounts;
- databases or telemetry;
- speaker diarization dependencies;
- LLM summarization;
- vector databases, RAG, web search, or agents;
- large framework abstractions.

Future transcript analysis may be called “LLM-assisted analysis.” Retrieval across many transcripts may be called “RAG.” Autonomous iterative research with tool selection may be called “agentic.” Do not conflate these with the MVP.

## Definition of done
A user can run `streamlit run app.py`, upload a real iPhone `.MOV`, click Transcribe, review a raw timestamped transcript with uncertainty warnings, and download TXT, JSON, SRT, and VTT. The default path requires no API key, temporary media is cleaned up, tests pass, setup is documented, and the project is accurately presented as a local ASR application.
