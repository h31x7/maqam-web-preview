# Maqam — team feedback checkpoint

Current single-file Arabic platform with dark/light appearance, embedded thmanyah heading font, local homework/notifications/calendar/quizzes/activity, More navigation, accessibility/voice controls and local publishing.

This is the user-requested current checkpoint, not a claim that all team feedback acceptance tests are complete. 62 automated tests pass; full cross-theme/device browser verification remains pending. Homework, uploads, scheduled releases and activity are local to this browser (localStorage/IndexedDB), with no cross-device or institute delivery. Missing meeting/media/interpreter sources are explicitly unavailable. Scheduling reconciles while open or reopened. See FONT-NOTICE.md for the font embedding notice and recommended written web-use confirmation.

Runtime package excludes .env, standalone font originals, license PDFs, old archives and development files. Existing /api/chat server proxy uses Render environment configuration. Owner must rotate the previously compromised Dify key and store replacement only in Render's DIFY_API_KEY.
