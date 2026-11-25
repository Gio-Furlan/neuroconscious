# Writing guide

How to write an article for your site. This file isn't part of the website.

## Start a new article

Create a file in `content/articles/`. The file name becomes the web address: `2026-12-01-curiosity-and-uncertainty.md` is published at `/articles/curiosity-and-uncertainty/` (the date at the start is dropped).

Every article begins with this block:

```yaml
---
title: "Curiosity and uncertainty"
date: 2026-12-01
summary: "One or two sentences shown on the home page and in link previews."
tags: [Exploration, EEG]
draft: true          # remove this line when you're ready to publish
toc: true            # optional: adds a contents list at the top
updated: 2026-12-15  # optional
---
```

Only `title` and `date` are required. Your text goes underneath.

## Text

- Separate paragraphs with a blank line.
- `*italics*`, `**bold**`, `==highlight==`, `~~strikethrough~~`
- Links: `[text](https://example.com)`
- Headings: `## Section` and `### Subsection`
- Lists start with `-` or `1.`; indent four spaces to nest.
- Quotes start with `>`.
- Three dashes `---` on their own line make a section break.

## Equations (LaTeX)

Inline: `\(P(s' \mid s, a)\)`

Display:

```
\[
Q(s,a) \leftarrow Q(s,a) + \alpha \left[ r + \gamma \max_{a'} Q(s',a') - Q(s,a) \right]
\]
```

## Figures

Put the image in `static/images/`, then on its own line:

```markdown
![Describe the image for screen readers](images/my-figure.png "This text becomes the caption.")
```

Tip: from matplotlib, `plt.savefig("fig.svg", transparent=True)` gives a sharp figure that also works in dark mode.

## References and footnotes

```markdown
...as shown previously.[^schultz]

[^schultz]: Schultz, W., Dayan, P., & Montague, P. R. (1997). A neural substrate of prediction and reward. *Science*, 275, 1593–1599.
```

Markers are numbered automatically and listed at the end of the article, so they work as a reference list.

## Code

Three backticks plus the language name:

````markdown
```python
def softmax(q, beta=3.0):
    z = np.exp(beta * (q - q.max()))
    return z / z.sum()
```
````

## Tables

```markdown
| Band  | Frequency (Hz) |
|-------|---------------:|
| Theta | 4–8            |
| Alpha | 8–12           |
```

`---:` right-aligns a column.

## Publish

1. Preview with `python build.py serve` at http://localhost:8000 (drafts show here only).
2. Delete the `draft: true` line.
3. Upload or push the file to GitHub. The site updates in about a minute.
