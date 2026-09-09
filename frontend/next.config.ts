import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // Pin the workspace root so Next doesn't pick up a stray lockfile elsewhere.
  turbopack: {
    root: path.join(__dirname),
  },
  sassOptions: {
    silenceDeprecations: ["legacy-js-api"],
  },
};

export default nextConfig;
