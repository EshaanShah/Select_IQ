import { useRef, useState } from "react";

import { submitFeedback } from "../../shared/api/client";

export function FeedbackForm({ projectId }: { projectId: string }) {
  const savingLock = useRef(false);
  const [rating, setRating] = useState<number | null>(null);
  const [comment, setComment] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (savingLock.current) return;
    if (rating === null) {
      setError("Choose a rating from 1 to 5 before submitting feedback.");
      return;
    }
    savingLock.current = true;
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      await submitFeedback(projectId, rating, comment || null);
      setSaved(true);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Feedback could not be saved.");
    } finally {
      savingLock.current = false;
      setSaving(false);
    }
  }

  return (
    <section className="upload-card feedback-card" aria-labelledby="feedback-title">
      <p className="section-kicker">07 · Evaluate</p>
      <h2 id="feedback-title">How useful was this collection?</h2>
      <p>Your response is stored with this completed project.</p>

      <fieldset className="rating-options">
        <legend>Overall satisfaction</legend>
        {[1, 2, 3, 4, 5].map((value) => (
          <label key={value}>
            <input
              type="radio"
              name="satisfaction-rating"
              value={value}
              checked={rating === value}
              onChange={() => setRating(value)}
            />
            <span>{value}</span>
          </label>
        ))}
      </fieldset>

      <label className="field" htmlFor="feedback-comment">
        <span>Optional comments</span>
        <textarea
          id="feedback-comment"
          value={comment}
          onChange={(event) => setComment(event.target.value)}
          placeholder="What worked well, and what would you change?"
        />
      </label>

      <button className="submit" type="button" disabled={saving} onClick={submit}>
        {saving ? "Saving…" : "Submit feedback"}
      </button>
      {saved && <p className="success">Feedback saved.</p>}
      {error && <p className="error" role="alert">{error}</p>}
    </section>
  );
}
