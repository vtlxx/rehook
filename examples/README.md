# Example inputs for the designer page

Files for trying out the page (`streamlit run app.py`) beyond the samples in `data/`. A real run costs about $0.15; mock mode works only for winner 012.

| File | What to do with it | What you should see |
|---|---|---|
| `winner_044.txt` | Under "Winner script" choose "Upload a file" and upload it, or choose "Paste text" and paste its contents. Untick Mock. A new winner: socks lost while travelling. | 20 variants across 6 angles for winner 044. |
| `launched_044.csv` | Upload under "Launch history → Launched hooks". Three manual and three AI hooks already launched for winner 044. | New IDs continue from `SL_W044_AI_H04_…`; variants close to these hooks are dropped as `similar_to_launched`. |
| `ads_export_044.csv` | Upload under "Launch history → Ads Manager export". Spend and purchases for the hooks above. | The best and worst launched hooks by ROMI go into the prompt as examples. |
| `winner_no_id.txt` | Choose "Upload a file" and upload it. | A clear error: `WINNER_ID line not found`. |
| `../data/brand_holiday.yaml` | Pick `brand_holiday.yaml` in "Brand brief". Holiday promo: the only allowed price is $25. | Any hook that says `$29` is flagged `price:$29`; the tone shifts to festive. |

Suggested scenarios:

1. **Mock, no cost:** keep "Sample from data/" with `winner_012.txt`, tick Mock, press Generate. Cards show flags (`price:$19`, `banned_claim:free`, a health claim); tick a few and download the CSV.
2. **Real model on a sample:** untick Mock, keep "Sample from data/", pick `winner_027.txt` or `winner_031.txt`, press Generate.
3. **Your own winner and history:** untick Mock, choose "Upload a file" and upload `winner_044.txt`, then under "Launch history" upload `launched_044.csv` and `ads_export_044.csv`, pick `brand_holiday.yaml`, press Generate.
4. **Errors:** upload `winner_no_id.txt`; press Generate in "Upload a file" or "Paste text" with nothing in it; or tick Mock with `winner_027.txt` (mock exists only for 012, and the error says to untick it).
