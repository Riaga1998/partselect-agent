const BACKEND_URL = "http://localhost:8000";

/**
 * Sends the full conversation history to the agent backend and returns
 * the assistant's response. ChatWindow calls this after every user message.
 */
export const getAIMessage = async (userQuery, previousMessages = []) => {
  const messages = [
    ...previousMessages
      .filter(m => m.role === "user" || m.role === "assistant")
      // Send only what the backend expects; strip frontend-only fields
      // (tool_calls, suggestions) so the conversation history stays clean.
      .map(m => ({ role: m.role, content: m.content })),
    { role: "user", content: userQuery }
  ];

  try {
    const response = await fetch(`${BACKEND_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Server error ${response.status}`);
    }

    const data = await response.json();
    return {
      role: "assistant",
      content: data.content,
      tool_calls: data.tool_calls || [],
      suggestions: data.suggestions || [],
    };

  } catch (error) {
    console.error("Agent error:", error);
    return {
      role: "assistant",
      content: "Sorry, I couldn't reach the parts assistant right now. Please try again in a moment.",
      tool_calls: [],
      suggestions: [],
    };
  }
};
