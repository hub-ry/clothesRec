# clothesRec: discovery and feedback plan

Status: planning only. This document does not authorize implementation.

## Goal and pace

Build a clothing-discovery app that Ryan and his friends can use to develop their own style. Ryan curates sources and makes product decisions; each person's feedback shapes their own recommendations.

- **Goal S:** genuinely useful discoveries, trustworthy listings, and recommendations that improve with feedback.
- **Goal A:** technically impressive engineering, demonstrated through measured retrieval quality, speed, and cost.
- **Target:** finish a useful version by the weekend. The proposed weekend boundary below still needs agreement; it is not a promise to finish every idea in this document.
- **Working pace:** explain one piece, agree on its behavior, build it when authorized, inspect real output together, then move on. Keep chat updates short.

Only clothesRec informs this plan. No dependencies on other personal projects.

## First milestone: review what we collect

A grid of collected clothing and inspiration, with saved feedback that an LLM can read.

Each card shows an image, title, source, and original link. Product listings also show price and currency, new/used condition, known sizes, availability, and when availability was last checked. Missing information stays unknown.

Controls:

- Left arrow: dislike.
- Right arrow: like.
- Up arrow: love.
- Equivalent clickable/tappable buttons.
- Optional reason or note, such as “too expensive” or “not my style.”

Keyboard actions apply only to the visibly selected card and never fire while typing a note. Ratings can be changed or cleared. Unrated means unknown, not disliked.

The grid should let us browse all collected records through pages or incremental loading, without loading every full-size image at once. Inspiration must be visibly distinct from purchasable inventory; invalid records need an inspectable rejection reason rather than disappearing silently.

## Records we need

These are proposed data contracts, not a commitment to a database or framework.

| Record | Minimum information |
|---|---|
| Collected item | Stable internal ID, source identity/link, item kind (inspiration or listing), title, image references, collection time |
| Listing facts | Price and currency, condition, category, known sizes, availability and last-check time; unknown values allowed |
| Feedback | Person ID, item ID, dislike/like/love, optional reason/note, timestamp |
| Preferences | Clothing shopping preference, three starting styles, category budgets, new/used preference |
| LLM summary | Person ID, referenced feedback IDs, summary time, model/prompt version, inferred preferences |

Keep source identity stable across refreshes so ratings stay attached when a listing's price changes. Similar photos do not prove that two listings are the same item. Do not automatically merge colorways or sellers using image similarity.

Ryan's example budgets are $40 for shirts, $100 for pants, and $130 for jackets. These are personal examples, not limits imposed on friends. Currency and whether budgets include shipping/tax need to be explicit.

## Build in small, demonstrable steps

All steps below are unstarted. Each is a discussion and verification checkpoint, not permission to execute the whole plan at once.

### 1. Prove one collection path

Choose one source and inspect a small real sample. Start with the existing Shopify collection approach if appropriate, or prove a chosen resale source if used clothing is the first priority.

**Check:** compare collected images, links, and listing facts with original pages. Repeat collection and confirm stable identities. A failed fetch must not mark everything sold or erase previously collected records.

### 2. Display the review grid

Render that sample with source links and clear unknown/sold/inspiration labels. Reuse the existing frontend where practical; do not choose a new UI framework just for this screen.

**Check:** open the actual screen on desktop and a phone-sized viewport. Inspect loading, missing images, empty results, and original links.

### 3. Save personal feedback

Add the three reactions, optional reasons, and persistence. Separate each person's feedback from Ryan's editorial choices. Choose the initial identity approach before implementation; shared deployment must protect one person's records from another.

**Check:** rate, change, clear, and reload. Use two separate users and confirm their ratings remain independent. Refresh the catalog and confirm ratings survive.

### 4. Let the LLM read the feedback

Provide an inspectable input containing selected rated examples, relevant listing facts, and notes. Images must be included when asking the model to infer visual preferences. Keep original feedback as the source of truth; model summaries are editable inferences.

Generate a summary on demand initially, rather than paying for a call on every click. Select examples from dislikes as well as likes and loves. Treat scraped text as untrusted content, never as instructions for the agent.

**Check:** inspect the exact input, make one real model call, and compare its conclusions with the supplied examples. It should not confuse a price objection with a style dislike or invent preferences without evidence. Record call cost and latency. Keep credentials server-side and make clear what feedback/images leave the app.

### 5. Try the complete loop with a friend

Collect real items, browse the grid, save independent reactions, and inspect separate LLM summaries.

**Check:** both people can explain what was saved and correct an inaccurate inference. Document startup instructions, known source limitations, and the demonstrated workflow.

**Proposed weekend deliverable:** steps 1–5. Agree on this boundary before building; add recommendation work only if we explicitly revise it together.

## Broader app direction

### Personal onboarding and ranking

Ask “What clothing do you want to see?”, then let the person pick three visual styles. Include individual budgets and new/used preferences. Use that as a starting guess, then learn from feedback. Ryan's taste must not silently become everyone's taste.

Build on clothesRec's image embeddings and style matching. Embed catalog images once, retrieve candidates without an LLM call, and optionally rerank a small shortlist with an LLM. Preserve some variety across brands and styles. Style buckets can help retrieval but should not permanently exclude discoveries.

Start with exact vector search as a baseline. Adopt an approximate index only when measured catalog size and latency justify its recall tradeoff. Fewer LLM calls do not automatically mean sublinear vector search.

**Evidence of improvement:** compare personalized results with the existing style-based baseline on separately rated items not used to build the profile. Measure preference quality, retrieval latency, and LLM cost. Compare shortlist quality with and without LLM reranking.

### Suggested outfits

An extension after useful retrieval: select complementary pieces across categories within a person's constraints. Similarity alone tends to retrieve more of the same garment; compatibility is a separate problem. An LLM can offer a second opinion on visual fit, not verify inventory or sizing.

### Sources and agent assistance

- TikTok creators Ryan respects and Pinterest can supply inspiration; neither automatically supplies purchasable listings.
- New and used inventory comes from sources whose current listing facts can be checked.
- Public repositories and spreadsheets may help discover brands and shops. Their interpretation and exact sources remain to be agreed.
- Grokbot is a proposed collection assistant, not an installed or proven dependency here.
- [webmcp-anything](https://github.com/New1Direction/webmcp-anything) is a candidate tool. Its README describes website-to-tool extraction and a best-effort LLM fallback; Pinterest and resale support have not been demonstrated for this project. Check pricing, account permissions, and data handling before connecting accounts.
- Prove any new collector on a small sample before committing. Respect site access rules and rate limits; do not treat login or bot challenges as solved by choosing an agent tool.

### Trending

Use an identifiable signal: store-reported bestsellers or aggregate app engagement once there is enough activity. Label the source and time window. “Recently collected” is not “trending,” and a creator's recommendation is not proof of broad popularity.

## Decisions to make before their build step

1. First collection source, and whether the initial grid includes listings, inspiration, or both.
2. Whether Ryan approves sources or every collected item.
3. Storage and initial user identity approach; SQLite is an option, not a settled requirement.
4. LLM provider, acceptable spend, and data-sharing consent.
5. Which proposed weekend acceptance criteria we commit to.

Do not install tools, connect accounts, run paid collection/model jobs, or modify application code merely because they appear in this plan.
