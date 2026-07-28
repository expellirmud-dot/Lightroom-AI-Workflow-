---
name: image-relevance-triage
description: Classify images by relevance (e.g. primary, supporting, test shots, accident).
---

# Image Relevance Triage

This skill teaches the AI to classify image relevance.

1. Determine whether the image belongs to the same event, subject, location, or narrative context as the batch.
2. Determine whether the image has documentary or supporting value.
3. Identify likely test-shot or accidental-capture evidence.
4. Assess technical usability.
5. Distinguish a relevant candid image from an unintended image.
6. Return KEEP, REVIEW, or SUGGEST_REJECT semantics with a specific class and reason.
