<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand">
        <div class="brand-mark">TS</div>
        <div>
          <h1>AI 后端技术信息源</h1>
          <p>开源趋势、社区讨论与工程实践聚合</p>
        </div>
      </div>

      <div class="search-wrap">
        <input
          v-model.trim="keyword"
          class="search-input"
          type="search"
          placeholder="搜索标题、摘要、关注点"
        >
      </div>
    </header>

    <main class="layout">
      <aside class="source-panel">
        <button
          v-for="source in sources"
          :key="source.id"
          class="source-tab"
          :class="{ active: source.id === activeSourceId }"
          type="button"
          @click="selectSource(source.id)"
        >
          <span>{{ source.label }}</span>
          <small>{{ source.category }}</small>
        </button>
      </aside>

      <section class="feed-panel">
        <div class="feed-toolbar">
          <div>
            <h2>{{ activeSourceLabel }}</h2>
            <p v-if="generatedAt">
              更新时间 {{ formatTime(generatedAt) }}，数据来自 {{ servedFromText }}
            </p>
            <p v-else>等待后端生成最新数据</p>
          </div>

          <div class="item-count">
            {{ filteredItems.length }} / {{ totalItemCount }}
          </div>
        </div>

        <div v-if="loading" class="state-box">正在加载数据</div>
        <div v-else-if="errorMessage" class="state-box error">{{ errorMessage }}</div>
        <div v-else-if="filteredItems.length === 0" class="state-box">
          当前来源暂无匹配内容
        </div>

        <article
          v-for="item in filteredItems"
          v-else
          :key="item.url + item.title"
          class="feed-item"
        >
          <div class="item-main">
            <a class="item-title" :href="item.url" target="_blank" rel="noreferrer">
              {{ item.title }}
            </a>
            <p class="item-summary">{{ item.chinese_summary || item.original_summary }}</p>
            <p class="item-focus">{{ item.backend_focus }}</p>
            <div class="item-meta">
              <span>{{ item.source }}</span>
              <span>{{ item.category }}</span>
              <span v-if="item.published_at">{{ item.published_at }}</span>
            </div>
          </div>
          <a class="open-link" :href="item.url" target="_blank" rel="noreferrer">
            原文
          </a>
        </article>
      </section>
    </main>
  </div>
</template>

<script>
const API_PREFIX = '/api';

export default {
  name: 'App',
  data() {
    return {
      sources: [],
      activeSourceId: '',
      items: [],
      keyword: '',
      generatedAt: '',
      servedFrom: '',
      totalItemCount: 0,
      loading: false,
      errorMessage: ''
    };
  },
  computed: {
    activeSourceLabel() {
      const source = this.sources.find((item) => item.id === this.activeSourceId);
      return source ? source.label : '最新内容';
    },
    servedFromText() {
      if (this.servedFrom === 'redis') {
        return 'Redis';
      }
      if (this.servedFrom === 'archive') {
        return '磁盘归档';
      }
      return '后端';
    },
    filteredItems() {
      if (!this.keyword) {
        return this.items;
      }
      const keyword = this.keyword.toLowerCase();
      return this.items.filter((item) => {
        return [
          item.title,
          item.chinese_summary,
          item.backend_focus,
          item.original_summary,
          item.category,
          item.source
        ].some((value) => String(value || '').toLowerCase().includes(keyword));
      });
    }
  },
  async created() {
    await this.loadSources();
  },
  methods: {
    async loadSources() {
      this.loading = true;
      this.errorMessage = '';
      try {
        const response = await fetch(`${API_PREFIX}/sources`);
        if (!response.ok) {
          throw new Error(`来源接口返回 ${response.status}`);
        }
        const payload = await response.json();
        this.sources = payload.sources || [];
        if (this.sources.length > 0) {
          await this.selectSource(this.sources[0].id);
        }
      } catch (error) {
        this.errorMessage = `加载来源失败：${error.message}`;
      } finally {
        this.loading = false;
      }
    },
    async selectSource(sourceId) {
      this.activeSourceId = sourceId;
      this.loading = true;
      this.errorMessage = '';
      try {
        const response = await fetch(`${API_PREFIX}/sources/${sourceId}/latest`);
        if (!response.ok) {
          throw new Error(`数据接口返回 ${response.status}`);
        }
        const payload = await response.json();
        this.items = payload.items || [];
        this.generatedAt = payload.generated_at || '';
        this.servedFrom = payload.served_from || '';
        this.totalItemCount = payload.total_item_count || payload.item_count || 0;
      } catch (error) {
        this.items = [];
        this.generatedAt = '';
        this.servedFrom = '';
        this.totalItemCount = 0;
        this.errorMessage = `加载内容失败：${error.message}`;
      } finally {
        this.loading = false;
      }
    },
    formatTime(value) {
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) {
        return value;
      }
      return date.toLocaleString('zh-CN', { hour12: false });
    }
  }
};
</script>

<style>
* {
  box-sizing: border-box;
}

body {
  margin: 0;
  color: #1f2937;
  background: #f4f6f8;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
    "Microsoft YaHei", sans-serif;
}

a {
  color: inherit;
  text-decoration: none;
}

.app-shell {
  min-height: 100vh;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 14px 32px;
  border-bottom: 1px solid #e5e7eb;
  background: rgba(255, 255, 255, 0.96);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 260px;
}

.brand-mark {
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border-radius: 8px;
  color: #ffffff;
  background: #2563eb;
  font-size: 13px;
  font-weight: 700;
}

.brand h1 {
  margin: 0;
  font-size: 18px;
  line-height: 1.3;
  font-weight: 700;
}

.brand p {
  margin: 2px 0 0;
  color: #6b7280;
  font-size: 12px;
}

.search-wrap {
  width: min(420px, 38vw);
}

.search-input {
  width: 100%;
  height: 40px;
  padding: 0 14px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #ffffff;
  color: #111827;
  font-size: 14px;
  outline: none;
}

.search-input:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.layout {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: 24px;
  max-width: 1240px;
  margin: 0 auto;
  padding: 24px 24px 48px;
}

.source-panel {
  position: sticky;
  top: 84px;
  align-self: start;
  padding: 8px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #ffffff;
}

.source-tab {
  display: flex;
  width: 100%;
  min-height: 48px;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  padding: 8px 10px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #374151;
  cursor: pointer;
  text-align: left;
}

.source-tab + .source-tab {
  margin-top: 4px;
}

.source-tab span {
  font-size: 14px;
  font-weight: 650;
}

.source-tab small {
  margin-top: 3px;
  color: #6b7280;
  font-size: 12px;
}

.source-tab.active {
  color: #1d4ed8;
  background: #eff6ff;
}

.feed-panel {
  min-width: 0;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #ffffff;
}

.feed-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 24px;
  border-bottom: 1px solid #e5e7eb;
}

.feed-toolbar h2 {
  margin: 0;
  font-size: 20px;
  line-height: 1.3;
}

.feed-toolbar p {
  margin: 5px 0 0;
  color: #6b7280;
  font-size: 13px;
}

.item-count {
  flex: 0 0 auto;
  color: #4b5563;
  font-size: 13px;
}

.feed-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 18px;
  padding: 20px 24px;
  border-bottom: 1px solid #edf0f3;
}

.feed-item:last-child {
  border-bottom: 0;
}

.feed-item:hover {
  background: #fafafa;
}

.item-title {
  display: inline;
  color: #111827;
  font-size: 19px;
  line-height: 1.38;
  font-weight: 700;
}

.item-title:hover {
  color: #1d4ed8;
}

.item-summary {
  margin: 8px 0 0;
  color: #4b5563;
  font-size: 15px;
  line-height: 1.65;
}

.item-focus {
  margin: 8px 0 0;
  color: #374151;
  font-size: 14px;
  line-height: 1.6;
}

.item-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.item-meta span {
  padding: 3px 8px;
  border-radius: 4px;
  background: #f3f4f6;
  color: #6b7280;
  font-size: 12px;
}

.open-link {
  align-self: start;
  padding: 6px 10px;
  border: 1px solid #dbe3ee;
  border-radius: 6px;
  color: #2563eb;
  font-size: 13px;
  white-space: nowrap;
}

.open-link:hover {
  background: #eff6ff;
}

.state-box {
  margin: 24px;
  padding: 28px;
  border: 1px dashed #d1d5db;
  border-radius: 8px;
  color: #6b7280;
  text-align: center;
}

.state-box.error {
  border-color: #fecaca;
  color: #b91c1c;
  background: #fef2f2;
}

@media (max-width: 860px) {
  .topbar {
    position: static;
    flex-direction: column;
    align-items: stretch;
    padding: 14px 16px;
  }

  .brand {
    min-width: 0;
  }

  .search-wrap {
    width: 100%;
  }

  .layout {
    display: block;
    padding: 16px;
  }

  .source-panel {
    position: static;
    display: flex;
    gap: 8px;
    margin-bottom: 16px;
    overflow-x: auto;
  }

  .source-tab {
    width: 150px;
    flex: 0 0 150px;
  }

  .source-tab + .source-tab {
    margin-top: 0;
  }

  .feed-toolbar,
  .feed-item {
    padding: 16px;
  }

  .feed-item {
    display: block;
  }

  .open-link {
    display: inline-block;
    margin-top: 12px;
  }
}
</style>
