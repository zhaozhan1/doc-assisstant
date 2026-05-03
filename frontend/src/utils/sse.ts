export type SSEEvent =
  | { type: "token"; value: string }
  | { type: "output_path"; value: string };

/**
 * Shared SSE stream parser. Yields decoded events from a server-sent
 * events stream delivered via a Fetch ReadableStream.
 */
export async function* parseSSEStream(
  reader: ReadableStreamDefaultReader<Uint8Array>,
): AsyncGenerator<SSEEvent, void, unknown> {
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) return;

    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split("\n");
    // Keep the last incomplete line in buffer
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const payload = line.slice(6).trim();
        if (payload === "[DONE]") return;
        try {
          const parsed = JSON.parse(payload) as Record<string, string>;
          if (parsed.token) yield { type: "token", value: parsed.token };
          if (parsed.output_path)
            yield { type: "output_path", value: parsed.output_path };
        } catch {
          /* skip malformed lines */
        }
      }
    }
  }
}
