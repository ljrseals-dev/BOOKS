# Background research

Notes gathered while designing books. Items marked *unverified* came from secondary summaries and should be checked before you cite them.

## 1. Term-paper mill catalogs are not a usable corpus

- 1980s commercial catalogs (e.g. Research Assistance, Los Angeles; Pacific Research, Seattle) were mail-order sales booklets of several hundred pages listing thousands of stock papers with a short description, footnote/bibliography counts and a price.
- The full catalogs were never deposited in libraries or digitized as open publications; only isolated sample entries appear in period press. There is nothing to collect, and they would be a poor and legally murky seed anyway.
- Conclusion: books starts from **texts you supply** (books and encyclopedias), not from mill listings.

## 2. Legitimate topic-seed sources

- Topic-idea guides such as Robert A. Farmer's *1000 Ideas for Term Papers* series (Arc Books) and Muccigrosso, Blazek and Maggio, *Term Paper Resource Guide to Twentieth-Century United States History* (Greenwood, 1999).
- Library research method: start from encyclopedias and reference works for background, narrow the topic, then move to monographs and journal articles. books automates the "find where sources overlap and disagree" step.
- Open material: Project Gutenberg, Wikisource, Internet Archive, open-access journals, government documents.

## 3. Academic-integrity context (*unverified summary*)

- Secondary summaries report that California Education Code section 66400 (enacted 1977) prohibits preparing or selling term papers when the seller knows or should know they will be submitted for academic credit, and that state and CSU suits against Research Assistance around 1990 led to an injunction. Verify against primary sources (statute text; contemporary Los Angeles Times / New York Times coverage) before relying on details such as dates and courts.
- Design consequence: books labels outputs `research_brief_only`, traces claims to passages, and has no mode that emits a finished submittable essay.

## 4. Architecture ideas (inspiration only)

Earlier brainstorming referenced an exhaustive combinatorial-search tool, a local "offline LLM" and a critic/approval gate with verdicts ALLOW / CONDITIONAL / DENY / ESCALATE. **The specific named repositories could not be verified from public sources and are not dependencies.** What was kept is the pattern:

1. Bounded, cost-capped enumeration of candidates (here: corpus-wide topic ranking).
2. Local model generates analysis only from retrieved evidence.
3. A deterministic gate verifies evidence before anything is trusted (here: `check` and the brief gate).

## 5. Reading list for method

- Booth, Colomb, Williams, *The Craft of Research*.
- Turabian, *A Manual for Writers of Research Papers, Theses, and Dissertations*.
- Adler and Van Doren, *How to Read a Book* (analytical and syntopical reading, which is exactly what `contrast` supports).
