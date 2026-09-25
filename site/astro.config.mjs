import sitemap from "@astrojs/sitemap";
import { defineConfig } from "astro/config";

export default defineConfig({
  site: "https://federicodiluca.github.io",
  base: "/la-scimmia-vince/",
  trailingSlash: "always",
  // la compressione mangia gli spazi tra testo ed elementi inline a capo ("sono<em>vere</em>")
  compressHTML: false,
  integrations: [sitemap({ filter: (page) => !page.includes("/og/") })],
});
