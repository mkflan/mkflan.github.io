# my blog website


## Post series

To make a post part of a series, add a `[taxonomies]` table to its front matter:

```toml
+++
title = "Part 2: Decoding instructions"
date = 2026-11-09

[taxonomies]
series = ["Building a Tiny Emulator"]
+++
```

Posts with the same series name are grouped automatically and ordered by `date`. Each post shows a "Part X of N" box and previous/next links, the post list shows the series name, and every series gets a page under `/series/`. The "series" link in the header only appears once at least one published post belongs to a series.

The `demo-emulator-*.md` posts are drafts that show the feature. Preview them locally with `zola serve --drafts`; they are left out of normal builds. Delete them before or after merging.
