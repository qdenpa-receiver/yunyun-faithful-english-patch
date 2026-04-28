# Translation Feedback

Use GitHub Discussions -> Translation Suggestions for wording suggestions, Japanese nuance corrections, proper-noun checks, typo/readability notes, UI overflow, untranslated strings, and other translation feedback.

Use Issues only for concrete patch or runtime defects, such as patcher crashes, restore failures, release artifact problems, or wrong text appearing in-game.

Good translation suggestions include:

- table name and key, if known;
- scene, menu, route, screenshot, or exact visible context if the table/key is unknown;
- current patch wording or a short visible excerpt needed to identify the line;
- proposed replacement;
- reasoning for the change;
- Japanese source explanation or reference, where relevant;
- screenshot for runtime/UI issues.

For screenshots, drag/drop or paste the image into the relevant GitHub form textbox; GitHub will insert a Markdown image link automatically.

Do not submit:

- official English localization text;
- copied game files;
- modified game files;
- source-language script dumps;
- large pasted script excerpts;
- material you do not have the right to license.

If you use machine translation, AI assistance, or translation-memory tooling while preparing a suggestion, you are responsible for understanding, checking, editing, and licensing the final text you submit. Raw or unreviewed tool output is not useful for review.

Suggestions are reviewed against the Japanese source. Runtime screenshots and context are useful, but they do not override the Japanese source meaning. Accepted suggestions may be edited before merging, rejected, or logged as ambiguous rather than applied directly.

Do not open drive-by pull requests against the translation JSON files for ordinary wording suggestions. Use Discussions first unless a maintainer has already accepted the change or requested a pull request.
