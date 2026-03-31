import api from "./axios";

/**
 * Sends interview feedback data to the backend REST API.
 *
 * @param {Object} payload - The data to send
 * @param {string} payload.question - The interview question
 * @param {string} payload.transcript - The user's answer text
 * @param {number} payload.duration_seconds - Duration of the recording
 * @param {Object} payload.behavioral_metrics - Calculated or placeholder metrics
 * @param {Object} payload.speech_metrics - Calculated or placeholder metrics
 * @returns {Promise<Object>} - The feedback response from the server
 */
export async function sendFeedback(payload) {
  const response = await api.post("/interview/submit_answer", payload);
  return response.data;
}
