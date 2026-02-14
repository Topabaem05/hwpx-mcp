const DEFAULT_DELAY_MS = 28;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function* chunkByWords(text: string, wordsPerChunk: number): Generator<string> {
  const words = text.split(/\s+/).filter(Boolean);
  if (words.length === 0) {
    return;
  }

  for (let i = 0; i < words.length; i += wordsPerChunk) {
    const part = words.slice(i, i + wordsPerChunk).join(" ");
    const suffix = i + wordsPerChunk < words.length ? " " : "";
    yield part + suffix;
  }
}

export async function* runStubAgent(userText: string, signal: AbortSignal): AsyncGenerator<string> {
  const response = `Echo agent: ${userText}`;
  for (const chunk of chunkByWords(response, 3)) {
    if (signal.aborted) {
      return;
    }
    yield chunk;
    await sleep(DEFAULT_DELAY_MS);
  }
}
