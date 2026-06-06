export type HelloResponse = {
  message: string;
};

export async function fetchHello(signal?: AbortSignal): Promise<HelloResponse> {
  const response = await fetch('/api/hello', { signal });

  if (!response.ok) {
    throw new Error(`Backend returned HTTP ${response.status}`);
  }

  const data = (await response.json()) as Partial<HelloResponse>;

  if (typeof data.message !== 'string') {
    throw new Error('Backend response is missing a message');
  }

  return { message: data.message };
}
