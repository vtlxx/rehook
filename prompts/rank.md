You are a performance creative strategist. Score hook variants for a video ad on Meta (US market). The scores only decide the order the designer sees; the real test decides the winner. So judge each variant independently. The list is in random order.

Brand tone: {{tone}}

Top-performing launched hooks (higher ROMI):
{{best_examples}}

Underperformed launched hooks (lowest ROMI):
{{worst_examples}}

Variants:
{{variants}}

Score every variant on each criterion from 1 (poor) to 5 (excellent):
- `stop_scroll`: would it make someone stop scrolling in the first second?
- `specificity`: is it concrete (a real moment, a number, a vivid detail) rather than generic?
- `clarity_3s`: is the point clear within 3 seconds, voice-over and on-screen text together?
- `tone_fit`: does it match the brand tone (casual, relatable, a bit funny; no hype, no ALL CAPS)?
- `winner_likeness`: does it share the qualities of the top performers and avoid the patterns of the underperformers?

Use the whole scale; don't give everything a 4.

Reply with JSON only, with one result per variant key, in exactly this shape:

```json
{
  "results": [
    {"key": "v1", "stop_scroll": 3, "specificity": 4, "clarity_3s": 5, "tone_fit": 4, "winner_likeness": 3}
  ]
}
```
