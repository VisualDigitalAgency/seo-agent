/**
 * Custom hook for SSE streaming with automatic reconnection
 * @param {string} url - SSE endpoint URL
 * @param {function} onMessage - Callback for received messages
 * @param {number} maxRetries - Maximum reconnection attempts (default 5)
 */

export function useSSE(url, onMessage, maxRetries = 5) {
  const [connected, setConnected] = React(false);
  const [reconnecting, setReconnecting] = React(false);
  const eventSourceRef = React.useRef(null);
  const retryCountRef = React.useRef(0);
  const timeoutRef = React.useRef(null);

  const startConnection = React.useCallback((retryCount = 0) => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const attemptConnection = () => {
      const es = new EventSource(url);
      eventSourceRef.current = es;

      es.onopen = () => {
        console.log('SSE connected');
        setConnected(true);
        setReconnecting(false);
        retryCountRef.current = 0;
      };

      es.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          onMessage(data);
        } catch (err) {
          console.error('Failed to parse SSE message:', err);
        }
      };

      es.onerror = () => {
        es.close();
        if (retryCount < maxRetries) {
          setReconnecting(true);
          const backoff = Math.min(1000 * Math.pow(2, retryCount), 30000);
          timeoutRef.current = setTimeout(() => {
            attemptConnection(retryCount + 1);
          }, backoff);
        } else {
          setReconnecting(false);
          console.error('SSE connection failed after maximum retries');
        }
      };
    };

    attemptConnection();
  }, [url, onMessage, maxRetries]);

  React.useEffect(() => {
    startConnection();

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [startConnection]);

  const disconnect = React.useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      setConnected(false);
      setReconnecting(false);
    }
  }, []);

  const reconnect = React.useCallback(() => {
    retryCountRef.current = 0;
    startConnection(0);
  }, [startConnection]);

  return {
    connected,
    reconnecting,
    disconnect,
    reconnect
  };
}
