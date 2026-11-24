# Improving AI responses with books

Most bad AI answers fail in the same ways: unsupported claims, invented citations, and merged viewpoints. books attacks each directly.

| Failure | Countermeasure in books |
|---|---|
| Invented citations | Every `[p<id>]` is looked up in the local index; unknown ids are reported. |
| Claims with no evidence | `check` lists any sentence over 8 words with no citation. |
| Citation that doesn't support the claim | Word-overlap check between claim and cited passage flags weak support (heuristic: confirm by reading). |
| Blended, one-sided summaries | `contrast` retrieves passages per source so each author is represented. |
| Overconfidence | Verdict is `CONDITIONAL` until problems are resolved. |

## Prompt pattern for a local model

```text
Use ONLY the passages below. After every claim write the passage id like [p12].
If no passage supports a claim, write "unsupported". Present each source's position
separately before comparing. List what the sources do NOT address.

PASSAGES:
[p12] (Marx) ...
[p31] (Durkheim) ...
```

## Loop

1. `contrast` to retrieve evidence.
2. Prompt the model with the pattern above.
3. Save the answer to `answer.txt`; run `python3 books.py check answer.txt`.
4. Feed the report back: "Fix these items using only the passages." Repeat until `ALLOW`.
5. Read the cited passages yourself. `ALLOW` means traceable, not true.

## Known limits

The overlap check is lexical, so paraphrase can score low and shallow copying can score high. It catches fabrication and drift, not subtle misreadings.
