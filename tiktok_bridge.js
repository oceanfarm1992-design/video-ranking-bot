/**
 * Bridge between Python and tiktok-api-dl.
 * Usage:
 *   node tiktok_bridge.js trending
 *   node tiktok_bridge.js search "funny"
 * Outputs a JSON array of video objects to stdout.
 */

const path = require("path");
const libPath = path.join(__dirname, "venv", "tiktok-api-dl", "lib", "index.js");

let lib;
try {
  lib = require(libPath);
} catch (e) {
  console.error(
    JSON.stringify({ error: "tiktok-api-dl not built. Run: cd venv/tiktok-api-dl && npm install && npm run build" })
  );
  process.exit(1);
}

const { Trending, Search, GetUserPosts } = lib;

const mode = process.argv[2];
const keyword = process.argv[3] || "funny";

// Redirect any library console.log to stderr so our JSON output on stdout stays clean.
const _origLog = console.log;
console.log = (...args) => process.stderr.write(args.join(" ") + "\n");

// Read optional TikTok session cookie from env (set TIKTOK_COOKIE in .env)
const TIKTOK_COOKIE = process.env.TIKTOK_COOKIE || "";

function normalizeVideo(item) {
  const id = item.id || item.video_id || "";
  const creator = item.author?.uniqueId || item.author?.nickname || item.authorMeta?.name || "";
  const video_url = id && creator
    ? `https://www.tiktok.com/@${creator}/video/${id}`
    : item.url || "";
  return {
    platform: "tiktok",
    id,
    title: item.title || item.desc || "",
    creator,
    views: parseInt(item.playCount || item.statsV2?.playCount || item.stats?.playCount || 0, 10),
    likes: parseInt(item.diggCount || item.statsV2?.diggCount || item.stats?.diggCount || 0, 10),
    video_url,
  };
}

// Trending now returns creator cards under exploreList — extract their posts instead.
async function fetchTrending() {
  const result = await Trending();
  const pages = result?.result || result?.data || [];
  const videos = [];
  for (const page of pages) {
    for (const entry of page?.exploreList || []) {
      const card = entry?.cardItem;
      if (!card) continue;
      // card.link is "/@username" — fetch their latest posts
      const username = (card.link || "").replace(/^\/@/, "");
      if (!username) continue;
      try {
        const posts = await GetUserPosts({ username, count: 5 });
        const items = posts?.result || posts?.data || [];
        videos.push(...items.map(normalizeVideo));
      } catch (_) {}
    }
  }
  return videos;
}

async function run() {
  try {
    if (mode === "trending") {
      const videos = await fetchTrending();
      _origLog(JSON.stringify(videos));

    } else if (mode === "search") {
      if (!TIKTOK_COOKIE) {
        // No cookie — fall back to GetUserPosts on known funny accounts
        const FUNNY_ACCOUNTS = ["failarmy", "funnymemes", "9gag", "ladbible"];
        const videos = [];
        for (const username of FUNNY_ACCOUNTS) {
          try {
            const posts = await GetUserPosts({ username, count: 8 });
            const items = posts?.result || posts?.data || [];
            videos.push(...items.map(normalizeVideo));
          } catch (_) {}
        }
        _origLog(JSON.stringify(videos));
      } else {
        const result = await Search(keyword, { type: "video", page: 1, cookie: TIKTOK_COOKIE });
        const videos = result?.result || result?.data || [];
        _origLog(JSON.stringify(videos.map(normalizeVideo)));
      }

    } else {
      console.error(JSON.stringify({ error: `Unknown mode: ${mode}. Use 'trending' or 'search'` }));
      process.exit(1);
    }
  } catch (err) {
    console.error(JSON.stringify({ error: err.message }));
    process.exit(1);
  }
}

run();
