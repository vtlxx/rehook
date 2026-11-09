You are a direct-response copywriter writing new hooks for a winning video ad on Meta (US market). A hook is the first ~3 seconds: the voice-over line, the on-screen text and the first frame. The rest of the ad stays exactly as it is.

Brand brief:
{{brand}}

Analysis of the winning ad:
{{parsed}}

The unchanged part of the ad (after 3 seconds):
{{body}}

Write hooks for THIS angle:
{{angle}}

Other angles are covered separately. Don't drift into them:
{{other_angles}}

Top-performing launched hooks (higher ROMI), for what works:
{{best_examples}}

Underperformed (lowest ROMI). Do not imitate these:
{{worst_examples}}

Already used. Do not repeat or paraphrase these:
{{avoid}}

Write exactly {{k}} variants for this angle. For each:
- `hook_type`: one of {{hook_types}}. Use a different hook type for every variant within this angle.
- `hook_vo`: the voice-over for the first ~3 seconds, at most {{vo_max}} words.
- `on_screen_text`: the text on screen, at most {{onscreen_max}} words.
- `first_frame`: one sentence describing the first frame for the designer. It must match the angle's `frame_format`.
- `bridge_line`: a new first line for the main part, only if the hook doesn't flow into the unchanged part above. Otherwise use an empty string.

Rules:
- Use only the facts and the offer from the brief; no other prices than the one in the offer; nothing from `banned_claims` or `banned_words`.
- Tone: follow the brief's `tone`. No hype, no ALL CAPS.
- Make every variant a genuinely different idea, not a rewording of another one.

Reply with JSON only, in exactly this shape:

```json
{
  "variants": [
    {"hook_type": "question", "hook_vo": "...", "on_screen_text": "...", "first_frame": "...", "bridge_line": ""}
  ]
}
```
