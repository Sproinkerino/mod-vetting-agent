export function throwIfAborted(signal) {
  if (signal?.aborted) throw new DOMException('Investigation cancelled', 'AbortError');
}

export function abortableDelay(milliseconds, signal) {
  throwIfAborted(signal);
  return new Promise((resolve, reject) => {
    const timer = setTimeout(resolve, milliseconds);
    signal?.addEventListener('abort', () => {
      clearTimeout(timer);
      reject(new DOMException('Investigation cancelled', 'AbortError'));
    }, { once: true });
  });
}