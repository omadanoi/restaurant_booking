import { useEffect, useRef } from "react";

import { WS_URL, tokenStore } from "../api/client";
import type { RealtimeEvent } from "../api/types";

/** Subscribes to a restaurant's live event stream. Reconnects with a small
 * backoff if the socket drops; closes cleanly on unmount/restaurant change.
 */
export function useRestaurantEvents(
  restaurantId: string | null,
  onEvent: (event: RealtimeEvent) => void,
) {
  const handlerRef = useRef(onEvent);
  handlerRef.current = onEvent;

  useEffect(() => {
    if (!restaurantId) return;

    let socket: WebSocket | null = null;
    let retryTimer: number | undefined;
    let attempts = 0;
    let closed = false;

    function connect() {
      const token = tokenStore.access;
      if (!token) return;
      socket = new WebSocket(`${WS_URL}/ws/restaurants/${restaurantId}?token=${token}`);
      socket.onopen = () => {
        attempts = 0;
      };
      socket.onmessage = (msg) => {
        try {
          handlerRef.current(JSON.parse(msg.data as string) as RealtimeEvent);
        } catch {
          /* ignore malformed frames */
        }
      };
      socket.onclose = () => {
        if (closed) return;
        attempts += 1;
        retryTimer = window.setTimeout(connect, Math.min(1000 * 2 ** attempts, 15000));
      };
    }

    connect();
    return () => {
      closed = true;
      window.clearTimeout(retryTimer);
      socket?.close();
    };
  }, [restaurantId]);
}
