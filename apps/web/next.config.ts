import type { NextConfig } from "next";

const nextConfig: NextConfig = {
	/* config options here */
};

export default nextConfig;

// Enable calling `getCloudflareContext()` in `next dev` only.
// See https://opennext.js.org/cloudflare/bindings#local-access-to-bindings.
if (process.env.NODE_ENV === "development") {
	import("@opennextjs/cloudflare").then(({ initOpenNextCloudflareForDev }) =>
		initOpenNextCloudflareForDev()
	);
}
