import createClient from "openapi-fetch";

import type { paths } from "@core/api/schema";
import { publicEnv } from "@core/env/browser-env";

export const apiClient = createClient<paths>({
  baseUrl: publicEnv.apiUrl,
});
