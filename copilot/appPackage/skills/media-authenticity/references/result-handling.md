# Result handling

Audio evidence may appear under `metrics`, image evidence under `image_metrics`, and video evidence under `video_metrics`. Each can have a different label and score. Audio `aggregated_score` and per-chunk `score` arrays are distinct fields. A score of zero is a valid numeric value, not a missing field.

Only report fields actually returned. Explain conflicts rather than selecting a favored modality. An absent audio result on a video does not establish that its audio is authentic. A completed job with missing metrics is insufficient for that assessment.

Pending or processing: preserve the UUID and read it later. Failed, error, or cancelled: report the failure. Unknown status: do not claim completion. When source tracing or contextual intelligence is still processing separately, describe that component as pending even if the primary detection is complete.

Follow-up explanations must remain grounded in returned evidence. A model score is not a calibrated probability of fraud or a substitute for independent verification. A source label reflects a supported model's inference and does not establish who created the media.
