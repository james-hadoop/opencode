import { createSignal, createResource, For, Show } from "solid-js"
import { useAuth } from "../store/auth"

const articles = [
  {
    id: "1",
    title: "The Science of Sleep: Why 7-8 Hours Matters",
    excerpt:
      "Understanding how sleep affects every aspect of your health, from cognitive function to immune system strength.",
    category: "Sleep Health",
    readTime: "8 min read",
    author: "Dr. Sarah Chen",
    date: "Mar 15, 2026",
    image: "moon",
    tags: ["Sleep", "Recovery", "Brain Health"],
    content:
      "Quality sleep is the foundation of good health. During deep sleep, your body repairs tissues, builds bone and muscle, and strengthens your immune system. Research shows that adults who consistently get 7-9 hours of sleep have better cognitive performance, emotional regulation, and metabolic health.",
  },
  {
    id: "2",
    title: "Hydration: More Than Just Drinking Water",
    excerpt: "Discover the optimal hydration strategies for peak physical and mental performance throughout the day.",
    category: "Nutrition",
    readTime: "6 min read",
    author: "Dr. Michael Torres",
    date: "Mar 12, 2026",
    image: "droplet",
    tags: ["Hydration", "Nutrition", "Performance"],
    content:
      "Proper hydration affects everything from cognitive performance to joint lubrication. The human body is approximately 60% water, and even mild dehydration can impair concentration, mood, and physical performance.",
  },
  {
    id: "3",
    title: "Mindful Eating: Transform Your Relationship with Food",
    excerpt: "Practical techniques for developing a healthier, more conscious approach to eating that lasts.",
    category: "Mental Health",
    readTime: "10 min read",
    author: "Dr. Emily Watson",
    date: "Mar 10, 2026",
    image: "meal",
    tags: ["Mindfulness", "Eating", "Mental Health"],
    content:
      "Mindful eating is about awareness and intention. By paying full attention to your eating experience — the taste, texture, and your body's hunger/fullness signals — you can transform your relationship with food.",
  },
  {
    id: "4",
    title: "The Power of Morning Routines",
    excerpt: "How successful people structure their mornings for maximum energy, focus, and well-being.",
    category: "Lifestyle",
    readTime: "7 min read",
    author: "James Mitchell",
    date: "Mar 8, 2026",
    image: "sun",
    tags: ["Routine", "Productivity", "Wellness"],
    content:
      "A consistent morning routine sets the tone for your entire day. Studies show that people with morning routines report higher energy levels, better stress management, and improved work performance.",
  },
  {
    id: "5",
    title: "Understanding Stress: Good vs. Bad",
    excerpt:
      "Learn to distinguish between beneficial stress that drives growth and harmful chronic stress that damages health.",
    category: "Mental Health",
    readTime: "9 min read",
    author: "Dr. Rachel Kim",
    date: "Mar 5, 2026",
    image: "activity",
    tags: ["Stress", "Mental Health", "Resilience"],
    content:
      "Not all stress is bad. Eustress motivates us, while distress overwhelms. Understanding the difference is key to managing your response and building resilience.",
  },
  {
    id: "6",
    title: "Movement as Medicine: Exercise Prescriptions",
    excerpt: "Evidence-based exercise recommendations tailored for different health goals and fitness levels.",
    category: "Fitness",
    readTime: "11 min read",
    author: "Coach David Park",
    date: "Mar 2, 2026",
    image: "fitness",
    tags: ["Exercise", "Fitness", "Longevity"],
    content:
      "Regular physical activity is one of the most powerful tools for preventing chronic disease and extending healthy lifespan. The WHO recommends at least 150 minutes of moderate aerobic activity per week.",
  },
]

const categories = ["All", "Sleep Health", "Nutrition", "Mental Health", "Lifestyle", "Fitness"]

export default function Articles() {
  const auth = useAuth()
  const [activeCategory, setActiveCategory] = createSignal("All")
  const [searchQuery, setSearchQuery] = createSignal("")
  const [selectedArticle, setSelectedArticle] = createSignal<any>(null)
  const [showBookmarks, setShowBookmarks] = createSignal(false)
  const [toast, setToast] = createSignal("")

  const [bookmarkIds, { refetch: refetchBookmarks }] = createResource(() => auth.api("/bookmarks"))

  const toggleBookmark = async (articleId: string) => {
    try {
      const isBookmarked = bookmarkIds()?.includes(articleId)
      await auth.api(`/bookmarks/${articleId}`, { method: isBookmarked ? "DELETE" : "POST" })
      refetchBookmarks()
      showToast(isBookmarked ? "Removed from bookmarks" : "Added to bookmarks")
    } catch (e: any) {
      showToast(e.message)
    }
  }

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(""), 3000)
  }

  const filteredArticles = () => {
    let result = articles
    if (showBookmarks()) {
      const ids = bookmarkIds() || []
      result = result.filter((a) => ids.includes(a.id))
    } else if (activeCategory() !== "All") {
      result = result.filter((a) => a.category === activeCategory())
    }
    if (searchQuery()) {
      const q = searchQuery().toLowerCase()
      result = result.filter(
        (a) =>
          a.title.toLowerCase().includes(q) ||
          a.excerpt.toLowerCase().includes(q) ||
          a.tags.some((t) => t.toLowerCase().includes(q)),
      )
    }
    return result
  }

  const getCategoryColor = (category: string) =>
    ({
      "Sleep Health": "var(--color-accent)",
      Nutrition: "var(--color-success)",
      "Mental Health": "#7c3aed",
      Lifestyle: "#db2777",
      Fitness: "var(--color-warning)",
    })[category] || "var(--color-text-tertiary)"

  return (
    <div>
      <Show when={toast()}>
        <div class="apple-toast">{toast()}</div>
      </Show>

      <div class="mb-10">
        <h1 class="apple-page-title">Health Articles</h1>
        <p class="apple-page-subtitle">Evidence-based insights to help you live your best life.</p>
      </div>

      <div class="apple-card mb-5">
        <div class="flex flex-col sm:flex-row gap-3">
          <div class="relative flex-1">
            <input
              type="text"
              placeholder="Search articles..."
              class="apple-input pl-10"
              value={searchQuery()}
              onInput={(e) => setSearchQuery(e.currentTarget.value)}
            />
            <svg
              class="absolute left-3.5 top-1/2 -translate-y-1/2"
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="var(--color-text-tertiary)"
              stroke-width="2"
            >
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
          </div>
          <button
            class="btn btn-secondary text-sm"
            classList={{ "btn-primary": showBookmarks() }}
            onClick={() => setShowBookmarks((v) => !v)}
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill={showBookmarks() ? "currentColor" : "none"}
              stroke="currentColor"
              stroke-width="2"
            >
              <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
            </svg>
            Bookmarks{bookmarkIds()?.length ? ` (${bookmarkIds()?.length})` : ""}
          </button>
        </div>
        <div class="flex flex-wrap gap-2 mt-4 pt-4" style="border-top: 1px solid var(--color-divider)">
          <For each={categories}>
            {(cat) => (
              <button
                class="px-4 py-1.5 text-sm font-medium rounded-full transition-all cursor-pointer"
                style={
                  activeCategory() === cat && !showBookmarks()
                    ? "background: var(--color-text); color: white"
                    : "background: var(--color-bg-subtle); color: var(--color-text-secondary); border: 1px solid var(--color-divider)"
                }
                onClick={() => {
                  setActiveCategory(cat)
                  setShowBookmarks(false)
                }}
              >
                {cat}
              </button>
            )}
          </For>
        </div>
      </div>

      <Show when={!showBookmarks() && filteredArticles().length > 0 && activeCategory() === "All"}>
        <div class="apple-card mb-6 cursor-pointer" onClick={() => setSelectedArticle(articles[0])}>
          <div class="flex flex-col md:flex-row gap-5">
            <div
              class="w-full md:w-44 h-44 rounded-xl flex items-center justify-center text-5xl shrink-0"
              style="background: var(--color-bg-subtle)"
            >
              <svg
                width="40"
                height="40"
                viewBox="0 0 24 24"
                fill="none"
                stroke="var(--color-text-tertiary)"
                stroke-width="1.5"
              >
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
              </svg>
            </div>
            <div class="flex-1">
              <div class="flex items-center gap-2 mb-2">
                <span class="tag tag-accent">{articles[0].category}</span>
                <span class="tag tag-neutral">Featured</span>
              </div>
              <h2 class="text-xl font-semibold tracking-tight mb-2" style="color: var(--color-text)">
                {articles[0].title}
              </h2>
              <p class="text-sm leading-relaxed mb-3" style="color: var(--color-text-secondary)">
                {articles[0].excerpt}
              </p>
              <div class="flex items-center gap-3 text-xs" style="color: var(--color-text-tertiary)">
                <span>{articles[0].author}</span>
                <span>·</span>
                <span>{articles[0].readTime}</span>
                <span>·</span>
                <span>{articles[0].date}</span>
              </div>
            </div>
          </div>
        </div>
      </Show>

      <Show when={filteredArticles().length === 0}>
        <div class="apple-card text-center py-12">
          <p class="text-sm font-medium mb-1" style="color: var(--color-text)">
            {showBookmarks() ? "No bookmarks yet" : "No articles found"}
          </p>
          <p class="text-sm" style="color: var(--color-text-tertiary)">
            {showBookmarks() ? "Bookmark articles to save them here" : "Try adjusting your search or filters"}
          </p>
        </div>
      </Show>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <For each={filteredArticles().slice(showBookmarks() || activeCategory() !== "All" ? 0 : 1)}>
          {(article) => (
            <div class="apple-card cursor-pointer" onClick={() => setSelectedArticle(article)}>
              <div class="flex gap-4">
                <div
                  class="w-16 h-16 rounded-lg flex items-center justify-center text-2xl shrink-0"
                  style="background: var(--color-bg-subtle)"
                >
                  <svg
                    width="28"
                    height="28"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="var(--color-text-tertiary)"
                    stroke-width="1.5"
                  >
                    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                    <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
                  </svg>
                </div>
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2 mb-1.5">
                    <span class="text-xs font-medium" style={`color: ${getCategoryColor(article.category)}`}>
                      {article.category}
                    </span>
                  </div>
                  <h3
                    class="font-semibold tracking-tight mb-1 line-clamp-2 leading-snug"
                    style="color: var(--color-text)"
                  >
                    {article.title}
                  </h3>
                  <p class="text-xs line-clamp-2 mb-2" style="color: var(--color-text-tertiary)">
                    {article.excerpt}
                  </p>
                  <div class="flex items-center gap-2">
                    <span class="text-xs" style="color: var(--color-text-tertiary)">
                      {article.author}
                    </span>
                    <span class="text-xs" style="color: var(--color-text-tertiary)">
                      ·
                    </span>
                    <span class="text-xs" style="color: var(--color-text-tertiary)">
                      {article.readTime}
                    </span>
                    <button
                      class="ml-auto p-1.5 rounded-lg cursor-pointer transition-colors"
                      style="color: var(--color-text-tertiary)"
                      onClick={(e) => {
                        e.stopPropagation()
                        toggleBookmark(article.id)
                      }}
                    >
                      <svg
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill={bookmarkIds()?.includes(article.id) ? "var(--color-accent)" : "none"}
                        stroke={
                          bookmarkIds()?.includes(article.id) ? "var(--color-accent)" : "var(--color-text-tertiary)"
                        }
                        stroke-width="2"
                      >
                        <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </For>
      </div>

      <Show when={selectedArticle()}>
        <div class="apple-modal-backdrop" onClick={(e) => e.target === e.currentTarget && setSelectedArticle(null)}>
          <div class="apple-modal" style="max-width: 560px">
            <div class="flex items-center justify-between mb-5">
              <span
                class="tag tag-accent"
                style={`background: ${getCategoryColor(selectedArticle()?.category)}15; color: ${getCategoryColor(selectedArticle()?.category)}`}
              >
                {selectedArticle()?.category}
              </span>
              <button class="btn btn-ghost p-2" onClick={() => setSelectedArticle(null)}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
            <h1 class="text-2xl font-bold tracking-tight mb-3" style="color: var(--color-text)">
              {selectedArticle()?.title}
            </h1>
            <div class="flex items-center gap-3 mb-5 pb-5" style="border-bottom: 1px solid var(--color-divider)">
              <div
                class="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-semibold"
                style="background: var(--color-text)"
              >
                {selectedArticle()
                  ?.author.split(" ")
                  .map((n: string) => n[0])
                  .join("")}
              </div>
              <div>
                <p class="text-sm font-medium" style="color: var(--color-text)">
                  {selectedArticle()?.author}
                </p>
                <p class="text-xs" style="color: var(--color-text-tertiary)">
                  {selectedArticle()?.date} · {selectedArticle()?.readTime}
                </p>
              </div>
            </div>
            <p class="text-base leading-relaxed mb-4" style="color: var(--color-text-secondary)">
              {selectedArticle()?.content}
            </p>
            <div class="flex flex-wrap gap-2 mb-5">
              <For each={selectedArticle()?.tags || []}>{(tag: any) => <span class="tag tag-neutral">{tag}</span>}</For>
            </div>
            <div class="flex gap-3">
              <button
                class="btn btn-secondary flex-1 justify-center"
                onClick={() => toggleBookmark(selectedArticle()?.id)}
              >
                <svg
                  width="15"
                  height="15"
                  viewBox="0 0 24 24"
                  fill={bookmarkIds()?.includes(selectedArticle()?.id) ? "currentColor" : "none"}
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
                </svg>
                {bookmarkIds()?.includes(selectedArticle()?.id) ? "Bookmarked" : "Bookmark"}
              </button>
              <button class="btn btn-primary flex-1 justify-center" onClick={() => setSelectedArticle(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      </Show>
    </div>
  )
}
