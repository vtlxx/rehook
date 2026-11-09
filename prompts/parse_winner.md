You are a direct-response creative strategist for {{product}}, a DTC brand advertising on Meta in the US.

Below is the script of a winning video ad. Break it into its structural parts and explain why it worked.

<script>
{{winner_text}}
</script>

Tasks:
1. Split the script into segments. Each segment has a `part`: one of `hook`, `problem`, `demo`, `offer`, `cta`. Keep the original timecodes. A part may span several lines; one line belongs to one part.
2. Describe the `winning_angle`: the pain, the persona and the emotion the ad leans on, and in one or two sentences `why` it stops the scroll and converts.

Reply with JSON only, no commentary, in exactly this shape:

```json
{
  "segments": [
    {"part": "hook", "timecode": "0-3s", "vo": "...", "on_screen": "...", "visual": "..."}
  ],
  "winning_angle": {"pain": "...", "persona": "...", "emotion": "...", "why": "..."}
}
```

Use an empty string for a missing `on_screen` or `visual`.
