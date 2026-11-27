# P09 online experiment prototype v0.1.0

No production service, recruitment, stimuli approval or participant data. All implementation tests use synthetic IDs and non-media byte fixtures.

## Allocation

Server-generated random opaque 128-bit IDs, distinct from consent/contact mappings. Authoritative consent, eligibility, event selection, audio/browser readiness and locked complete baseline must be checked before assignment by an authenticated service; boolean gates in the offline function are not authentication. Allocate 1:1 within musical training strata using OS randomness, concealed permuted blocks of 4 or 6 and SQLite transaction serialization. Freeze stimulus manifest digest for the entire allocation database. Retries return identical arm, UTC assignment timestamp and digest; never return future assignments or slot order. No RNG seed in production. Keep database and backups in a university-approved restricted environment outside Git. Separate P09 and P08 allocation stores; no schema sharing.

## Stimulus bank

Exactly six instrumental and six nonfigurative visual candidates. Validate IDs, modality, file extension, bytes, SHA-256, unique files and documented provenance, rights basis and approval reference. Manifest purpose must be approved-study for ordinary validation. The validator checks declarations and bytes, not actual permission, media decoding, duration or accessibility. An authorised reviewer must independently verify provider licence, output redistribution, source assets, consent and generation provenance; the synthetic fixtures are not valid stimuli. Freeze duration, loudness, visual contrast, semantic ambiguity and salience after pilot. Match the available exploration time, instructions and selection opportunities, not sensory modality. No personal input enters any generator.

## Task and privacy

Both arms: privately recall selected event, preview candidates, select/revise pairing within the same 480-second window; common neutral reflection instructions afterwards. The pure state machine validates preview before selection, elapsed time, stop and finish. Candidate index refers only to the assigned bank modality. It does not record autobiographical text, personal prompts, or free-text input. A future client must keep any optional narrative in volatile memory only (no browser persistence, telemetry, crash logs, third-party scripts or network transmission); provide a no-typing private reflection alternative. Clear on exit/stop/reload, confirm with network inspection and storage tests. Do not equate preview activation with actual perception or assume eight minutes of exposure; assess fidelity separately. Stopping does not imply consent withdrawal and does not invalidate later ratings. Apply timing and original-event gates from inference.py.

## Cessation and export

Withdrawal prototype marks consumed assignment and rejects retry; never recycle slots. Active-status checks are required on all future actions; the caller must enforce them atomically with writes in the eventual service. The marker is not a deletion service or permission to retain data. Pending approved policy, any withdrawal blocks full-cohort export/reconciliation. Institutional policy must determine whether and how to retain minimum randomisation accounting, delete or restrict data, and stop reminders. No promise of deletion from backups without a verified procedure. Distinguish consent withdrawal from incomplete assessment and unknown original event status. Before analysis reconcile the full assigned cohort, arm, stratum, timestamp and bank digest against the restricted ledger; reject missing/extra/tampered rows. Do not export the ledger publicly. A future approved export adapter must resolve withdrawal retention and call reconciliation before inference.

## Pilot decision

Use the approved pilot and content validation protocol; freeze task, bank, timings, SESOI and sample size before confirmation. The previous sensitivity calculations (434/588 randomised) are conditional, not a recruitment commitment. No participant-facing deployment until rights, ethics, authenticated server, secure local UI, end-to-end withdrawal and export verification are complete.
