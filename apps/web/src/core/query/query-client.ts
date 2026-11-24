import { QueryClient } from "@tanstack/react-query";

const QUERY_STALE_TIME_MS = 60_000;
const QUERY_MAX_RETRIES = 1;

export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { staleTime: QUERY_STALE_TIME_MS, retry: QUERY_MAX_RETRIES },
    },
  });
}
